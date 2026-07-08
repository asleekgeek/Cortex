"""Handler tests for replay_tracking — the shared CLS-B producer wiring.

Pure wiring tests (fake duck-typed store, no database): verifies that a
replay event bumps the counters, applies exactly one C-HORSE transfer delta
to hippocampal_dependency, respects the TWO_STAGE_MODEL ablation switch, and
never raises even when the store misbehaves.
"""

from __future__ import annotations

from mcp_server.core.two_stage_transfer import update_hippocampal_dependency
from mcp_server.handlers.replay_tracking import track_replay_event


class _FakeStore:
    def __init__(self, memories: dict[int, dict]) -> None:
        self._memories = memories
        self.access_calls: list[int] = []
        self.dependency_writes: dict[int, float] = {}

    def update_memory_access(self, memory_id: int) -> None:
        self.access_calls.append(memory_id)

    def increment_replay_count(self, memory_id: int) -> dict | None:
        mem = self._memories.get(memory_id)
        if mem is None:
            return None
        mem["replay_count"] = mem.get("replay_count", 0) + 1
        return {
            "replay_count": mem["replay_count"],
            "hippocampal_dependency": mem.get("hippocampal_dependency", 1.0),
            "schema_match_score": mem.get("schema_match_score", 0.0),
            "importance": mem.get("importance", 0.5),
        }

    def update_memory_hippocampal_dependency(
        self, memory_id: int, dependency: float
    ) -> None:
        self.dependency_writes[memory_id] = dependency
        self._memories[memory_id]["hippocampal_dependency"] = dependency


class _RaisingStore:
    def update_memory_access(self, memory_id: int) -> None:
        raise RuntimeError("connection dropped")

    def increment_replay_count(self, memory_id: int) -> None:
        raise AssertionError("must not be reached")


def test_bumps_access_and_replay_count():
    store = _FakeStore({1: {"replay_count": 0}})
    track_replay_event(1, store)
    assert store.access_calls == [1]
    assert store._memories[1]["replay_count"] == 1


def test_below_min_replays_no_dependency_write():
    """First replay (count=1) is below _MIN_REPLAYS_FOR_TRANSFER=2 — count
    advances but dependency is untouched (compute_transfer_delta guard)."""
    store = _FakeStore({1: {"replay_count": 0, "hippocampal_dependency": 1.0}})
    track_replay_event(1, store)
    assert 1 not in store.dependency_writes
    assert store._memories[1]["hippocampal_dependency"] == 1.0


def test_second_replay_applies_exactly_one_transfer_delta():
    store = _FakeStore({1: {"replay_count": 1, "hippocampal_dependency": 1.0}})
    track_replay_event(1, store)
    expected = update_hippocampal_dependency(1.0, 2, 0.0, 0.5)
    assert store.dependency_writes[1] == expected
    assert expected < 1.0


def test_ablation_disables_decay_but_keeps_counting(monkeypatch):
    monkeypatch.setenv("CORTEX_ABLATE_TWO_STAGE_MODEL", "1")
    store = _FakeStore({1: {"replay_count": 1, "hippocampal_dependency": 1.0}})
    track_replay_event(1, store)
    assert store._memories[1]["replay_count"] == 2
    assert 1 not in store.dependency_writes


def test_memory_deleted_between_enrichment_and_tracking_is_a_noop():
    store = _FakeStore({})
    track_replay_event(999, store)  # must not raise
    assert store.dependency_writes == {}


def test_store_errors_never_propagate():
    track_replay_event(1, _RaisingStore())  # must not raise


def test_dependency_at_release_threshold_stays_a_no_op_write():
    """Once dependency has already reached the release threshold, further
    replays keep replay_count advancing but issue no further dependency
    write (compute_transfer_delta returns 0 at/below the threshold)."""
    store = _FakeStore({1: {"replay_count": 10, "hippocampal_dependency": 0.05}})
    track_replay_event(1, store)
    assert 1 not in store.dependency_writes
