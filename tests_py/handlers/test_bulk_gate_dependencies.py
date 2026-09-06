"""Counterexamples: pre-observing gated writes changes actual handler outcomes."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from mcp_server.handlers import import_sessions, remember
from mcp_server.handlers.consolidation import memify_derive
from tests_py.handlers._remember_bulk_fakes import harness, run


CONTENT = "steady observation"


def capture_first_observation(env, frozen):
    env.store.repeat_after_insert = 10
    if not frozen:
        return
    first = []
    observe = remember.observe_gate

    def snapshot(request):
        if not first:
            first.append(observe(request))
        return first[0]

    env.stack.enter_context(patch.object(remember, "observe_gate", snapshot))


class GateDependencies(unittest.TestCase):
    def import_run(self, frozen=False):
        with harness() as env:
            capture_first_observation(env, frozen)
            result = run(
                import_sessions._process_session_items(
                    [{"content": CONTENT, "tags": []} for _ in range(2)],
                    "fixture",
                    "fixture",
                    False,
                    [],
                )
            )
            return result, env

    def test_import_reobserves_prior_insert_and_skips_encode_for_bound_rejection(self):
        live, frozen = self.import_run(), self.import_run(True)
        self.assertEqual(live[0], (1, 1))
        self.assertEqual(frozen[0], (2, 0))
        self.assertEqual(live[1].engine.scalars, [CONTENT])
        self.assertEqual(live[1].engine.batches, [])

    def derive_run(self, frozen=False):
        with harness() as env:
            capture_first_observation(env, frozen)
            relation = {"source_entity_id": 1, "target_entity_id": 2}
            results = [
                run(memify_derive._derive_one(env.store, relation, CONTENT, marker))
                for marker in ("first", "second")
            ]
            return results, env

    def test_derive_gate_and_source_ids_depend_on_preceding_write(self):
        live, frozen = self.derive_run(), self.derive_run(True)
        self.assertEqual(live[0], ["derived_created", "derived_rejected"])
        self.assertEqual(frozen[0], ["derived_created", "derived_created"])
        self.assertEqual(live[1].engine.scalars, [CONTENT])
        self.assertIn("derived-src:1", frozen[1].store.rows[0][2])
        self.assertIn("derived-src:2", frozen[1].store.rows[1][2])


if __name__ == "__main__":
    unittest.main()
