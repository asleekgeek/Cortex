"""Per-window session registry — T2-handlers increment H1 (foundation).

Design: t2-handlers-design.md, decisions T2-D1..D12 (2026-07-10). Hooks
(write side, H2) record the CURRENT session of their window; the MCP
server (read side, H3) resolves it at each emission. No hook wiring
lives here — H1 is the infrastructure module + its own tests only.

Directing invariant (design §1, zetetic): a false attribution is worse
than a missing one. Every anomaly this module can observe — no entry,
unknown schema version, dead pid, pid-reuse (start-time mismatch),
tombstone — degrades to ``None``. Never a guessed or stale value.

Architecture (T2-D2/D3/D4/D8, F8/F9): ONE JSON file per window at
``~/.cache/cortex/session-registry/<claude_pid>.json`` (prior art:
``cortex_viz/server/viz_instance.py``'s ``viz-server.json``, F6).
Writer (hook side, H2): resolves the ancestor ``claude`` process via a
bounded ancestor walk (hooks run ``claude -> bash -> python``, F9 —
depth is NOT constant across OS/bash versions) and writes atomically
(tmp + ``os.replace``, T2-D4). Reader (server side, H3): the MCP
server is a DIRECT child of the window's ``claude`` process
(``runpy.run_module`` in-process, ``scripts/launcher.py:314-316``, F8)
— ``os.getppid()`` resolves the key with no walk needed. Resolved
fresh on EVERY call, never cached (T2-D7): a cache would reconstruct
the exact staleness bug (``CLAUDE_CODE_SESSION_ID`` at spawn, F2) this
module exists to fix.

Platform note (design risk 1 — Windows portability): ``ps``/``comm``/
process-start-time discovery are POSIX-only. Every platform-specific
helper below degrades to ``None``/``False`` rather than raising on an
unsupported platform — never a false attribution.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

from mcp_server.infrastructure.file_io import read_json

# Schema version (T2-D10): unknown versions are rejected by the reader
# rather than mis-parsed — future format changes bump this constant and
# old readers degrade to None instead of guessing at a new shape.
# source: design T2-D10.
_SCHEMA_VERSION = 1

# Ancestor-walk depth bound (T2-D3): hooks run claude -> bash -> python
# (F9); bash does not exec-replace on a `&&` command list (measured
# 2026-07-10, design F9), so hook depth is >= 2 but not a fixed
# constant across OS/bash versions. 15 is the hard bound the design
# specifies for this walk. source: design T2-D3.
_MAX_ANCESTOR_DEPTH = 15

# Subprocess timeout for `ps` probes. Hooks share UserPromptSubmit's 5s
# budget (design risk 5) and must never block it; `ps -p <pid>` returns
# in single-digit milliseconds locally. source: measured 2026-07-10,
# local darwin — bound is a hang-guard, not a tuned value.
_PS_TIMEOUT_S = 1.0


def registry_dir() -> Path:
    """Registry dir — mirrors ``viz-server.json`` prior art (F6)."""
    return Path.home() / ".cache" / "cortex" / "session-registry"


def registry_path(claude_pid: int) -> Path:
    """Registry file for one window, keyed by its ``claude`` pid."""
    return registry_dir() / f"{claude_pid}.json"


def _pid_alive(pid: int) -> bool:
    """True iff ``pid`` currently identifies a live process. Never
    raises; a permission error (pid exists, owned by another user)
    still counts as alive."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _process_start_signature(pid: int) -> str | None:
    """Opaque per-process start-time token (T2-D5 pid-reuse guard).

    Returned as an OPAQUE string — never parsed as a timestamp, only
    compared for equality between write and read. Sidesteps locale/
    clock-format concerns entirely; only "did this pid restart since
    the entry was written" matters.

    Linux: ``/proc/<pid>/stat`` field 22 (starttime, clock ticks since
    boot — kernel-stable, locale-free; source: proc(5)). macOS/BSD (no
    /proc): ``ps -o lstart=`` — locale-fixed text, used only as an
    opaque comparison token (source: design T2-D5, "ps -o
    lstart=/epoch-equivalent"; psutil is NOT a project dependency —
    checked pyproject.toml 2026-07-10 — so stdlib+ps is the minimal,
    dependency-free choice matching infra-layer stdlib-only imports,
    CLAUDE.md dependency table). Any other platform, or any read/parse
    failure: None (degrade, never guess — design risk 1).
    """
    stat_path = Path(f"/proc/{pid}/stat")
    if stat_path.exists():
        try:
            raw = stat_path.read_text(encoding="utf-8")
            after_comm = raw.rsplit(")", 1)[1]
            fields = after_comm.split()
            return fields[19]  # field 22 overall = index 19 after comm+state
        except (OSError, IndexError, ValueError):
            return None
    try:
        out = subprocess.run(
            ["ps", "-o", "lstart=", "-p", str(pid)],
            capture_output=True,
            text=True,
            timeout=_PS_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    line = out.stdout.strip()
    return line or None


def _ppid_and_comm(pid: int) -> tuple[int, str] | None:
    """One ancestor-walk step: ``(parent pid, comm)`` of ``pid``, or
    None on any probe failure (dead pid, unsupported platform)."""
    try:
        out = subprocess.run(
            ["ps", "-o", "ppid=,comm=", "-p", str(pid)],
            capture_output=True,
            text=True,
            timeout=_PS_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    parts = out.stdout.strip().split(None, 1)
    if len(parts) != 2:
        return None
    try:
        ppid = int(parts[0])
    except ValueError:
        return None
    return ppid, parts[1].strip()


def find_claude_ancestor(max_depth: int = _MAX_ANCESTOR_DEPTH) -> int | None:
    """Walk ancestors from ``os.getppid()`` looking for a ``claude``
    process (T2-D3, hook side only — the server uses ``os.getppid()``
    directly, see ``current_window_session``).

    precondition: called from a hook's python process (claude -> bash
    -> python chain, F9). postcondition: returns the nearest ancestor
    pid whose executable basename is ``claude``, or None when none is
    found within ``max_depth`` steps or a probe fails — no match is a
    legitimate outcome (renamed/wrapped claude binary, design risk 2).
    invariant: loop runs at most ``max_depth`` iterations; terminates
    early on probe failure, root (`ppid <= 1`), or a match.
    """
    pid = os.getppid()
    for _ in range(max_depth):
        info = _ppid_and_comm(pid)
        if info is None:
            return None
        ppid, comm = info
        if os.path.basename(comm) == "claude":
            return pid
        if ppid <= 1:
            return None
        pid = ppid
    return None


def _atomic_write(path: Path, payload: dict) -> bool:
    """Write ``payload`` as JSON to ``path`` atomically (T2-D4): a
    reader sees the old content or the new content in full, never a
    torn file. Best-effort — returns False rather than raising (hooks
    must never fail their primary path for this)."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=path.name + ".tmp.", dir=str(path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(payload, f)
        except Exception:
            os.unlink(tmp)
            raise
        os.replace(tmp, path)
    except OSError:
        return False
    return True


def write_session(session_id: str | None, *, claude_pid: int | None = None) -> bool:
    """Write/refresh this window's registry entry (writer side, H2).

    precondition: ``session_id`` is the transcript-stem identity the
    caller already computed (``session_id_from_transcript`` in
    ``handlers/injection_receipts.py`` — this module does not derive
    it, T2-D1); ``claude_pid``, if given, is a pre-resolved ancestor
    pid, else resolved here via ``find_claude_ancestor()``.
    postcondition: on success, ``registry_path(claude_pid)`` exists,
    holds valid JSON ``{v, session_id, claude_pid, claude_start_time,
    updated_at}``, replaced atomically. Returns False without writing
    when the ancestor pid or its start signature cannot be resolved
    (degrade, never invent — design §1). ``session_id=None`` writes a
    TOMBSTONE (Q1 arbitrage): entry stays present, valid lineage, but
    reads as no-session.
    """
    pid = claude_pid if claude_pid is not None else find_claude_ancestor()
    if pid is None:
        return False
    start_sig = _process_start_signature(pid)
    if start_sig is None:
        return False
    payload = {
        "v": _SCHEMA_VERSION,
        "session_id": session_id,
        "claude_pid": pid,
        "claude_start_time": start_sig,
        "updated_at": time.time(),
    }
    return _atomic_write(registry_path(pid), payload)


def tombstone(claude_pid: int) -> bool:
    """SessionEnd write path (Q1 arbitrage, H2 calls this): the window's
    entry degrades to no-session until the next refresh. Idempotent."""
    return write_session(None, claude_pid=claude_pid)


def current_window_session() -> str | None:
    """Read side (H3/H4): this window's current session, or None.

    precondition: called from the MCP server process — a direct child
    of the window's ``claude`` process (F8; ``os.getppid()`` needs no
    ancestor walk here, unlike the hook side).
    postcondition: returns the tombstone-free, lineage-valid
    ``session_id`` for THIS window, or None on any of: no registry
    file, unreadable/non-dict JSON, unknown/missing schema version,
    ``claude_pid`` mismatch, dead ``claude_pid``, start-time lineage
    mismatch (pid reuse), or a tombstoned entry. No TTL (T2-D5) —
    validity is process lineage, not entry age. Fresh every call,
    never cached (T2-D7).
    """
    claude_pid = os.getppid()
    data = read_json(registry_path(claude_pid))
    if not isinstance(data, dict):
        return None
    if data.get("v") != _SCHEMA_VERSION:
        return None
    if data.get("claude_pid") != claude_pid:
        return None
    if not _pid_alive(claude_pid):
        return None
    recorded_start = data.get("claude_start_time")
    current_start = _process_start_signature(claude_pid)
    if current_start is None or recorded_start != current_start:
        return None
    session_id = data.get("session_id")
    return session_id if isinstance(session_id, str) and session_id else None


def purge_dead_entries() -> int:
    """Delete registry files whose ``claude_pid`` is no longer alive
    (T2-D11, prior art ``viz_instance.py``'s pid-dead invalidation).
    Exposed for H2 to call from the SessionStart hook. No daemon, no
    TTL: the only leak is a closed window's file.

    postcondition: returns count of files removed; never raises — an
    unreadable directory or file is skipped, not fatal.
    """
    removed = 0
    d = registry_dir()
    try:
        entries = list(d.iterdir())
    except OSError:
        return 0
    for entry in entries:
        if entry.suffix != ".json":
            continue
        try:
            pid = int(entry.stem)
        except ValueError:
            continue
        if not _pid_alive(pid):
            try:
                entry.unlink()
                removed += 1
            except OSError:
                pass
    return removed
