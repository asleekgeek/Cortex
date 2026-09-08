"""Bound database round trips on the first ordinary remember call."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from mcp_server.infrastructure.pg_store_engram import PgEngramMixin
from tests_py.conftest import _USE_PG


def _store(existing):
    return SimpleNamespace(
        _execute=Mock(return_value=SimpleNamespace(fetchone=lambda: {"c": existing})),
        _conn=SimpleNamespace(commit=Mock()),
    )


def test_initial_slot_allocation_has_constant_statement_count():
    store = _store(0)
    # source: write_post_store's actual default allocation, reproduced in the
    # native ordinary-remember fixture (5000 INSERTs before this correction).
    PgEngramMixin.init_engram_slots(store, 5000)
    assert store._execute.call_count == 2
    store._conn.commit.assert_called_once_with()


@pytest.mark.parametrize("existing,requested", [(5, 5), (5, 3), (0, 0)])
def test_existing_capacity_does_not_write_or_commit(existing, requested):
    store = _store(existing)
    PgEngramMixin.init_engram_slots(store, requested)
    assert store._execute.call_count == 1
    store._conn.commit.assert_not_called()


def test_non_integral_capacity_is_rejected_before_insert():
    store = _store(0)
    with pytest.raises(TypeError):
        PgEngramMixin.init_engram_slots(store, 3.5)
    assert store._execute.call_count == 1
    store._conn.commit.assert_not_called()


def test_allocation_failure_propagates_without_committing():
    store = _store(0)
    store._execute.side_effect = [
        SimpleNamespace(fetchone=lambda: {"c": 0}),
        RuntimeError("allocation unavailable"),
    ]
    with pytest.raises(RuntimeError, match="allocation unavailable"):
        PgEngramMixin.init_engram_slots(store, 5)
    store._conn.commit.assert_not_called()


@pytest.mark.skipif(not _USE_PG, reason="requires isolated PostgreSQL")
@pytest.mark.parametrize("occupied", [[], [0, 1], [0, 3]])
def test_native_slots_preserve_existing_values_holes_and_repeat(occupied):
    from mcp_server.infrastructure.pg_store import PgMemoryStore

    store = PgMemoryStore()
    try:
        for slot in occupied:
            store._execute(
                "INSERT INTO engram_slots VALUES (%s, 0.75, '2026-01-01Z')",
                (slot,),
            )
        before = {row["slot_index"]: row for row in store.get_all_engram_slots()}
        store.init_engram_slots(5)
        first = {row["slot_index"]: row for row in store.get_all_engram_slots()}
        # The original loop begins at COUNT(*), including for a sparse table.
        assert first.keys() == set(occupied) | set(range(len(occupied), 5))
        for slot, row in first.items():
            if slot in before:
                assert row == before[slot]
            else:
                assert row == {
                    "slot_index": slot,
                    "excitability": 0.5,
                    "last_activated": None,
                }
        store.init_engram_slots(5)
        assert store.get_all_engram_slots() == list(first.values())
    finally:
        store.close()
