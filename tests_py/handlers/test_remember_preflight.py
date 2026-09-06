"""Exact bound/eager equivalence on deterministic observations, no DB/model."""

from __future__ import annotations

import itertools
import math
import os
import unittest
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from mcp_server.core import write_gate, write_gate_calibration as calibration
from mcp_server.core.novelty_modulation import NoveltyModulation
from mcp_server.handlers import remember_helpers as helpers
from mcp_server.handlers.remember_preflight import (
    GateObservation,
    GateOptions,
    GateRequest,
    bound_rejection,
    prepare_gate,
)
from tests_py.handlers._preflight_fakes import Engine, Store
from mcp_server.observability import silent_failure


class PreflightEquivalence(unittest.TestCase):
    def setUp(self):
        silent_failure.reset()
        self.addCleanup(silent_failure.reset)
        calibration.reset_all_states()
        self.addCleanup(calibration.reset_all_states)
        settings = SimpleNamespace(
            WRITE_GATE_THRESHOLD=0.4, WRITE_GATE_HIERARCHICAL=False
        )
        for name in (
            "mcp_server.handlers.remember_helpers.get_memory_settings",
            "mcp_server.handlers.remember_preflight.get_memory_settings",
        ):
            changed = patch(name, return_value=settings)
            changed.start()
            self.addCleanup(changed.stop)
        clock = patch.object(write_gate, "_parse_hours_since", return_value=0.0)
        clock.start()
        self.addCleanup(clock.stop)
        self.settings = settings

    def request(self, store, **changes):
        options = GateOptions(False, "fixture", "auto", "local_action")
        return GateRequest(store.content, [], store, replace(options, **changes))

    def eager(self, request, engine):
        options = request.options
        return helpers.evaluate_gate(
            request.content,
            request.tags,
            engine.encode(request.content),
            options.force,
            request.store,
            engine,
            domain=options.domain,
            write_class=options.write_class,
            origin=options.origin,
        )

    def test_fixture_decisions_equal_eager_for_every_entry(self):
        corpus = [
            "steady observation",
            "API uses Parser.",
            "# Tool: Read\n**Read:** `/project/file.py`",
        ]
        for text, repeats, similarity, threshold in itertools.product(
            corpus, (0, 2, 10), (0.0, 0.5, 1.0), (0.4, 0.8)
        ):
            with self.subTest(
                text=text, repeats=repeats, similarity=similarity, threshold=threshold
            ):
                calibration.reset_all_states()
                self.settings.WRITE_GATE_THRESHOLD = threshold
                eager = self.eager(
                    self.request(Store(text, repeats)), Engine(similarity)
                )
                calibration.reset_all_states()
                request, engine = self.request(Store(text, repeats)), Engine(similarity)
                observed = prepare_gate(request, helpers.observe_gate)
                self.assertIsNotNone(observed)
                rejection = bound_rejection(request, observed)
                if rejection is None:
                    lazy = helpers.evaluate_observed_gate(
                        request, observed, engine.encode(text), engine
                    )
                    self.assertEqual(lazy, eager)
                else:
                    self.assertFalse(eager["should_store"])
                    self.assertEqual(engine.encoded, [])
                    self.assertIsNone(rejection["novelty"]["embedding_novelty"])
                    self.assertIsNone(rejection["novelty"]["temporal_novelty"])
                self.assertEqual(calibration.get_state("fixture").total_observations, 1)

    def test_strict_boundary_and_next_representable_threshold(self):
        request = self.request(Store())
        upper = helpers.compute_novelty_score(1.0, 0.0, 1.0, 0.0)
        observed = GateObservation(
            {"importance": 0.2, "ent_nov": 0.0, "struct_nov": 0.0},
            (NoveltyModulation(), NoveltyModulation()),
            (upper, upper),
        )
        self.assertIsNone(bound_rejection(request, observed))
        above = math.nextafter(upper, math.inf)
        self.assertIsNotNone(
            bound_rejection(request, replace(observed, thresholds=(above, above)))
        )

    def test_fallback_reuses_all_observations_and_threshold(self):
        store = Store(repeats=0)
        request = self.request(store)
        observed = prepare_gate(request, helpers.observe_gate)
        reads = store.calls.copy()
        self.settings.WRITE_GATE_THRESHOLD = 0.9
        calibration.get_state("fixture").threshold = 0.9
        store.repeats = 100
        store.triggers = [
            {"trigger_type": "keyword_match", "trigger_condition": "steady"}
        ]
        engine = Engine()
        result = helpers.evaluate_observed_gate(
            request, observed, engine.encode(request.content), engine
        )
        for method in (
            "get_hot_memories",
            "get_entity_by_name",
            "signature_repeat_stats",
            "get_active_prospective_memories",
        ):
            self.assertEqual(store.calls[method], reads[method])
        self.assertEqual(result["gate_threshold"], 0.4)
        self.assertEqual(result["habituation"]["combined_gain"], 1.0)

    def test_every_bypass_keeps_eager_path(self):
        cases = [
            ("steady", [], {"force": True}),
            ("An exception occurred during startup", [], {}),
            ("We decided to use PostgreSQL", [], {}),
            ("steady", ["important"], {}),
            ("steady", ["CRITICAL"], {}),
            ("steady", [], {"write_class": "deliberate"}),
        ]
        observe = MagicMock()
        for content, tags, options in cases:
            request = replace(self.request(Store(content), **options), tags=tags)
            self.assertIsNone(prepare_gate(request, observe))
        observe.assert_not_called()

    def test_untrusted_content_cannot_buy_error_or_decision_bypass(self):
        for origin in ("network", "unknown", "legacy"):
            request = self.request(
                Store("An exception occurred during startup"), origin=origin
            )
            observe = MagicMock(return_value=object())
            self.assertIs(prepare_gate(request, observe), observe.return_value)
            observe.assert_called_once_with(request)

    def test_hierarchical_and_predictive_ablation_keep_eager_path(self):
        request, observe = self.request(Store()), MagicMock()
        self.settings.WRITE_GATE_HIERARCHICAL = True
        self.assertIsNone(prepare_gate(request, observe))
        self.settings.WRITE_GATE_HIERARCHICAL = False
        with patch.dict(os.environ, {"CORTEX_ABLATE_PREDICTIVE_CODING": "1"}):
            self.assertIsNone(prepare_gate(request, observe))
        observe.assert_not_called()

    def test_modulation_errors_are_identity_and_not_retried_on_fallback(self):
        store = Store()
        store.signature_repeat_stats = MagicMock(
            side_effect=RuntimeError("repeat failed")
        )
        store.get_active_prospective_memories = MagicMock(
            side_effect=RuntimeError("goal failed")
        )
        request = self.request(store)
        observed = prepare_gate(request, helpers.observe_gate)
        self.assertTrue(all(mod.gain is None for mod in observed.modulations))
        helpers.evaluate_observed_gate(request, observed, b"raw", Engine())
        store.signature_repeat_stats.assert_called_once()
        store.get_active_prospective_memories.assert_called_once()

    def test_calibrated_domain_threshold_is_used_for_bound(self):
        request = self.request(Store())
        calibration.get_state("fixture").threshold = 0.9
        observed = prepare_gate(request, helpers.observe_gate)
        result = bound_rejection(request, observed)
        self.assertIsNotNone(result)
        self.assertIn("threshold=0.9", result["reason"])


if __name__ == "__main__":
    unittest.main()
