"""Private rotating worker diagnostics, independent of the launching hook pipe."""

from __future__ import annotations

import logging
import os
import stat
from logging.handlers import RotatingFileHandler
from pathlib import Path

# source: remediation F9, measured 2026-09-06: 196 kB/day; 30 days ≈ 6 MB.
LOG_BYTES = 196_000 * 30


def configure(runtime: Path) -> None:
    path = runtime / "worker.log"
    for candidate in (path, path.with_suffix(".log.1")):
        try:
            info = candidate.lstat()
        except FileNotFoundError:
            continue
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid():
            raise PermissionError("capture worker log must be an owner-controlled file")
    descriptor = os.open(
        path, os.O_CREAT | os.O_APPEND | os.O_WRONLY | os.O_NOFOLLOW, 0o600
    )
    os.fchmod(descriptor, 0o600)
    os.close(descriptor)
    # Retain the immediately previous segment; no accumulated unbounded history.
    handler = RotatingFileHandler(
        path, maxBytes=LOG_BYTES, backupCount=1, encoding="utf-8"
    )
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
