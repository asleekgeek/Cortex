"""Silent-except sweep (audit 2026-07-11): CLS causal-edge persistence.

``_store_causal_edges`` swallows a per-edge ``insert_relationship``
failure so one bad edge never kills the whole consolidation batch (a
legitimate fallback). Before this fix that swallow had zero log signal
-- a schema mismatch or FK violation on every edge would silently zero
out causal-graph growth every consolidation cycle, indistinguishable
from "no causal edges found this cycle" (the ``reason_for_zero``
diagnostic path in this same module).
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from mcp_server.handlers.consolidation.cls import _store_causal_edges
from mcp_server.observability import silent_failure


@pytest.fixture(autouse=True)
def _reset():
    silent_failure.reset()
    yield
    silent_failure.reset()


def test_insert_relationship_failure_is_logged_and_edge_is_skipped(caplog):
    store = MagicMock()
    store.insert_relationship.side_effect = RuntimeError("FK violation")
    all_entities = [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
    edges = [{"source": "A", "target": "B", "is_directed": True, "strength": 0.8}]

    with caplog.at_level("WARNING", logger="mcp_server.observability.silent_failure"):
        count = _store_causal_edges(store, all_entities, edges)

    assert count == 0  # behavior-preserving: bad edge is skipped, not counted
    assert any("cls.causal_edge_persist" in r.message for r in caplog.records)
    assert any("FK violation" in r.message for r in caplog.records)


def test_one_bad_edge_does_not_block_the_rest(caplog):
    store = MagicMock()
    calls = {"n": 0}

    def flaky_insert(payload):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("first edge broken")

    store.insert_relationship.side_effect = flaky_insert
    all_entities = [
        {"id": 1, "name": "A"},
        {"id": 2, "name": "B"},
        {"id": 3, "name": "C"},
    ]
    edges = [
        {"source": "A", "target": "B", "is_directed": True, "strength": 0.8},
        {"source": "B", "target": "C", "is_directed": True, "strength": 0.5},
    ]

    with caplog.at_level("WARNING", logger="mcp_server.observability.silent_failure"):
        count = _store_causal_edges(store, all_entities, edges)

    assert count == 1  # second edge still landed
    assert any("cls.causal_edge_persist" in r.message for r in caplog.records)
