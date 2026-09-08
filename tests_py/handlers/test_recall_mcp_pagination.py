"""Actual registered MCP calls: ID paging and rooted disclosure boundaries."""

from __future__ import annotations

import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from mcp.server.mcpserver import MCPServer

from mcp_server import tool_registry_memory as registry
from mcp_server.core.response_budget import MAX_RESPONSE_CHARS
from mcp_server.handlers import recall
from mcp_server.handlers._tool_meta import apply_output_schemas, apply_param_docs


def server() -> MCPServer:
    result = MCPServer(name="recall-pagination-test")
    registry._register_recall(result)
    apply_output_schemas(result, {"recall": recall.schema})
    apply_param_docs(result, {"recall": recall.schema})
    return result


def invoke(root, row, arguments, budget=MAX_RESPONSE_CHARS):
    settings = SimpleNamespace(MAX_RESPONSE_CHARS=budget)
    store = Mock(get_memory=Mock(return_value=row))
    with patch.dict("os.environ", {"CORTEX_ROOT_AGENT_TOPIC": root or ""}):
        with (
            patch.object(recall, "_get_store", return_value=store),
            patch.object(recall, "get_memory_settings", return_value=settings),
            patch("mcp_server.core.telemetry.record"),
        ):
            result = asyncio.run(server().call_tool("recall", arguments))
    return result.structured_content


class RegisteredPaging(unittest.TestCase):
    def test_both_schemas_expose_paging_and_keep_query_required(self):
        for root in ("", "agent-a"):
            with patch.dict("os.environ", {"CORTEX_ROOT_AGENT_TOPIC": root}):
                tool = asyncio.run(server().list_tools())[0]
            schema = tool.input_schema
            self.assertIn("memory_id", schema["properties"])
            self.assertEqual(schema["properties"]["content_offset"]["default"], 0)
            self.assertIn("query", schema["required"])
            self.assertEqual("agent_topic" in schema["properties"], not bool(root))

    def test_unrooted_preserves_existing_fetch_compatibility(self):
        row = {"id": 7, "content": "abcdef", "agent_context": "agent-b"}
        result = invoke(
            None,
            row,
            {
                "query": "ignored",
                "memory_id": 7,
                "content_offset": 2,
                "agent_topic": "agent-a",
            },
        )
        memory = result["memories"][0]
        self.assertEqual(memory["id"], 7)
        self.assertEqual(memory["content"], "cdef")
        self.assertEqual(memory["content_offset"], 2)
        self.assertEqual(memory["content_length"], 6)

    def test_rooted_same_scope_default_offset_returns_the_actual_memory(self):
        row = {"id": 7, "content": "permitted", "agent_context": "agent-a"}
        result = invoke("agent-a", row, {"query": "ignored", "memory_id": 7})
        self.assertEqual(result["memories"][0]["content"], "permitted")
        self.assertEqual(result["memories"][0]["content_offset"], 0)

    def test_rooted_other_scope_global_and_absent_are_indistinguishable(self):
        arguments = {"query": "ignored", "memory_id": 7}
        missing = invoke("agent-a", None, arguments)
        for extra in (
            {"agent_context": "agent-b"},
            {"agent_context": "agent-b", "is_global": True},
            {},
            {"agent_context": None},
        ):
            row = {"id": 7, "content": "must not disclose", **extra}
            self.assertEqual(invoke("agent-a", row, arguments), missing)
        self.assertEqual(missing["memories"], [])
        self.assertEqual(missing["count"], 0)

    def test_rooted_62503_character_document_pages_through_real_wrapper(self):
        # source: W4-4's 62,503-character documentation-memory finding.
        body = "".join(str(index % 10) for index in range(62_503))
        row = {"id": 7, "content": body, "agent_context": "agent-a"}
        arguments = {"query": "ignored", "memory_id": 7}
        first = invoke("agent-a", row, arguments, budget=len(body))
        page = first["memories"][0]
        self.assertTrue(page["truncated"])
        self.assertEqual(page["id"], 7)
        offset = len(page["content"])
        second = invoke(
            "agent-a", row, {**arguments, "content_offset": offset}, budget=len(body)
        )
        self.assertEqual(page["content"] + second["memories"][0]["content"], body)
        self.assertEqual(second["memories"][0]["content_length"], len(body))
        self.assertEqual(row["content"], body)


if __name__ == "__main__":
    unittest.main()
