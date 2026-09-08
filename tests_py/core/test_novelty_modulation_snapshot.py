"""Snapshot arithmetic retains raw gains, independent clamps and ablations."""

from __future__ import annotations

import itertools
import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from mcp_server.core import goal_maintenance, habituation, write_gate
from mcp_server.core.novelty_modulation import apply_modulation
from mcp_server.observability import silent_failure


class ModulationSnapshot(unittest.TestCase):
    def setUp(self):
        silent_failure.reset()
        self.addCleanup(silent_failure.reset)

    def test_habituation_matches_original_outcome_without_rounding(self):
        for score, repeats, hours, importance in itertools.product(
            (0.0, 0.17, 0.6, 1.0), (0, 1, 10), (None, 0.0, 1.0), (0.2, 0.9)
        ):
            salient = habituation.is_salient(importance)
            expected = habituation.habituate_novelty(
                score,
                "steady",
                repeats,
                hours,
                importance if salient else 0.0,
                0.0 if salient else None,
            )
            store = SimpleNamespace(
                signature_repeat_stats=MagicMock(return_value=(repeats, hours))
            )
            observed = write_gate.prepare_habituation("steady", importance, store)
            actual, details = apply_modulation(score, observed)
            self.assertEqual(actual, expected.modulated_novelty)
            self.assertEqual(details, habituation.habituation_outcome_as_dict(expected))

    def test_goal_gain_stays_raw_while_diagnostics_round(self):
        goal = goal_maintenance.build_goal_from_task(
            "alpha bravo charlie delta echo foxtrot golf"
        )
        content = "alpha"
        with patch.object(write_gate, "read_active_goal", return_value=goal):
            observed = write_gate.prepare_goal_maintenance(content, [], object())
        expected = goal_maintenance.goal_write_gain(goal, content, entities=[])
        self.assertEqual(observed.gain, expected)
        self.assertNotEqual(observed.gain, observed.details["gain"])
        score, details = apply_modulation(0.6, observed)
        self.assertEqual(score, max(0.0, min(1.0, 0.6 * expected)))
        self.assertEqual(details["modulated_novelty"], round(score, 4))

    def test_ablation_reads_nothing_and_preserves_score_exactly(self):
        store = MagicMock()
        with patch.dict(
            os.environ,
            {"CORTEX_ABLATE_HABITUATION": "1", "CORTEX_ABLATE_GOAL_MAINTENANCE": "1"},
        ):
            first = write_gate.prepare_habituation("steady", 0.3, store)
            second = write_gate.prepare_goal_maintenance("steady", [], store)
        for observed in (first, second):
            self.assertEqual(
                apply_modulation(0.7123456789, observed), (0.7123456789, None)
            )
        self.assertEqual(store.mock_calls, [])

    def test_public_modulation_errors_remain_non_fatal(self):
        store = SimpleNamespace(signature_repeat_stats=lambda _: (1, 0.0))
        self.assertEqual(
            write_gate.apply_habituation(None, "steady", 0.3, store), (None, None)
        )
        goal = goal_maintenance.build_goal_from_task("steady")
        with patch.object(write_gate, "read_active_goal", return_value=goal):
            self.assertEqual(
                write_gate.apply_goal_maintenance(None, "steady", [], store),
                (None, None),
            )


if __name__ == "__main__":
    unittest.main()
