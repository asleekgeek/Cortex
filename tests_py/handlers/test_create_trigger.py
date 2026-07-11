"""Tests for mcp_server.handlers.create_trigger — source_memory_id
traceability added for M-D6 (7.6) lesson promotion.

Contract under test (from create_trigger.py):
  POST-1  source_memory_id, when supplied, round-trips into the response
          and is persisted on the prospective_memories row.
  POST-2  source_memory_id defaults to None when omitted — existing
          direct-creation callers are unaffected.
"""

from __future__ import annotations

import pytest


class TestCreateTriggerSourceMemoryId:
    @pytest.mark.asyncio
    async def test_source_memory_id_round_trips(self):
        from mcp_server.handlers.create_trigger import handler

        result = await handler(
            {
                "content": "Promoted from a lesson: recall pgvector index rebuild.",
                "trigger_condition": "pgvector",
                "trigger_type": "keyword",
                "source_memory_id": 4198018,
            }
        )

        assert result["created"] is True
        assert result["source_memory_id"] == 4198018

    @pytest.mark.asyncio
    async def test_source_memory_id_defaults_to_none(self):
        from mcp_server.handlers.create_trigger import handler

        result = await handler(
            {
                "content": "Direct trigger, not promoted from a lesson.",
                "trigger_condition": "direct-trigger-test",
                "trigger_type": "keyword",
            }
        )

        assert result["created"] is True
        assert result["source_memory_id"] is None

    @pytest.mark.asyncio
    async def test_persisted_source_memory_id_readable_via_active_triggers(self):
        from mcp_server.handlers.create_trigger import _get_store, handler

        result = await handler(
            {
                "content": "Promoted trigger, readback check.",
                "trigger_condition": "readback-check-marker",
                "trigger_type": "keyword",
                "source_memory_id": 555,
            }
        )
        assert result["created"] is True

        store = _get_store()
        active = store.get_active_prospective_memories()
        row = next(r for r in active if r["id"] == result["trigger_id"])
        assert row["source_memory_id"] == 555
