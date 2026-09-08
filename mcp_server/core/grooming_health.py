"""Core: grooming staleness classification (pure logic, no I/O).

source: ADR-0186"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

# source: ADR-0186


GROOMING_STALENESS_THRESHOLD_DAYS = 6.0


def days_since(last_iso: str | None, now: datetime | None = None) -> float | None:
    """Elapsed days between ``last_iso`` and ``now``.

    Precondition: ``last_iso`` is a valid ISO-8601 timestamp string, or
    None.
    Postcondition: returns a non-negative float when ``last_iso`` is
    set; returns None when ``last_iso`` is None (the grooming kind has
    never executed -- age is undefined, not zero).
    """
    if not last_iso:
        return None
    ts = datetime.fromisoformat(last_iso)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    now = now or datetime.now(timezone.utc)
    return (now - ts).total_seconds() / 86400.0


def is_stale(
    last_iso: str | None,
    threshold_days: float = GROOMING_STALENESS_THRESHOLD_DAYS,
    now: datetime | None = None,
) -> bool:
    """True when a grooming kind is overdue for attention.

    Precondition: ``threshold_days`` > 0.
    Postcondition: True iff the kind has never run (``last_iso`` is
    None) or last ran more than ``threshold_days`` ago. Never-run is
    always stale by construction -- an undefined age exceeds any finite
    threshold.
    """
    d = days_since(last_iso, now=now)
    return d is None or d > threshold_days


def legs_due(
    kinds: dict[str, dict[str, Any]], *, force: bool = False
) -> dict[str, bool]:
    """Which judgment-level grooming legs are due for a scheduled run
    (G-3), given ``get_grooming_health``'s ``kinds`` output.

    Precondition: kinds has wiki and distillation dictionaries, each with
    stale (bool) and backlog_count (int); any promotion key is ignored.
    Postcondition: a leg is due when force is True or when stale and its
    backlog is nonzero. force=True marks both legs due.
    Invariant: returned keys are exactly wiki and distillation.
    source: ADR-0186"""

    def _due(kind: str) -> bool:
        if force:
            return True
        k = kinds.get(kind) or {}
        return bool(k.get("stale")) and int(k.get("backlog_count") or 0) > 0

    return {"wiki": _due("wiki"), "distillation": _due("distillation")}
