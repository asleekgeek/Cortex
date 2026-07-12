"""Unit tests for mcp_server.tool_error_handler._classify_error.

Focus: the anti-silent-fallback boundary (fix/bare-container-contract review
finding #2). RuntimeError raised by memory_store._construct_store when an
explicit DATABASE_URL is unreachable must NOT be reclassified into the
generic "database_not_connected" PostgreSQL-setup guide — that guide tells
the user to install/configure Postgres, discarding the actually load-bearing
information (the fallback was refused on purpose; unset DATABASE_URL or opt
in via CORTEX_ALLOW_SQLITE_FALLBACK=1).
"""

from __future__ import annotations

from mcp_server.tool_error_handler import _classify_error


class TestExplicitDatabaseUrlUnreachableClassification:
    def test_explicit_refusal_message_is_not_masked(self):
        exc = RuntimeError(
            "explicit DATABASE_URL unreachable "
            "(url=postgresql://127.0.0.1:1/x): "
            "OperationalError: connection failed: connection to server at "
            '"127.0.0.1", port 1 failed: Connection refused; refusing '
            "silent SQLite fallback; unset DATABASE_URL for sandbox mode "
            "or set CORTEX_ALLOW_SQLITE_FALLBACK=1 to opt in"
        )
        error_type, message = _classify_error(exc)
        assert error_type == "explicit_database_url_unreachable"
        assert "refusing silent SQLite fallback" in message

    def test_generic_connection_refused_still_classified_as_db_not_connected(self):
        """Regression guard: unrelated connection errors (the CLI/postgresql
        required path, or any other psycopg failure) must keep getting the
        friendly setup guide — only OUR marker string bypasses it."""
        exc = RuntimeError(
            "PostgreSQL connection failed (url=postgresql://127.0.0.1:1/x): "
            "OperationalError: connection refused"
        )
        error_type, message = _classify_error(exc)
        assert error_type == "database_not_connected"


class TestGenericClassification:
    def test_missing_extension_classified(self):
        exc = Exception('type "vector" does not exist')
        error_type, _ = _classify_error(exc)
        assert error_type == "missing_extension"

    def test_unrecognized_error_falls_through_unclassified(self):
        exc = ValueError("some unrelated application error")
        error_type, message = _classify_error(exc)
        assert error_type == "ValueError"
        assert message == "some unrelated application error"
