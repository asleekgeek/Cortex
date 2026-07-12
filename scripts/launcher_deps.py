#!/usr/bin/env python3
"""Dependency bootstrap for scripts/launcher.py — stdlib only.

Runs BEFORE the plugin's own dependencies exist on ``sys.path``, so this
module (like launcher.py itself) may import only the Python standard
library — no fastmcp, no pydantic, no numpy.

Public entry points used by launcher.py: ``ensure_deps`` (base runtime,
every entry point) and ``ensure_all_deps`` (base + ML stack, SessionStart
only).

Source: issue #97 (reporter mbe14, Windows 11). The prior commit step
blindly ``rmtree``'d and ``os.replace``'d every top-level entry pip just
resolved into a temp dir, including transitive deps (e.g. numpy, pulled
in by sentence-transformers) that were already correctly installed and
in-use by a concurrently-running MCP server process. On Windows the
server's imported ``.pyd`` files are locked, so the ``os.replace`` failed
mid-loop, and the pre-existing ``finally: shutil.rmtree(tmp_dir)`` then
destroyed the freshly-downloaded replacement too — leaving deps_dir with
neither the old nor the new package, and every later hook re-attempting
and re-failing the same multi-hundred-MB install for the rest of the
session.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import shutil
import subprocess
import sys
import time

# numpy resolves to two versions in uv.lock depending on Python:
#   2.2.6 for Python < 3.11  (resolution-marker "python_full_version < '3.11'")
#   2.4.4 for Python >= 3.11 (all remaining markers)
# source: uv.lock (numpy blocks at lines ~1968 and ~2033).
_NUMPY_VERSION = "2.2.6" if sys.version_info < (3, 11) else "2.4.4"

# Base runtime (every entry point) + postgres trio (pg_store hard-imports
# at module load): (import_name, pip_spec). All versions sourced from
# uv.lock resolved set.
_BASE_PACKAGES: list[tuple[str, str]] = [
    ("fastmcp", "fastmcp==3.2.4"),  # source: uv.lock
    ("pydantic", "pydantic==2.13.3"),  # source: uv.lock
    ("pydantic_settings", "pydantic-settings==2.14.0"),  # source: uv.lock
    ("numpy", f"numpy=={_NUMPY_VERSION}"),  # source: uv.lock
    ("psycopg", "psycopg[binary]==3.3.3"),  # source: uv.lock
    ("psycopg_pool", "psycopg_pool==3.3.0"),  # source: uv.lock
    ("pgvector", "pgvector==0.4.2"),  # source: uv.lock
]

# ML stack — SessionStart-only. source: uv.lock (sentence-transformers
# and flashrank blocks).
_ML_PACKAGES: list[tuple[str, str]] = [
    ("sentence_transformers", "sentence-transformers==5.4.1"),
    ("flashrank", "flashrank==0.2.10"),
]

_STALE_LOCK_SECONDS = 120  # abandon a lock older than this (crashed holder)
_LOCK_WAIT_SECONDS = 30  # give up waiting and proceed unlocked past this


def _importable(import_name: str, deps_dir: str) -> bool:
    """True iff ``import_name`` resolves to a REAL package.

    A bare ``import pkg`` succeeds even for the husk an interrupted
    ``pip install --target`` leaves behind: the package directory
    exists but has no ``__init__.py``, so Python imports it as a
    NAMESPACE package (``__file__ is None``) and every
    ``from pkg import X`` later dies with "unknown location". Because
    deps_dir is first on sys.path, that husk shadows any healthy
    install and the MCP server fails to connect on every retry
    (observed 2026-06-12: deps/fastmcp without __init__.py →
    "cannot import name 'FastMCP' from 'fastmcp' (unknown location)").

    When a husk is detected inside deps_dir it is deleted so the
    reinstall lands clean. This is deliberately import-based (not a
    dist-info probe) because husk detection needs the real import
    machinery — the fast, import-free dist-info check lives in
    ``_pins_satisfied`` and is tried first by ``ensure_deps``/
    ``ensure_all_deps`` so this function is only reached on a cold or
    mismatched cache (issue #97 suggestion 4).
    """
    import importlib

    try:
        mod = importlib.import_module(import_name)
    except ImportError:
        return False
    if getattr(mod, "__file__", None) is not None:
        return True
    sys.modules.pop(import_name, None)
    husk = os.path.join(deps_dir, import_name)
    if os.path.isdir(husk):
        shutil.rmtree(husk, ignore_errors=True)
        print(
            f"[cortex-launcher] removed corrupt partial install: {husk}",
            file=sys.stderr,
        )
    return False


def _normalize_dist_key(name: str) -> str:
    """Fold a distribution or import name to its dist-info key.

    Mirrors the normalization Python's wheel installer uses for
    ``.dist-info`` directory names (PEP 427/503): runs of ``-._`` become
    a single ``_``, case-folded. ``pydantic-settings`` and
    ``pydantic_settings`` both normalize to ``pydantic_settings``,
    matching the on-disk ``pydantic_settings-2.14.0.dist-info``.
    """
    return re.sub(r"[-_.]+", "_", name).strip("_").lower()


def _parse_pip_spec(spec: str) -> tuple[str, str]:
    """Split ``'name[extra]==version'`` into ``(dist_key, version)``."""
    name_part, _, version = spec.partition("==")
    name_part = name_part.split("[", 1)[0].strip()
    return _normalize_dist_key(name_part), version.strip()


def _dist_info_versions(dir_path: str) -> dict[str, str]:
    """Map normalized dist key -> version for every ``*.dist-info`` child.

    Precondition: none — a missing/unreadable dir yields an empty map.
    Postcondition: pure read, no side effects. Used both for the
    idempotence guard (issue #97 suggestion 1) and the stamp-free
    presence check.
    """
    versions: dict[str, str] = {}
    try:
        children = os.listdir(dir_path)
    except OSError:
        return versions
    for name in children:
        if not name.endswith(".dist-info"):
            continue
        base = name[: -len(".dist-info")]
        dist_name, _, version = base.rpartition("-")
        if not dist_name:
            continue
        versions[_normalize_dist_key(dist_name)] = version
    return versions


def _entry_dist_key(entry: str) -> str:
    """Best-effort normalized dist key for a top-level deps-dir entry."""
    if entry.endswith(".dist-info"):
        base = entry[: -len(".dist-info")]
        dist_name, _, _version = base.rpartition("-")
        return _normalize_dist_key(dist_name or base)
    return _normalize_dist_key(entry)


@contextlib.contextmanager
def _deps_lock(deps_dir: str):
    """Cross-platform mutual exclusion around install+commit.

    Precondition: none. Postcondition: on normal exit the lock directory
    is removed; on an unbounded wait (another process holds a live lock
    past ``_LOCK_WAIT_SECONDS``) this proceeds WITHOUT the lock rather
    than blocking forever — a SessionStart hook has a bounded timeout
    (30s, .claude-plugin/plugin.json) and a permanently-hung bootstrap is
    worse than the historical race this lock narrows.

    Uses ``os.mkdir`` (atomic on every platform CPython supports,
    including Windows) rather than a POSIX-only ``fcntl`` flock, per the
    stdlib-only constraint at the top of this module.

    Rationale for the lock at all: issue #97's race is the SessionStart
    hook and the MCP server both discovering missing base deps at the
    very first boot and calling ``_pip_install`` concurrently — the
    idempotence guard below (skip-if-dest-already-matches) closes the
    common case, but two processes racing to be FIRST still need
    serialization so only one of them performs the commit.
    """
    lock_dir = f"{deps_dir}.lock"
    stamp_file = os.path.join(lock_dir, "holder")
    deadline = time.monotonic() + _LOCK_WAIT_SECONDS
    acquired = False
    while time.monotonic() < deadline:
        try:
            os.mkdir(lock_dir)
            acquired = True
            break
        except FileExistsError:
            try:
                age = time.time() - os.path.getmtime(stamp_file)
            except OSError:
                age = 0.0
            if age > _STALE_LOCK_SECONDS:
                shutil.rmtree(lock_dir, ignore_errors=True)
                continue
            time.sleep(0.2)
    if acquired:
        try:
            with open(stamp_file, "w", encoding="utf-8") as fh:
                fh.write(f"{os.getpid()} {time.time()}")
        except OSError:
            pass
    try:
        yield acquired
    finally:
        if acquired:
            shutil.rmtree(lock_dir, ignore_errors=True)


def _stamp_path(deps_dir: str, kind: str) -> str:
    return os.path.join(deps_dir, f".cortex-deps-stamp-{kind}.json")


def _pins_satisfied(deps_dir: str, kind: str, pins: list[str]) -> bool:
    """True iff a prior successful bootstrap already covered these pins.

    Precondition: ``pins`` is the exact, ordered pip-spec list this call
    would install. Postcondition: pure read (no import, no dist-info
    scan) — this is the "cheaper presence probe" (issue #97 suggestion
    4): once written, later calls in the same session (and across
    sessions, until a Cortex release bumps a pin) skip
    ``_importable``/dist-info work entirely.

    A stamp is trusted only for the exact pin set and Python minor
    version that produced it — "un stamp par version de pin suffit"
    (issue #97): any pin bump (new Cortex release) or interpreter change
    invalidates it and the full check runs again, self-healing.
    """
    try:
        with open(_stamp_path(deps_dir, kind), encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return False
    py = f"{sys.version_info.major}.{sys.version_info.minor}"
    return data.get("python") == py and data.get("pins") == sorted(pins)


def _write_stamp(deps_dir: str, kind: str, pins: list[str]) -> None:
    payload = {
        "python": f"{sys.version_info.major}.{sys.version_info.minor}",
        "pins": sorted(pins),
    }
    try:
        with open(_stamp_path(deps_dir, kind), "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
    except OSError:
        pass  # best-effort — worst case the next call re-verifies


def _commit_entry(tmp_dir: str, deps_dir: str, entry: str) -> str | None:
    """Move one top-level ``tmp_dir`` entry into ``deps_dir``.

    Precondition: ``entry`` is a direct child name of both ``tmp_dir``
    (must exist there) and, if present, ``deps_dir``.
    Postcondition: returns ``None`` on success (dest now holds the new
    entry, any pre-existing dest was moved to a same-directory backup
    which is then removed) or the backup path on FAILURE, in which case
    dest has been restored to its PRE-CALL state (rollback) and the
    caller is responsible for NOT deleting ``tmp_dir`` so ``entry``'s
    freshly-downloaded copy survives for a retry.

    Non-destructive by construction (issue #97 suggestion 2): the
    previous version's ``rmtree(dest)`` before ``os.replace`` meant a
    mid-loop failure left dest permanently deleted with nothing to
    restore. Renaming dest aside first means the ORIGINAL bytes are
    still on disk until the replace has actually succeeded.
    """
    dest = os.path.join(deps_dir, entry)
    src = os.path.join(tmp_dir, entry)
    backup = f"{dest}.bak-{os.getpid()}"
    had_dest = os.path.exists(dest)
    if had_dest:
        if os.path.isdir(backup):
            shutil.rmtree(backup, ignore_errors=True)
        elif os.path.exists(backup):
            os.remove(backup)
        os.replace(dest, backup)
    try:
        os.replace(src, dest)
    except OSError:
        if had_dest:
            # Restore the pre-call state; leave `backup` for the caller's
            # rollback bookkeeping (removed once restore is confirmed).
            if os.path.exists(dest):
                if os.path.isdir(dest):
                    shutil.rmtree(dest, ignore_errors=True)
                else:
                    os.remove(dest)
            os.replace(backup, dest)
        raise
    if had_dest:
        if os.path.isdir(backup):
            shutil.rmtree(backup, ignore_errors=True)
        else:
            with contextlib.suppress(OSError):
                os.remove(backup)
    return None


def _pip_install(deps_dir: str, packages: list[str]) -> bool:
    """Install ``packages`` into ``deps_dir``, surfacing failures.

    Returns True iff every resolved top-level entry was either already
    satisfied (idempotence guard, issue #97 suggestion 1) or committed
    without error. On any commit failure, ``tmp_dir`` is deliberately
    NOT removed (issue #97 suggestion 2: the old ``finally:
    shutil.rmtree(tmp_dir)`` is exactly what made a failed commit
    unrecoverable — it deleted the freshly-installed replacement too).

    PEP 668 interpreters refuse ``pip install`` with an
    ``externally-managed-environment`` error; the explicit
    user-requested override is ``--break-system-packages``. Installing
    with ``--target`` into the plugin's own deps dir never touches
    system site-packages, so the override is safe here.

    Supply-chain safety: ``--index-url`` pins the official PyPI index;
    the sanitized env below strips any inherited PIP_INDEX_URL /
    PIP_EXTRA_INDEX_URL / PIP_CONFIG_FILE so a caller can't reopen the
    dependency-confusion vector this closes.
    """
    tmp_dir = f"{deps_dir}.tmp-{os.getpid()}"
    clean_env = dict(os.environ)
    for _var in (
        "PIP_INDEX_URL",
        "PIP_EXTRA_INDEX_URL",
        "PIP_CONFIG_FILE",
        "PIP_FIND_LINKS",
        "PIP_TRUSTED_HOST",
    ):
        clean_env.pop(_var, None)
    base = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "-q",
        "--index-url",
        "https://pypi.org/simple/",
        "--target",
        tmp_dir,
        *packages,
    ]
    proc = subprocess.run(base, capture_output=True, text=True, env=clean_env)
    err = (proc.stderr or "") + (proc.stdout or "")
    if proc.returncode != 0 and "externally-managed-environment" in err:
        print(
            "[cortex-launcher] WARNING: pip reports an externally-managed "
            "Python environment (PEP 668). The Cortex plugin installs "
            "dependencies into its own private directory (not system "
            "site-packages), so --break-system-packages is safe here. "
            "Retrying with that flag now. If you want to suppress this "
            f"retry, pre-install the packages yourself: {', '.join(packages)}",
            file=sys.stderr,
        )
        proc = subprocess.run(
            base + ["--break-system-packages"],
            capture_output=True,
            text=True,
            env=clean_env,
        )
        err = (proc.stderr or "") + (proc.stdout or "")
    if proc.returncode != 0:
        print(
            "[cortex-launcher] dependency install failed for "
            f"{', '.join(packages)} (python {sys.executable}).\n"
            f"[cortex-launcher] pip said:\n{err.strip()[-2000:]}\n"
            "[cortex-launcher] Fix the pip failure above (network/proxy/"
            "permissions), or pre-install the packages, then reconnect "
            "the cortex MCP server.",
            file=sys.stderr,
        )
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return False

    tmp_versions = _dist_info_versions(tmp_dir)
    dest_versions = _dist_info_versions(deps_dir)
    ok = True
    failed_entry: str | None = None
    for entry in os.listdir(tmp_dir):
        key = _entry_dist_key(entry)
        tmp_v = tmp_versions.get(key)
        # Idempotence guard: dest already has this exact version — never
        # touch it. This is what protects a locked, already-correct
        # transitive dep (numpy under a running MCP server) from ever
        # entering the rmtree/replace path.
        if tmp_v is not None and dest_versions.get(key) == tmp_v:
            continue
        try:
            _commit_entry(tmp_dir, deps_dir, entry)
        except OSError as exc:
            failed_entry = entry
            ok = False
            print(
                f"[cortex-launcher] commit failed for {entry}: {exc}. "
                f"Rolled back; retry preserved at {tmp_dir}.",
                file=sys.stderr,
            )
            break
    if ok:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    else:
        print(
            f"[cortex-launcher] dependency commit stopped at {failed_entry}; "
            f"{tmp_dir} preserved for manual recovery or retry.",
            file=sys.stderr,
        )
    return ok


def ensure_deps(deps_dir: str) -> None:
    """Install the base runtime if missing (every entry point).

    Precondition: none. Postcondition: every package in
    ``_BASE_PACKAGES`` is importable from ``deps_dir``, OR a diagnostic
    was printed to stderr and the caller's own import will fail with a
    clear ImportError.

    The stamp check is a pure file read — issue #97's "one-time
    bootstrap with a success stamp" (suggestion 3) applied to the base
    stack too: after the first successful boot, every later hook/server
    launch in the same install skips ``_importable`` entirely.
    """
    os.makedirs(deps_dir, exist_ok=True)
    pins = [spec for _name, spec in _BASE_PACKAGES]
    if _pins_satisfied(deps_dir, "base", pins):
        return
    missing = [spec for name, spec in _BASE_PACKAGES if not _importable(name, deps_dir)]
    if not missing:
        _write_stamp(deps_dir, "base", pins)
        return
    with _deps_lock(deps_dir):
        # Double-checked: another process may have finished installing
        # while this one waited for the lock.
        if _pins_satisfied(deps_dir, "base", pins):
            return
        missing = [
            spec for name, spec in _BASE_PACKAGES if not _importable(name, deps_dir)
        ]
        if missing:
            _pip_install(deps_dir, missing)
        if all(_importable(name, deps_dir) for name, _spec in _BASE_PACKAGES):
            _write_stamp(deps_dir, "base", pins)


def ensure_all_deps(deps_dir: str) -> None:
    """Install base + ML dependencies (SessionStart hook only).

    Precondition/postcondition: same shape as ``ensure_deps``, extended
    to ``_ML_PACKAGES``. Kept out of the hot path for every OTHER hook
    (issue #97 suggestion 3) — only SessionStart and explicit
    ``--install-deps`` invoke this.
    """
    ensure_deps(deps_dir)
    ml_pins = [spec for _name, spec in _ML_PACKAGES]
    if _pins_satisfied(deps_dir, "ml", ml_pins):
        return
    if _importable("sentence_transformers", deps_dir) and _importable(
        "flashrank", deps_dir
    ):
        _write_stamp(deps_dir, "ml", ml_pins)
        return
    with _deps_lock(deps_dir):
        if _pins_satisfied(deps_dir, "ml", ml_pins):
            return
        if not (
            _importable("sentence_transformers", deps_dir)
            and _importable("flashrank", deps_dir)
        ):
            _pip_install(deps_dir, [spec for _name, spec in _ML_PACKAGES])
        if _importable("sentence_transformers", deps_dir) and _importable(
            "flashrank", deps_dir
        ):
            _write_stamp(deps_dir, "ml", ml_pins)
