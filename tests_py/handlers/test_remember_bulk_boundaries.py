"""Real continuation and original caller bodies, with no DB or ML effects."""

from __future__ import annotations

import copy
import asyncio
import unittest
from pathlib import Path
from unittest.mock import patch

from mcp_server.errors import ValidationError
from mcp_server.handlers import record_session_end_memory as lessons
from mcp_server.handlers import remember, seed_project
from mcp_server.handlers.remember_bulk import prepare_bulk, store_prepared
from tests_py.handlers._remember_bulk_fakes import (
    harness,
    original,
    reference_caller,
    run,
)


def seed_scenario(discoveries, reference=False, fault=None):
    with harness() as env:
        if fault:
            fault(env)
        env.reference = original(remember, "remember")["_handler_impl"]
        env.stack.enter_context(
            patch.object(seed_project, "_get_store", return_value=env.store)
        )
        fn = seed_project._store_discoveries
        if reference:
            fn = reference_caller(
                seed_project, "seed", "_store_discoveries", env.reference
            )
        try:
            result = run(fn(copy.deepcopy(discoveries), Path("/fixture"), "fixture"))
        except BaseException as exc:
            result = (type(exc), str(exc))
        return result, env


def lesson_scenario(suggestions, reference=False, fault=None):
    with harness() as env:
        if fault:
            fault(env)
        env.reference = original(remember, "remember")["_handler_impl"]
        fn = lessons._try_store_lesson_candidates
        if reference:
            fn = reference_caller(
                lessons, "lessons", "_try_store_lesson_candidates", env.reference
            )
        try:
            result = run(fn(suggestions, "fixture-session", "fixture", ""))
        except BaseException as exc:
            result = (type(exc), str(exc))
        return result, env


