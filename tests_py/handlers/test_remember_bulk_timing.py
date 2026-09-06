"""Deterministic elapsed-time boundaries; no model, database or wall-clock probe."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from mcp_server.errors import ValidationError
from mcp_server.handlers import remember
from mcp_server.handlers._telemetry_wrap import instrument
from mcp_server.handlers.remember_bulk import prepare_bulk, store_prepared
from mcp_server.handlers.remember_prepared import InputFailure
from tests_py.handlers._remember_bulk_fakes import harness, run


class Clock:
    """Synthetic seconds make overlapping entry latencies exactly observable."""

    def __init__(self):
        self.now = 0.0

    def advance(self, seconds):
        self.now += seconds

    def timed(self, fn, seconds):
        def wrapped(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            finally:
                self.advance(seconds)

        return wrapped


def timed_harness(env):
    clock = Clock()
    env.stack.enter_context(patch("time.perf_counter", side_effect=lambda: clock.now))
    for owner, name, seconds in (
        (remember, "prepare_write", 2),
        (env.engine, "encode_batch", 10),
        (env.engine, "encode", 5),
        (remember, "insert_and_post_process", 3),
    ):
        env.stack.enter_context(
            patch.object(owner, name, clock.timed(getattr(owner, name), seconds))
        )
    return clock


def samples(env):
    return [
        (call.kwargs["latency_ms"], call.kwargs["ok"])
        for call in env.telemetry.call_args_list
    ]


class RememberBulkTiming(unittest.TestCase):
    def test_latencies_include_preparation_batch_and_previous_continuations(self):
        with harness() as env:
            clock = timed_harness(env)
            pending = prepare_bulk(
                [{"content": text, "force": True} for text in ("first", "second")]
            )
            self.assertEqual([item.started_at for item in pending], [0.0, 2.0])
            self.assertEqual(clock.now, 14.0)
            run(store_prepared(pending[0]))
            run(store_prepared(pending[1]))
            self.assertEqual(samples(env), [(17000.0, True), (18000.0, True)])
            self.assertEqual(clock.now, 20.0)  # entry latencies overlap, not CPU sums

    def test_validation_error_keeps_its_own_preparation_and_batch_wait(self):
        with harness() as env:
            timed_harness(env)
            pending = prepare_bulk(
                [
                    {"content": "first", "force": True},
                    {"content": "bad", "force": True, "write_class": "invalid"},
                ]
            )
            run(store_prepared(pending[0]))
            with self.assertRaises(ValidationError):
                run(store_prepared(pending[1]))
            self.assertEqual(samples(env), [(17000.0, True), (15000.0, False)])

    def test_encoding_error_includes_failed_batch_and_scalar_recovery(self):
        with harness() as env:
            timed_harness(env)
            env.engine.failures["bad"] = RuntimeError("encode")
            with self.assertLogs("mcp_server.infrastructure.embedding_batch", "ERROR"):
                pending = prepare_bulk(
                    [{"content": text, "force": True} for text in ("first", "bad")]
                )
            run(store_prepared(pending[0]))
            with self.assertRaisesRegex(RuntimeError, "encode"):
                run(store_prepared(pending[1]))
            self.assertEqual(samples(env), [(27000.0, True), (25000.0, False)])

    def test_engine_lookup_error_includes_preparation_and_next_retry(self):
        with harness() as env:
            clock = timed_harness(env)
            lookup = env.stack.enter_context(
                patch.object(
                    remember,
                    "get_embedding_engine",
                    side_effect=[RuntimeError("lookup"), env.engine],
                )
            )
            env.stack.enter_context(
                patch.object(remember, "get_embedding_engine", clock.timed(lookup, 6))
            )
            pending = prepare_bulk(
                [{"content": text, "force": True} for text in ("first", "second")]
            )
            with self.assertRaisesRegex(RuntimeError, "lookup"):
                run(store_prepared(pending[0]))
            run(store_prepared(pending[1]))
            self.assertEqual(samples(env), [(10000.0, False), (22000.0, True)])

    def test_store_error_includes_batch_and_failed_continuation(self):
        with harness() as env:
            timed_harness(env)
            env.store.fail_insert = "bad"
            pending = prepare_bulk([{"content": "bad", "force": True}])
            with self.assertRaisesRegex(RuntimeError, "insert failure"):
                run(store_prepared(pending[0]))
            self.assertEqual(samples(env), [(15000.0, False)])

    def test_caller_input_failure_and_abandonment_do_not_fabricate_handler_calls(self):
        with harness() as env:
            timed_harness(env)
            pending = prepare_bulk(
                [
                    InputFailure(ValueError("input")),
                    {"content": "unused", "force": True},
                ]
            )
            self.assertIsNone(pending[0].started_at)
            with self.assertRaisesRegex(ValueError, "input"):
                run(store_prepared(pending[0]))
            self.assertEqual(samples(env), [])

    def test_default_wrapper_starts_at_each_call_and_records_interruptions(self):
        with harness() as env:
            clock = timed_harness(env)

            async def operation(args):
                clock.advance(3)
                if args["cancel"]:
                    raise KeyboardInterrupt("stop")
                return {}

            wrapped = instrument("remember", operation)
            run(wrapped({"cancel": False}))
            clock.advance(7)
            with self.assertRaises(KeyboardInterrupt):
                run(wrapped({"cancel": True}))
            self.assertEqual(samples(env), [(3000.0, True), (3000.0, False)])
