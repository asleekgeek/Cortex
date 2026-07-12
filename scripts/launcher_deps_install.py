#!/usr/bin/env python3
"""Pip invocation and non-destructive commit — stdlib only.

Split out of ``scripts/launcher_deps.py`` for SRP and the 500-line
file-size rule: this module owns the two I/O-heavy steps of a
dependency install — spawning ``pip`` into a scratch dir and committing
its result into ``deps_dir`` one entry at a time — while
``launcher_deps.py`` owns the higher-level policy (stamping, locking,
when to call this at all) and ``launcher_deps_fs.py`` owns pure
filesystem primitives this module reads/writes through.

Like its siblings, this module runs before the plugin's own
dependencies exist on ``sys.path`` and may import only the Python
standard library.
"""

from __future__ import annotations

import contextlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

_SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)
import launcher_deps_fs as _fs  # noqa: E402


def commit_entry(tmp_dir: str, deps_dir: str, entry: str) -> str | None:
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


def pip_install(
    deps_dir: str, packages: list[str], constraints: list[str] | None = None
) -> bool:
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

    ``constraints``, when given, is a list of pip specs (``name==ver``)
    written to a ``-c`` constraints file for this install only (issue
    #97 residue 3, reporter mbe14, "the substantial one"): without it, a
    package pip pulls in as a TRANSITIVE (e.g. numpy via
    sentence-transformers for the ML install) resolves freely and can
    land on a different version than the pin the base install already
    committed, splitting deps_dir's numpy across two callers. Passing
    the base pins as constraints on the ML install forces pip to solve
    within them, so a shared transitive agrees with the base pin instead
    of "whatever pip's resolver happens to pick this time."
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
    constraints_file = None
    if constraints:
        constraints_file = f"{deps_dir}.constraints-{os.getpid()}.txt"
        with open(constraints_file, "w", encoding="utf-8") as fh:
            fh.write("\n".join(constraints) + "\n")
    base = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "-q",
        "--index-url",
        "https://pypi.org/simple/",
        *(["-c", constraints_file] if constraints_file else []),
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
    if constraints_file is not None:
        # Only a resolution hint for THIS pip invocation — not needed
        # past this point regardless of outcome.
        with contextlib.suppress(OSError):
            os.remove(constraints_file)
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

    tmp_versions = _fs.dist_info_versions(tmp_dir)
    dest_versions = _fs.dist_info_versions(deps_dir)
    ok = True
    failed_entry: str | None = None
    for entry in os.listdir(tmp_dir):
        key = _fs.entry_dist_key(entry)
        tmp_v = tmp_versions.get(key)
        # Idempotence guard: dest already has this exact version — never
        # touch it. This is what protects a locked, already-correct
        # transitive dep (numpy under a running MCP server) from ever
        # entering the rmtree/replace path.
        if tmp_v is not None and dest_versions.get(key) == tmp_v:
            continue
        try:
            commit_entry(tmp_dir, deps_dir, entry)
        except OSError as exc:
            failed_entry = entry
            ok = False
            print(
                f"[cortex-launcher] commit failed for {entry}: {exc}. "
                f"Rolled back; retry preserved at {tmp_dir}.",
                file=sys.stderr,
            )
            break
        else:
            # Residue 2: only reached on a SUCCESSFUL commit — a
            # cross-version bump just replaced dest's dist-info, so any
            # older sibling for the same distribution is now stale.
            _fs.prune_superseded_dist_info(deps_dir, entry)
    if ok:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    else:
        print(
            f"[cortex-launcher] dependency commit stopped at {failed_entry}; "
            f"{tmp_dir} preserved for manual recovery or retry.",
            file=sys.stderr,
        )
    return ok