class RememberBulk(unittest.TestCase):
    def assert_same(self, before, after):
        self.assertEqual(before[0], after[0])
        self.assertEqual(before[1].store.rows, after[1].store.rows)
        self.assertEqual(before[1].store.events, after[1].store.events)
        self.assertEqual(before[1].store.read_versions, after[1].store.read_versions)
        self.assertEqual(before[1].telemetry.call_count, after[1].telemetry.call_count)

    def test_seed_one_batch_exact_raw_vectors_and_sequential_reads_heat_ids(self):
        items = [{"content": text} for text in ("  raw text  ", "next\nline", "")]
        old, new = seed_scenario(items, True), seed_scenario(items)
        self.assert_same(old, new)
        self.assertEqual(new[0], (2, 1, [1, 2]))
        self.assertEqual(new[1].engine.scalars, [])
        self.assertEqual(new[1].engine.batches, [["  raw text  ", "next\nline"]])
        self.assertEqual(new[1].store.read_versions, [0, 1])

    def test_seed_invalid_n_keeps_prior_writes_and_never_encodes_invalid_or_later(self):
        items = [{"content": "first"}, {"content": 7}, {"content": "later"}]
        old, new = seed_scenario(items, True), seed_scenario(items)
        self.assert_same(old, new)
        self.assertEqual(len(new[1].store.rows), 1)
        self.assertEqual(new[1].engine.batches, [["first"]])

    def test_seed_input_construction_failure_keeps_prior_write_and_telemetry(self):
        items = [{"content": "first"}, {"content": "bad", "tags": None}]
        old, new = seed_scenario(items, True), seed_scenario(items)
        self.assert_same(old, new)
        self.assertEqual(len(new[1].store.rows), 1)

    def test_seed_store_failure_preserves_prefix(self):
        items = [{"content": text} for text in ("first", "bad", "later")]

        def fault(env):
            env.store.fail_insert = "bad"

        self.assert_same(
            seed_scenario(items, True, fault), seed_scenario(items, fault=fault)
        )

    def test_seed_ordinary_encoder_failure_preserves_prefix_and_reports_recovery(self):
        items = [{"content": text} for text in ("first", "bad", "later")]

        def fault(env):
            env.engine.failures["bad"] = RuntimeError("encode failure")

        old = seed_scenario(items, True, fault)
        with self.assertLogs(
            "mcp_server.infrastructure.embedding_batch", level="ERROR"
        ):
            new = seed_scenario(items, fault=fault)
        self.assert_same(old, new)
        self.assertEqual(len(new[1].engine.batches), 1)
        self.assertEqual(new[1].engine.scalars, ["first", "bad", "later"])

    def test_interrupt_is_propagated_and_prefix_difference_is_explicit(self):
        items = [{"content": text} for text in ("first", "interrupt")]

        def fault(env):
            env.engine.failures["interrupt"] = KeyboardInterrupt("stop")

        old, new = seed_scenario(items, True, fault), seed_scenario(items, fault=fault)
        self.assertEqual(old[0], new[0])
        self.assertEqual(old[0][0], KeyboardInterrupt)
        self.assertEqual(len(old[1].store.rows), 1)
        self.assertEqual(new[1].store.rows, [])

    def test_lessons_strip_skip_batch_and_counters_match_original(self):
        inputs = ["  first  ", "", None, "second"]
        old, new = lesson_scenario(inputs, True), lesson_scenario(inputs)
        self.assert_same(old, new)
        self.assertEqual(new[0], 2)
        self.assertEqual(len(new[1].engine.batches), 1)
        self.assertEqual(new[1].engine.scalars, [])

    def test_lessons_strip_failure_aborts_after_same_prefix(self):
        old, new = lesson_scenario(["first", 7], True), lesson_scenario(["first", 7])
        self.assert_same(old, new)
        self.assertEqual(len(new[1].store.rows), 1)
        self.assertEqual(new[0][0], AttributeError)

    def test_lessons_write_failure_continues_at_next_suggestion(self):
        def fault(env):
            env.store.fail_insert = "[self-critique, session fixture-session] bad"

        old = lesson_scenario(["first", "bad", "last"], True, fault)
        new = lesson_scenario(["first", "bad", "last"], fault=fault)
        self.assert_same(old, new)
        self.assertEqual(new[0], 2)

    def test_invalid_write_class_and_empty_inputs_never_construct_model(self):
        with harness() as env:
            getter = env.stack.enter_context(
                patch.object(remember, "get_embedding_engine")
            )
            pending = prepare_bulk(
                [
                    {"content": "bad", "force": True, "write_class": "invalid"},
                    {"content": "", "force": True},
                ]
            )
            with self.assertRaises(ValidationError):
                run(store_prepared(pending[0]))
            self.assertFalse(run(store_prepared(pending[1]))["stored"])
            getter.assert_not_called()
            self.assertEqual(prepare_bulk([]), [])

    def test_lookup_failure_is_deferred_and_next_lesson_retries_like_original(self):
        def fault(env):
            env.stack.enter_context(
                patch.object(
                    remember,
                    "get_embedding_engine",
                    side_effect=[RuntimeError("lookup"), env.engine],
                )
            )

        old = lesson_scenario(["first", "second"], True, fault)
        new = lesson_scenario(["first", "second"], fault=fault)
        self.assert_same(old, new)
        self.assertEqual(new[0], 1)
        self.assertEqual(new[1].engine.batches, [])

    def test_prepared_continuations_add_no_event_loop_yield_or_global_state(self):
        with harness() as env:

            async def calls():
                events = []
                asyncio.get_running_loop().call_soon(events.append, "scheduled")
                pending = prepare_bulk(
                    [
                        {"content": "first", "force": True},
                        {"content": "abandoned", "force": True},
                    ]
                )
                await store_prepared(pending[0])
                await remember.handler({"content": "fresh", "force": True})
                self.assertEqual(events, [])

            run(calls())
            self.assertEqual([row[0] for row in env.store.rows], ["first", "fresh"])
            self.assertEqual(env.engine.scalars, ["fresh"])

    def test_prepared_batch_does_not_accept_gated_or_supersession_inputs(self):
        with harness() as env:
            pending = prepare_bulk(
                [
                    {"content": "gated", "write_class": "mechanical"},
                    {"content": "edge", "force": True, "supersedes_id": 1},
                ]
            )
            for item in pending:
                with self.assertRaises(ValueError):
                    run(store_prepared(item))
            self.assertEqual(env.engine.batches + env.engine.scalars, [])


if __name__ == "__main__":
    unittest.main()
