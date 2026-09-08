"""Store-derived signal readers consumed by pg_recall's orchestration stages.

source: ADR-0219"""

from __future__ import annotations

from typing import Any

from mcp_server.core import goal_maintenance
from mcp_server.core.titans_memory import TitansMemory
from mcp_server.observability import silent_failure

# Singleton Titans memory module (persists across recalls within a session)
_titans: TitansMemory | None = None


def _get_titans() -> TitansMemory:
    global _titans
    if _titans is None:
        _titans = TitansMemory()
    return _titans


def _get_active_goal(store: Any) -> Any:
    """Promote the store's active prospective triggers into a sustained goal (A3).

    source: ADR-0219

    Returns ``goal_maintenance.EMPTY_GOAL`` (inactive → identity re-weight) when
    the store is None, lacks the reader, has no active triggers, or the read
    fails. Per the source-discipline rule we never fabricate a goal signal.
    """

    if store is None or not hasattr(store, "get_active_prospective_memories"):
        return goal_maintenance.EMPTY_GOAL
    try:
        triggers = store.get_active_prospective_memories()
        return goal_maintenance.build_goal_from_triggers(triggers)
    except Exception as exc:  # noqa: BLE001 — source: ADR-0219
        silent_failure.note("pg_recall.active_goal", exc)
        return goal_maintenance.EMPTY_GOAL


def _get_user_mood(store: Any) -> float | None:
    """Return the user's session-level mood in [-1, +1], or None if absent.

    source: ADR-0219"""
    if store is None:
        return None
    if not hasattr(store, "get_user_mood"):
        return None
    try:
        v = store.get_user_mood()
    except Exception as exc:  # noqa: BLE001 — source: ADR-0219
        silent_failure.note("pg_recall.user_mood", exc)
        return None
    if v is None:
        return None
    try:
        return max(-1.0, min(1.0, float(v)))
    except (TypeError, ValueError):
        return None
