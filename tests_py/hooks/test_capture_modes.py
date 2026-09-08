"""Capture-mode policy and lifecycle tests; stdlib only, no store/model."""

from __future__ import annotations

import io
import os
import sys
import unittest
from contextlib import contextmanager, redirect_stderr
from types import ModuleType
from unittest.mock import patch

from mcp_server.hooks import post_tool_capture as hook
from mcp_server.hooks._capture_mode import capture_skip_reason

_WRITES = ("Edit", "Write", "Bash", "MultiEdit", "NotebookEdit")
_READS = ("Read", "NotebookRead", "Glob", "Grep", "WebFetch", "WebSearch", "Task")


def event(tool):
    return {
        "tool_name": tool,
        "tool_input": {"file_path": "example.py", "command": "cat example.py"},
        "tool_response": "This output passes the existing capture length filter.",
    }


@contextmanager
def capture_mode(mode):
    with patch.dict(os.environ):
        if mode is None:
            os.environ.pop("CORTEX_CAPTURE_MODE", None)
        else:
            os.environ["CORTEX_CAPTURE_MODE"] = mode
        yield


class CaptureModes(unittest.TestCase):
    def test_policy_matrix(self):
        for tool in _WRITES + _READS:
            self.assertIsNone(capture_skip_reason("full", tool, _WRITES))
            self.assertIsNotNone(capture_skip_reason("off", tool, _WRITES))
            reason = capture_skip_reason("writes-only", tool, _WRITES)
            self.assertEqual(reason is None, tool in _WRITES)

    def test_default_and_full_keep_captures_and_count_ignored_tools(self):
        for mode in (None, "full"):
            with capture_mode(mode), redirect_stderr(io.StringIO()):
                with (
                    patch.object(hook, "_maybe_run_cascade") as cascade,
                    patch.object(hook, "_store_memory") as store,
                ):
                    for tool in _WRITES + _READS:
                        hook.process_event(event(tool))
                    self.assertEqual(cascade.call_count, len(_WRITES + _READS))
                    captured = [call.args[0] for call in store.call_args_list]
                    self.assertEqual(captured, list(_WRITES + _READS[:-1]))

    def test_writes_only_preserves_existing_write_filter(self):
        with capture_mode("writes-only"), redirect_stderr(io.StringIO()):
            with (
                patch.object(hook, "_maybe_run_cascade") as cascade,
                patch.object(hook, "_store_memory") as store,
            ):
                for tool in _WRITES:
                    hook.process_event(event(tool))
                self.assertEqual(store.call_count, len(_WRITES))
                short_event = {**event("Bash"), "tool_response": "short"}
                hook.process_event(short_event)
                self.assertEqual(store.call_count, len(_WRITES))
                self.assertEqual(cascade.call_count, len(_WRITES) + 1)

    def assert_skipped(self, mode, tools):
        diagnostic = io.StringIO()
        with capture_mode(mode), redirect_stderr(diagnostic):
            with (
                patch.object(hook, "_normalize_output") as normalize,
                patch.object(hook, "_maybe_run_cascade") as cascade,
                patch.object(hook, "_store_memory") as store,
            ):
                for tool in tools:
                    hook.process_event(event(tool))
                normalize.assert_not_called()
                cascade.assert_not_called()
                store.assert_not_called()
        return diagnostic.getvalue()

    def test_writes_only_excludes_reads_before_processing(self):
        diagnostic = self.assert_skipped("writes-only", _READS)
        self.assertIn("CORTEX_CAPTURE_MODE=writes-only", diagnostic)

    def test_off_excludes_every_tool_before_processing(self):
        diagnostic = self.assert_skipped("off", _WRITES + _READS)
        self.assertIn("CORTEX_CAPTURE_MODE=off", diagnostic)

    def test_invalid_values_report_actual_value_without_enabling_capture(self):
        for mode in ("", "Full", " full ", "write-only"):
            diagnostic = self.assert_skipped(mode, _WRITES + _READS)
            self.assertIn(f"invalid CORTEX_CAPTURE_MODE={mode!r}", diagnostic)
            self.assertIn("expected full, writes-only or off", diagnostic)

    def test_cli_cleanup_for_admitted_events_includes_failures(self):
        transitions = []

        @contextmanager
        def cleanup():
            transitions.append("enter")
            try:
                yield
            finally:
                transitions.append("exit")

        module = ModuleType("mcp_server.hooks._store_lifecycle")
        module.close_shared_store_on_exit = cleanup
        with capture_mode("full"), patch.dict(sys.modules, {module.__name__: module}):
            for error in (None, RuntimeError("failure"), SystemExit(1)):
                with patch.object(hook, "process_event", side_effect=error) as process:
                    try:
                        hook._dispatch_with_store_cleanup(event("Read"))
                    except (RuntimeError, SystemExit) as caught:
                        self.assertIs(caught, error)
                    process.assert_called_once()
                self.assertEqual(transitions[-2:], ["enter", "exit"])
        self.assertEqual(len(transitions), 6)

    def test_cli_excluded_event_never_enters_cleanup(self):
        with capture_mode("off"), redirect_stderr(io.StringIO()):
            with patch.object(hook, "process_event") as process:
                hook._dispatch_with_store_cleanup(event("Write"))
                process.assert_not_called()


if __name__ == "__main__":
    unittest.main()
