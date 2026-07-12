"""Output-schema validation for checkpoint (#99 regression guard).

A strict MCP client validates every tool result against the tool's
declared ``outputSchema``. Prior to #99, ``outputSchema.required``
included ``action``, but neither ``_save_checkpoint`` nor
``_restore_context`` (success paths) nor the error paths populated it —
every response, including successful saves, failed client-side output
validation. This test runs each return path through
``jsonschema.validate`` and asserts none of them raise.
"""

from __future__ import annotations

import jsonschema
import pytest

from mcp_server.handlers.checkpoint import handler, schema

_OUTPUT_SCHEMA = schema["outputSchema"]


class TestCheckpointOutputSchemaValidation:
    @pytest.mark.asyncio
    async def test_save_success_validates(self):
        result = await handler({"action": "save", "current_task": "t"})
        jsonschema.validate(result, _OUTPUT_SCHEMA)

    @pytest.mark.asyncio
    async def test_restore_success_validates(self):
        result = await handler({"action": "restore"})
        jsonschema.validate(result, _OUTPUT_SCHEMA)

    @pytest.mark.asyncio
    async def test_missing_action_error_validates(self):
        result = await handler({})
        jsonschema.validate(result, _OUTPUT_SCHEMA)

    @pytest.mark.asyncio
    async def test_none_args_error_validates(self):
        result = await handler(None)
        jsonschema.validate(result, _OUTPUT_SCHEMA)

    @pytest.mark.asyncio
    async def test_unknown_action_error_validates(self):
        result = await handler({"action": "delete"})
        jsonschema.validate(result, _OUTPUT_SCHEMA)

    def test_action_not_in_required(self):
        """The fix removes `action` from required (it can never be a
        valid enum member on the error paths that fire precisely when
        it's absent/invalid) rather than fabricating a value."""
        assert "required" not in _OUTPUT_SCHEMA or "action" not in _OUTPUT_SCHEMA.get(
            "required", []
        )

    @pytest.mark.asyncio
    async def test_save_response_carries_action_save(self):
        result = await handler({"action": "save", "current_task": "t"})
        assert result["action"] == "save"

    @pytest.mark.asyncio
    async def test_restore_response_carries_action_restore(self):
        result = await handler({"action": "restore"})
        assert result["action"] == "restore"
