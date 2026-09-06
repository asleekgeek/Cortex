"""Real CLI import guards and persistent pending cadence; stdlib only."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_GUARDED_CLI = """
import importlib.abc
import json
import runpy
import sys
attempted = []
class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if fullname.startswith('mcp_server.infrastructure'):
            attempted.append(fullname)
            raise AssertionError('unexpected infrastructure import: ' + fullname)
sys.meta_path.insert(0, Guard())
runpy.run_module('mcp_server.hooks.post_tool_capture', run_name='__main__')
loaded = [name for name in sys.modules if name.startswith('mcp_server.infrastructure')]
assert not attempted, attempted
assert not loaded, loaded
print(json.dumps({'attempted': attempted, 'loaded': loaded}))
"""

_ADMITTED_CHILD = """
import os
from pathlib import Path
from mcp_server.hooks import post_tool_capture as hook
root = Path(os.environ['CORTEX_CLAUDE_DIR'])
def advance():
    with (root / 'advances.txt').open('a', encoding='utf-8') as output:
        output.write('advanced\\n')
hook._run_cascade = advance
hook._store_memory = lambda *args: None
hook.main()
"""


class CaptureModeProcesses(unittest.TestCase):
    def setUp(self):
        self.tree = tempfile.TemporaryDirectory(prefix="cortex-capture-mode-test-")
        self.addCleanup(self.tree.cleanup)
        self.root = Path(self.tree.name)
        key = hashlib.sha256(b"session").hexdigest()
        self.counter = self.root / "methodology" / "hook-cascade" / key / "counter.json"
        self.counter.parent.mkdir(parents=True)

    def seed(self, count):
        self.counter.write_text(json.dumps({"tool_calls": count, "completed": 0}))
        return self.counter.read_bytes()

    def child(self, mode, tool, script=_GUARDED_CLI):
        env = {**os.environ, "CORTEX_CLAUDE_DIR": str(self.root), "DATABASE_URL": ""}
        env.pop("CORTEX_HEADLESS_AUTHORING_CHILD", None)
        env["CORTEX_CAPTURE_MODE"] = mode
        event = {
            "tool_name": tool,
            "transcript_path": str(self.root / "session.jsonl"),
            "tool_response": "This output passes the existing capture length filter.",
        }
        result = subprocess.run(
            [sys.executable, "-S", "-c", script],
            cwd=Path(__file__).resolve().parents[2],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            env=env,
            timeout=10,  # source: plugin.json PostToolUse capture timeout.
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def assert_no_import(self, result, original):
        self.assertEqual(json.loads(result.stdout), {"attempted": [], "loaded": []})
        self.assertEqual(self.counter.read_bytes(), original)
        self.assertFalse((self.root / "advances.txt").exists())
        # The excluded path does not even create a lock or store file.
        files = sorted(path for path in self.root.rglob("*") if path.is_file())
        self.assertEqual(files, [self.counter])

    def test_reads_never_import_infrastructure_at_twentieth_event_or_pending_due(self):
        # source: W2-4 preserves the existing 20-event cascade interval.
        for count in (19, 20, 40):
            original = self.seed(count)
            for tool in (
                "Read",
                "NotebookRead",
                "Glob",
                "Grep",
                "WebFetch",
                "WebSearch",
            ):
                result = self.child("writes-only", tool)
                self.assert_no_import(result, original)
                self.assertIn("CORTEX_CAPTURE_MODE=writes-only", result.stderr)

    def test_off_and_invalid_never_import_or_touch_due_state(self):
        original = self.seed(20)
        for mode in ("off", "", "Full", "write-only"):
            for tool in ("Read", "Write", "Bash"):
                result = self.child(mode, tool)
                self.assert_no_import(result, original)
                self.assertIn("CORTEX_CAPTURE_MODE", result.stderr)

    def test_pending_cascade_waits_for_next_admitted_event(self):
        original = self.seed(20)
        self.assert_no_import(self.child("writes-only", "Read"), original)
        result = self.child("writes-only", "Bash", _ADMITTED_CHILD)
        self.assertNotIn("cascade failed", result.stderr)
        self.assertEqual(
            json.loads(self.counter.read_text()), {"tool_calls": 21, "completed": 20}
        )
        self.assertEqual((self.root / "advances.txt").read_text(), "advanced\n")

    def test_full_still_counts_an_ignored_tool_at_due_event(self):
        self.seed(19)
        result = self.child("full", "Task", _ADMITTED_CHILD)
        self.assertIn("skip Task: low_value_tool:Task", result.stderr)
        self.assertEqual(
            json.loads(self.counter.read_text()), {"tool_calls": 20, "completed": 20}
        )
        self.assertEqual((self.root / "advances.txt").read_text(), "advanced\n")


if __name__ == "__main__":
    unittest.main()
