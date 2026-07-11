"""Silent-except sweep (audit 2026-07-11): try_block_replica_upsert.

This is the checkpoint/rethink block-sync path (memory-architecture.md:
``.pending-sync`` -> Cortex DB replica of ``memory-tool.sh`` writes).
Both its SQL statements were a bare ``except Exception: return False,
None`` -- the exact SQL-error-swallowed shape as the spread_activation
incident (a broken SELECT/UPDATE is indistinguishable from "no existing
block row", so the caller silently INSERTS A DUPLICATE instead of
superseding, with zero signal).
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from mcp_server.handlers.remember_helpers import try_block_replica_upsert
from mcp_server.observability import silent_failure


@pytest.fixture(autouse=True)
def _reset():
    silent_failure.reset()
    yield
    silent_failure.reset()


def test_select_failure_is_logged_and_falls_back_to_insert_path(caplog):
    store = MagicMock()
    store._execute.side_effect = RuntimeError("relation does not exist")

    with caplog.at_level("WARNING", logger="mcp_server.observability.silent_failure"):
        updated, existing_id = try_block_replica_upsert(
            content="checkpoint body",
            embedding=None,
            tags=["memory-replica", "vpath:/memories/engineer/checkpoint.md"],
            source="block",
            store=store,
        )

    assert updated is False
    assert existing_id is None
    assert any(
        "remember_helpers.block_supersede_select" in r.message for r in caplog.records
    )


def test_update_failure_is_logged(caplog):
    store = MagicMock()
    # SELECT succeeds and finds an existing row...
    select_result = MagicMock()
    select_result.fetchall.return_value = [{"id": 7}]
    # ...but the subsequent UPDATE raises.
    store._execute.side_effect = [select_result, RuntimeError("deadlock detected")]

    with caplog.at_level("WARNING", logger="mcp_server.observability.silent_failure"):
        updated, existing_id = try_block_replica_upsert(
            content="checkpoint body v2",
            embedding=None,
            tags=["memory-replica", "vpath:/memories/engineer/checkpoint.md"],
            source="block",
            store=store,
        )

    assert updated is False
    assert existing_id is None
    assert any(
        "remember_helpers.block_supersede_update" in r.message for r in caplog.records
    )
