"""Tests for emit_injection_receipt — blame path T1 emitter.

The emitter maps the BOUND response payload to receipt items. Named
degradation modes only: no injection → no receipt; store write failure
(I/O) → degrade to None. A payload entry without memory_id is an
upstream contract violation and must RAISE — pg_recall and
inject_triggered_memories guarantee the id by construction, so
swallowing it would hide a regression as silently-missing receipts.
"""

from __future__ import annotations

import pytest

from mcp_server.handlers.injection_receipts import emit_injection_receipt


class _Store:
    def __init__(self, fail: bool = False) -> None:
        self.calls: list[dict] = []
        self.fail = fail

    def insert_injection_receipt(
        self, channel: str, items: list[dict], session_id: str | None = None
    ) -> int:
        if self.fail:
            raise RuntimeError("db down")
        self.calls.append(
            {"channel": channel, "items": items, "session_id": session_id}
        )
        return 42


def _mems() -> list[dict]:
    return [
        {"memory_id": 11, "score": 0.9, "content": "a"},
        {"memory_id": 7, "score": None, "content": "b"},
    ]


def test_items_mirror_bound_payload() -> None:
    store = _Store()
    rid = emit_injection_receipt(store, _mems())
    assert rid == 42
    assert store.calls[0]["items"] == [
        {"memory_id": 11, "rank": 0, "score": 0.9},
        {"memory_id": 7, "rank": 1, "score": None},
    ]
    assert store.calls[0]["channel"] == "recall"
    assert store.calls[0]["session_id"] is None


def test_empty_payload_emits_nothing() -> None:
    store = _Store()
    assert emit_injection_receipt(store, []) is None
    assert store.calls == []


def test_missing_memory_id_is_a_loud_contract_violation() -> None:
    store = _Store()
    with pytest.raises(KeyError):
        emit_injection_receipt(store, [{"content": "x", "score": 1.0}])
    assert store.calls == []


def test_store_failure_degrades_to_none() -> None:
    assert emit_injection_receipt(_Store(fail=True), _mems()) is None
