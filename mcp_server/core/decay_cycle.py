"""Decay cycle — entity heat decay only.

source: ADR-0156"""

from __future__ import annotations

from datetime import datetime, timezone

# source: ADR-0156

# source: ADR-0156
_MIN_HEAT_DELTA: float = 0.001


def _parse_datetime(value) -> datetime | None:
    """Parse a datetime from either a string or native datetime object.

    psycopg3 returns native datetime objects from TIMESTAMPTZ columns,
    while some code paths pass ISO strings. Handle both.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if isinstance(value, str) and value:
        try:
            dt = datetime.fromisoformat(value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            return None
    return None


def _parse_hours_since_access(record: dict, now: datetime) -> float | None:
    """Parse hours since last access from an entity record.

    source: ADR-0156"""
    last_accessed = (
        record.get("last_accessed")
        or record.get("ingested_at")
        or record.get("created_at", "")
    )
    last_dt = _parse_datetime(last_accessed)
    if last_dt is None:
        return None
    hours = (now - last_dt).total_seconds() / 3600.0
    return hours if hours > 0 else None


def compute_entity_decay(
    entities: list[dict],
    now: datetime | None = None,
    *,
    decay_factor: float = 0.98,
    cold_threshold: float = 0.05,
) -> list[tuple[int, float]]:
    """Compute new heat values for entities.

    source: ADR-0156"""
    if now is None:
        now = datetime.now(timezone.utc)

    updates: list[tuple[int, float]] = []
    for entity in entities:
        current_heat = entity.get("heat", 0.0)
        if current_heat < cold_threshold:
            continue
        hours = _parse_hours_since_access(entity, now)
        if hours is None:
            continue
        new_heat = current_heat * (decay_factor**hours)
        if abs(new_heat - current_heat) > _MIN_HEAT_DELTA:
            updates.append((entity["id"], round(new_heat, 6)))

    return updates
