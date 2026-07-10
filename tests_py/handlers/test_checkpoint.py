"""Tests for mcp_server.handlers.checkpoint — hippocampal replay."""

from unittest.mock import patch

import pytest


class TestCheckpointSave:
    @pytest.mark.asyncio
    async def test_save_returns_checkpoint_id(self):
        from mcp_server.handlers.checkpoint import handler

        result = await handler(
            {
                "action": "save",
                "session_id": "test-session",
                "current_task": "Writing tests",
                "files_being_edited": ["test.py"],
                "key_decisions": ["Use SQLite"],
                "open_questions": ["How to scale?"],
                "next_steps": ["Run tests"],
                "active_errors": [],
                "custom_context": "Extra info",
            }
        )
        assert result["status"] == "saved"
        assert "checkpoint_id" in result

    @pytest.mark.asyncio
    async def test_save_minimal(self):
        from mcp_server.handlers.checkpoint import handler

        result = await handler({"action": "save"})
        assert result["status"] == "saved"

    @pytest.mark.asyncio
    async def test_missing_action_returns_error(self):
        from mcp_server.handlers.checkpoint import handler

        result = await handler({})
        assert "error" in result

    @pytest.mark.asyncio
    async def test_none_args_returns_error(self):
        from mcp_server.handlers.checkpoint import handler

        result = await handler(None)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_unknown_action_returns_error(self):
        from mcp_server.handlers.checkpoint import handler

        result = await handler({"action": "delete"})
        assert "error" in result


class TestCheckpointRestore:
    @pytest.mark.asyncio
    async def test_restore_without_prior_save(self):
        from mcp_server.handlers.checkpoint import handler

        result = await handler({"action": "restore"})
        assert result["status"] == "restored"
        assert result["checkpoint"] is False
        assert isinstance(result["anchored_count"], int)
        assert isinstance(result["recent_count"], int)
        assert isinstance(result["hot_count"], int)
        assert "formatted" in result

    @pytest.mark.asyncio
    async def test_save_then_restore(self):
        from mcp_server.handlers.checkpoint import handler

        # Save
        save_result = await handler(
            {
                "action": "save",
                "current_task": "Building memory system",
                "files_being_edited": ["memory.py", "store.py"],
                "key_decisions": ["Use thermodynamic model"],
            }
        )
        assert save_result["status"] == "saved"

        # Restore
        restore_result = await handler({"action": "restore"})
        assert restore_result["status"] == "restored"
        assert restore_result["checkpoint"] is True
        assert "Building memory system" in restore_result["formatted"]
        assert "memory.py" in restore_result["formatted"]

    @pytest.mark.asyncio
    async def test_restore_with_directory(self):
        from mcp_server.handlers.checkpoint import handler

        result = await handler(
            {
                "action": "restore",
                "directory": "/project/src",
            }
        )
        assert result["status"] == "restored"

    @pytest.mark.asyncio
    async def test_multiple_saves_restore_latest(self):
        from mcp_server.handlers.checkpoint import handler

        await handler({"action": "save", "current_task": "First task"})
        await handler({"action": "save", "current_task": "Second task"})

        result = await handler({"action": "restore"})
        assert result["checkpoint"] is True
        assert "Second task" in result["formatted"]


class TestCheckpointSchema:
    def test_schema_exists(self):
        from mcp_server.handlers.checkpoint import schema

        assert "description" in schema
        assert "inputSchema" in schema
        assert schema["inputSchema"]["required"] == ["action"]


class TestResolveSessionId:
    """Q2 alignment: checkpoint.save's session_id resolution chain."""

    def test_explicit_session_id_wins(self):
        from mcp_server.handlers.checkpoint import _resolve_session_id

        assert _resolve_session_id("explicit-123") == "explicit-123"

    def test_falls_back_to_registry_stem_when_absent(self):
        from mcp_server.handlers import checkpoint

        with patch(
            "mcp_server.handlers.checkpoint.current_window_session",
            return_value="7374abf5-stem",
        ):
            assert checkpoint._resolve_session_id(None) == "7374abf5-stem"

    def test_falls_back_to_default_when_registry_empty(self):
        from mcp_server.handlers import checkpoint

        with patch(
            "mcp_server.handlers.checkpoint.current_window_session",
            return_value=None,
        ):
            assert checkpoint._resolve_session_id(None) == "default"

    def test_registry_exception_degrades_to_default(self):
        from mcp_server.handlers import checkpoint

        with patch(
            "mcp_server.handlers.checkpoint.current_window_session",
            side_effect=RuntimeError("boom"),
        ):
            assert checkpoint._resolve_session_id(None) == "default"

    def test_empty_string_explicit_falls_back(self):
        """An explicit but empty session_id degrades the same as absence
        (falsy check) rather than persisting an empty string."""
        from mcp_server.handlers import checkpoint

        with patch(
            "mcp_server.handlers.checkpoint.current_window_session",
            return_value="stem-x",
        ):
            assert checkpoint._resolve_session_id("") == "stem-x"

    @pytest.mark.asyncio
    async def test_save_uses_registry_stem_when_session_id_omitted(self):
        """Live proof: a save with no session_id arg persists the
        registry's canonical stem, not the hardcoded 'default'."""
        from mcp_server.handlers.checkpoint import handler

        with patch(
            "mcp_server.handlers.checkpoint.current_window_session",
            return_value="live-stem-abc",
        ):
            result = await handler({"action": "save", "current_task": "t"})
        assert result["status"] == "saved"
