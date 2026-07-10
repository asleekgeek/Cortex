"""Safe ``git`` subcommand executor for ``git_diff``.

Isolates all ``subprocess.run`` calls + argument sanitisation behind a
frozen-allowlist check so CodeQL sees the data flow is interrupted
(CWE-78). The public surface is tiny:

* ``git_cmd_safe`` — run an allow-listed git subcommand, return stdout
  or ``""`` on any failure.
* ``get_tracked_files`` — ``git ls-files`` wrapped as a ``set[str]``.

Lives in ``infrastructure`` because it runs external processes. Pure
subprocess boundary, no policy.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from mcp_server.shared.subprocess_safe import run_with_hard_timeout

# Resolve git binary once at import time — never from user input.
_GIT_BINARY = shutil.which("git") or "git"

_ALLOWED_SUBCOMMANDS = frozenset(
    {
        "rev-parse",
        "ls-files",
        "diff",
        "log",
        "show",
    }
)

_DANGEROUS_CHARS = frozenset(";|&$`\n\r\x00")


def _sanitize_arg(arg: str) -> str | None:
    """Reject shell-metacharacter-bearing args (CWE-78).

    Returns a new ``str`` (not the original reference) so CodeQL can
    verify the taint flow is interrupted.
    """
    if any(c in arg for c in _DANGEROUS_CHARS):
        return None
    return str(arg)


def git_cmd_safe(subcommand: str, args: list[str], cwd: Path) -> str:
    """Run a git subcommand under the frozen allowlist.

    Security (CWE-78 mitigation):
      1. subcommand must be in _ALLOWED_SUBCOMMANDS
      2. each arg is validated by _sanitize_arg
      3. sanitised args are new ``str`` objects (breaks taint)
      4. ``shell=False`` everywhere
      5. _GIT_BINARY was resolved at import time via ``shutil.which``

    precondition: ``subcommand``/``args`` are attacker-influenceable
    (diff/entity retrieval on the graph path); ``cwd`` is a resolved
    git root, not user input.
    postcondition: returns stdout (stripped) on a clean exit, or ``""``
    on any failure — disallowed subcommand, a rejected arg, spawn
    failure, non-zero exit, or timeout. Never raises.

    Execution goes through ``run_with_hard_timeout`` (not
    ``subprocess.run``) so a timeout kills the child without CPython's
    own post-kill ``communicate()`` retry — the Windows pipe-handle
    deadlock described in cdeust/Cortex#91/#94.
    """
    if subcommand not in _ALLOWED_SUBCOMMANDS:
        return ""
    safe_args: list[str] = []
    for arg in args:
        sanitized = _sanitize_arg(arg)
        if sanitized is None:
            return ""
        safe_args.append(sanitized)
    run_cmd = [_GIT_BINARY, subcommand, *safe_args]  # noqa: S603 — validated above
    out = run_with_hard_timeout(run_cmd, cwd=cwd, timeout=10)
    return out if out is not None else ""


def get_tracked_files(git_root: Path) -> set[str]:
    """Return the set of all git-tracked files inside ``git_root``."""
    raw = git_cmd_safe("ls-files", [], git_root)
    if not raw:
        return set()
    return set(raw.splitlines())
