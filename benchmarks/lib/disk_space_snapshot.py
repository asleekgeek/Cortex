"""Disk-space snapshot for a benchmark cell.

source: ADR-0074"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _usage(path: str) -> dict | None:
    try:
        usage = shutil.disk_usage(path)
    except OSError:
        return None
    return {
        "path": path,
        "free_bytes": usage.free,
        "total_bytes": usage.total,
    }


def _docker_root_dir() -> str | None:
    try:
        out = subprocess.run(
            ["docker", "info", "--format", "{{.DockerRootDir}}"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return out or None


def disk_space_snapshot() -> dict:
    """Free/total bytes on the volume(s) backing benchmark data + Docker
        storage, as this run saw them.

    source: ADR-0074"""
    docker_root = _docker_root_dir()
    return {
        "repo_root": _usage(str(_REPO_ROOT)),
        "docker_root": _usage(docker_root) if docker_root else None,
    }
