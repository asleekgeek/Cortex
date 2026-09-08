"""Per-cell checkpoint/resume state for the trust-factor sweep.

The load/disk snapshots are NOT a defence against this failure mode (a kill
happens regardless of what they read) -- they remain what they were built
for: metadata that lets a later reader requalify a cell's number without
trusting the runner's word for it. Load and disk are deliberately two
separate signals, not redundant: load average integrates I/O wait as well
as CPU, so it rises under a saturated disk with no CPU contention at all.

source: ADR-0088"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

PROGRESS_FILENAME = "PROGRESS.json"


def _git_sha() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return out.stdout.strip() if out.returncode == 0 else "unknown"


def read_progress(sweep_dir: str) -> dict:
    """Read PROGRESS.json, or an empty structure if absent/unreadable --
    never raises, matching this project's other best-effort snapshot code."""
    path = Path(sweep_dir) / PROGRESS_FILENAME
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {"cells": []}


def completed_w_values(sweep_dir: str) -> set[float]:
    progress = read_progress(sweep_dir)
    return {c["w"] for c in progress.get("cells", []) if c.get("status") == "complete"}


def next_pending_w(grid: list[float], sweep_dir: str) -> float | None:
    """First grid value with no `status: complete` entry, in grid order, or
    None once every cell has one -- the resume point after a kill/crash."""
    done = completed_w_values(sweep_dir)
    for w in grid:
        if w not in done:
            return w
    return None


def record_cell_result(
    sweep_dir: str,
    w: float,
    *,
    status: str,
    repro_dir: str | None,
    snapshots: dict,
) -> None:
    """Append (or replace) one cell's completion record in PROGRESS.json.

    source: ADR-0088"""
    progress = read_progress(sweep_dir)
    progress.setdefault("cells", [])
    progress["cells"] = [c for c in progress["cells"] if c.get("w") != w]
    progress["cells"].append(
        {
            "w": w,
            "status": status,
            "git_sha": _git_sha(),
            "repro_dir": repro_dir,
            **snapshots,
        }
    )
    path = Path(sweep_dir) / PROGRESS_FILENAME
    path.write_text(json.dumps(progress, indent=2))
