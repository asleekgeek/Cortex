"""Silent-except sweep (audit 2026-07-11): pg_recall's soft-signal readers.

``_get_active_goal`` and ``_get_user_mood`` are documented as returning the
inactive/absent signal on ANY read failure (duck-typed store methods).
That fallback is legitimate -- but before this fix, a real regression in
``goal_maintenance.build_goal_from_triggers`` or a broken
``get_user_mood()`` on the production store would be indistinguishable
from "mechanism not wired yet", exactly the FlashRank/spread_activation
shape. Unit-tested with a MagicMock store; no PostgreSQL required.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from mcp_server.core import goal_maintenance
from mcp_server.core.pg_recall import _get_active_goal, _get_user_mood
from mcp_server.observability import silent_failure


@pytest.fixture(autouse=True)
def _reset():
    silent_failure.reset()
    yield
    silent_failure.reset()


class TestActiveGoalFailureIsObservable:
    def test_trigger_read_failure_falls_back_to_empty_goal(self, caplog):
        store = MagicMock()
        store.get_active_prospective_memories.side_effect = RuntimeError("pg down")
        with caplog.at_level(
            "WARNING", logger="mcp_server.observability.silent_failure"
        ):
            goal = _get_active_goal(store)
        assert goal == goal_maintenance.EMPTY_GOAL
        assert any("pg_recall.active_goal" in r.message for r in caplog.records)
        assert any("pg down" in r.message for r in caplog.records)

    def test_store_without_reader_is_not_a_failure(self, caplog):
        # No `get_active_prospective_memories` attribute at all -- this is
        # NOT a failure (older store shape), so no log should fire.
        store = object()
        with caplog.at_level(
            "WARNING", logger="mcp_server.observability.silent_failure"
        ):
            goal = _get_active_goal(store)
        assert goal == goal_maintenance.EMPTY_GOAL
        assert not any("pg_recall.active_goal" in r.message for r in caplog.records)


class TestUserMoodFailureIsObservable:
    def test_get_user_mood_failure_falls_back_to_none(self, caplog):
        store = MagicMock()
        store.get_user_mood.side_effect = RuntimeError("column missing")
        with caplog.at_level(
            "WARNING", logger="mcp_server.observability.silent_failure"
        ):
            mood = _get_user_mood(store)
        assert mood is None
        assert any("pg_recall.user_mood" in r.message for r in caplog.records)

    def test_repeat_failure_does_not_spam(self, caplog):
        store = MagicMock()
        store.get_user_mood.side_effect = RuntimeError("column missing")
        with caplog.at_level(
            "WARNING", logger="mcp_server.observability.silent_failure"
        ):
            _get_user_mood(store)
            first = len(caplog.records)
            _get_user_mood(store)
            second = len(caplog.records)
        assert second == first
