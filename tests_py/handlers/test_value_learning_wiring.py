"""Integration test for the B2 value-learning wiring in rate_memory.

Verifies that a usefulness verdict triggers a TD value update persisted via
store.update_memory_value, using a fake store (no Postgres required).
"""

from __future__ import annotations

import asyncio

from mcp_server.handlers import rate_memory
from mcp_server.core import value_learning


class _FakeStore:
    def __init__(self, mem):
        self._mem = dict(mem)
        self.value_writes: list[tuple[int, float]] = []
        self.metamemory_writes: list[tuple] = []

    def get_memory(self, memory_id):
        return dict(self._mem) if self._mem.get("id") == memory_id else None

    def update_memory_metamemory(
        self, memory_id, access_count, useful_count, confidence
    ):
        self.metamemory_writes.append(
            (memory_id, access_count, useful_count, confidence)
        )

    def update_memory_value(self, memory_id, value):
        self.value_writes.append((memory_id, value))


def _run(store, args, monkeypatch):
    monkeypatch.setattr(rate_memory, "_get_store", lambda: store)
    # Avoid the reranker Platt side-path (needs a query); omit query.
    return asyncio.run(rate_memory._handler_impl(args))


def test_rate_useful_raises_value(monkeypatch):
    store = _FakeStore(
        {
            "id": 5,
            "content": "x",
            "value": 0.5,
            "importance": 0.8,
            "access_count": 2,
            "useful_count": 1,
            "confidence": 0.5,
        }
    )
    out = _run(store, {"memory_id": 5, "useful": True}, monkeypatch)
    assert out["rated"] is True
    # A value write happened and the new value rose above the 0.5 prior.
    assert len(store.value_writes) == 1
    mid, new_v = store.value_writes[0]
    assert mid == 5
    assert new_v > 0.5
    assert out["value"] == round(new_v, 4)


def test_rate_not_useful_lowers_value(monkeypatch):
    store = _FakeStore(
        {
            "id": 6,
            "content": "y",
            "value": 0.7,
            "importance": 0.5,
            "access_count": 4,
            "useful_count": 3,
            "confidence": 0.6,
        }
    )
    _run(store, {"memory_id": 6, "useful": False}, monkeypatch)
    mid, new_v = store.value_writes[0]
    assert new_v < 0.7


def test_value_absent_uses_prior(monkeypatch):
    # A memory whose row predates the value column (no 'value' key).
    store = _FakeStore(
        {
            "id": 7,
            "content": "z",
            "importance": 0.5,
            "access_count": 1,
            "useful_count": 0,
            "confidence": 1.0,
        }
    )
    _run(store, {"memory_id": 7, "useful": True}, monkeypatch)
    mid, new_v = store.value_writes[0]
    # Started from VALUE_PRIOR (0.5) and rose on the positive verdict.
    expected, _ = value_learning.td_update(
        value_learning.VALUE_PRIOR,
        value_learning.outcome_to_reward(True, False, 0.5),
    )
    assert abs(new_v - expected) < 1e-9


def test_value_write_failure_is_non_fatal(monkeypatch):
    class _BoomStore(_FakeStore):
        def update_memory_value(self, memory_id, value):
            raise RuntimeError("value column missing")

    store = _BoomStore(
        {
            "id": 8,
            "content": "q",
            "value": 0.5,
            "importance": 0.5,
            "access_count": 1,
            "useful_count": 1,
            "confidence": 0.5,
        }
    )
    out = _run(store, {"memory_id": 8, "useful": True}, monkeypatch)
    # Rating still succeeds; value simply omitted from the response.
    assert out["rated"] is True
    assert "value" not in out
