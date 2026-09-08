"""Executed compression boundaries against the original source snapshot."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

from mcp_server.core import compression as policy
from mcp_server.handlers.consolidation import compression
from tests_py.core.test_compression_encode_count import _FakeStore, _mem
from tests_py.handlers._remember_bulk_fakes import TraceEngine, original


class Clock(datetime):
    value = datetime(2026, 9, 6, tzinfo=timezone.utc)

    @classmethod
    def now(cls, zone=None):
        return cls.value


SETTINGS = SimpleNamespace(
    COMPRESSION_GIST_AGE_HOURS=168.0, COMPRESSION_TAG_AGE_HOURS=720.0
)


def run_compression(reference=False, setup=None):
    engine, store = TraceEngine(), _FakeStore()
    memory = _mem(2000)
    stats = {"compressed_to_gist": 0, "compressed_to_tag": 0}
    if setup:
        setup(engine, memory)
    namespace = original(compression, "compression") if reference else vars(compression)
    try:
        namespace["_compress_memory"](store, SETTINGS, engine, memory, stats)
        error = None
    except BaseException as exc:
        error = (type(exc), str(exc))
    return store, engine, stats, error


class CompressionBoundaries(unittest.TestCase):
    def assert_same(self, before, after):
        self.assertEqual(before[0].archives, after[0].archives)
        self.assertEqual(before[0].updates, after[0].updates)
        self.assertEqual(before[2:], after[2:])

    def test_missing_gist_vector_preserves_scalar_encodes_and_write_order(self):
        def setup(engine, memory):
            memory["created_at"] = "2000-01-01T00:00:00+00:00"
            scalar = engine.encode

            def first_none(text):
                if not engine.scalars:
                    engine.scalars.append(text)
                    return None
                return scalar(text)

            engine.encode = first_none

        old, new = run_compression(True, setup), run_compression(setup=setup)
        self.assert_same(old, new)
        self.assertEqual(len(old[1].scalars), 3)
        self.assertEqual(new[1].scalars, old[1].scalars)
        self.assertEqual(new[1].batches, [])
        self.assertEqual([row[3] for row in new[0].updates], [1, 2])

    def test_tag_runtime_error_keeps_prior_gist_archive_and_update(self):
        def setup(engine, memory):
            memory["created_at"] = "2000-01-01T00:00:00+00:00"
            tag = policy.generate_tag(policy.extract_gist(memory["content"]), memory)
            engine.failures[tag] = RuntimeError("late tag failure")

        with self.assertLogs(compression.logger, level="ERROR"):
            old, new = run_compression(True, setup), run_compression(setup=setup)
        self.assert_same(old, new)
        self.assertEqual([row[3] for row in new[0].updates], [1])
        self.assertEqual(new[2], {"compressed_to_gist": 1, "compressed_to_tag": 0})

    def test_tag_interrupt_preserves_committed_gist_and_is_not_swallowed(self):
        def setup(engine, memory):
            memory["created_at"] = "2000-01-01T00:00:00+00:00"
            tag = policy.generate_tag(policy.extract_gist(memory["content"]), memory)
            engine.failures[tag] = KeyboardInterrupt("late stop")

        old, new = run_compression(True, setup), run_compression(setup=setup)
        self.assert_same(old, new)
        self.assertEqual(new[3][0], KeyboardInterrupt)
        self.assertEqual([row[3] for row in new[0].updates], [1])

    def test_gist_error_retains_precedence_over_malformed_tag_error(self):
        memory = {
            "id": 1,
            "content": "gist text",
            "created_at": datetime.now(timezone.utc),
        }
        for reference in (False, True):
            engine, store = TraceEngine(), _FakeStore()
            engine.failures["gist text"] = RuntimeError("gist failed first")
            namespace = (
                original(compression, "compression") if reference else vars(compression)
            )
            with self.assertRaisesRegex(RuntimeError, "gist failed first"):
                namespace["_compress_to_tag_from_gist"](store, engine, memory, {})
            self.assertEqual(store.archives + store.updates, [])
            self.assertEqual(engine.scalars, ["gist text"])

    def test_prefrozen_schedule_changes_a_real_threshold_crossing(self):
        start = datetime(2026, 9, 6, tzinfo=timezone.utc)
        clock = Clock
        clock.value = start
        rows = [_mem(200, mid=1), _mem(168, mid=2)]
        rows[0]["created_at"] = (start - timedelta(hours=200)).isoformat()
        rows[1]["created_at"] = (
            start - timedelta(hours=168) + timedelta(seconds=1)
        ).isoformat()
        with patch.object(policy, "datetime", Clock):
            old = self._schedule_run(rows, clock, frozen=False)
            clock.value = start
            frozen = self._schedule_run(rows, clock, frozen=True)
        self.assertEqual(old, [1, 2])
        self.assertEqual(frozen, [1])

    def _schedule_run(self, rows, clock, frozen):
        namespace = original(compression, "compression")
        if frozen:
            levels = iter(policy.get_compression_schedule(row) for row in rows)
            # Consume now, before the first encode advances the fake clock.
            prepared = list(levels)
            namespace["get_compression_schedule"] = lambda row, **kwargs: prepared.pop(
                0
            )
        engine, store = TraceEngine(), _FakeStore()
        scalar = engine.encode

        def advance(text):
            clock.value += timedelta(seconds=2)
            return scalar(text)

        engine.encode = advance
        namespace["run_compression_cycle"](store, SETTINGS, engine, rows)
        return [row[0] for row in store.updates]


if __name__ == "__main__":
    unittest.main()
