"""Integration test for D1 stress-hormone modulation wiring into the CLS
consolidation path (consolidation_engine.plan_cls_consolidation + the
consolidation/cls handler's session-stress derivation).

Verifies the DIRECTION the science constrains (Roozendaal & McGaugh 2011;
McGaugh 2000) as it flows through consolidation:
  - a NEUTRAL session (stress 0) leaves the consolidation scope identical to the
    pre-D1 call — the behavior-preserving default;
  - MODERATE session stress lowers the effective recurrence bar (enhancement) so
    a pattern that was just below threshold now consolidates;
  - EXTREME session stress raises the bar (impairment) so a pattern that just
    cleared it no longer consolidates;
  - CORTEX_ABLATE_STRESS_MODULATION=1 forces the gain to 1.0 — no scope change
    at any stress level;
  - the cls handler derives the session-stress scalar from the episodic batch
    (urgency/failure markers + negative-valence share).
"""

from __future__ import annotations

import pytest

from mcp_server.core.consolidation_engine import (
    plan_cls_consolidation,
    stress_scaled_min_occurrences,
)
from mcp_server.core import stress_modulation as sm


def _exact_sim(a, b):
    if a is None or b is None:
        return 0.0
    return 1.0 if a == b else 0.0


def _cluster(n, sessions=2, content="always use UTC"):
    """n identical-embedding memories spread across `sessions` sources."""
    return [
        {
            "id": i,
            "embedding": b"pattern",
            "content": content,
            "source": f"s{i % sessions}",
            "tags": ["time"],
        }
        for i in range(n)
    ]


# ── Neutral stress => identity ───────────────────────────────────────────────
class TestNeutralIdentity:
    def test_default_no_stress_matches_explicit_zero(self):
        mems = _cluster(4)
        base = plan_cls_consolidation(
            mems, [], _exact_sim, cluster_threshold=0.9, min_occurrences=3
        )
        zero = plan_cls_consolidation(
            mems,
            [],
            _exact_sim,
            cluster_threshold=0.9,
            min_occurrences=3,
            session_stress=0.0,
        )
        assert base["patterns_found"] == zero["patterns_found"]
        assert len(base["new_semantics"]) == len(zero["new_semantics"])

    def test_neutral_gain_is_one_and_bar_unchanged(self):
        mems = _cluster(4)
        plan = plan_cls_consolidation(
            mems,
            [],
            _exact_sim,
            cluster_threshold=0.9,
            min_occurrences=3,
            session_stress=0.0,
        )
        assert plan["consolidation_gain"] == pytest.approx(1.0)
        assert plan["effective_min_occurrences"] == 3


# ── Moderate stress enhances (lowers the recurrence bar) ─────────────────────
class TestModerateEnhances:
    def test_moderate_stress_lowers_bar(self):
        # gain>1 at moderate stress => effective bar below the base.
        eff = stress_scaled_min_occurrences(4, sm.STRESS_ENHANCE_PEAK)
        assert eff < 4

    def test_pattern_just_below_bar_now_consolidates(self):
        # A 3-member cluster from 2 sessions with base bar 4 => no pattern...
        mems = _cluster(3)
        strict = plan_cls_consolidation(
            mems,
            [],
            _exact_sim,
            cluster_threshold=0.9,
            min_occurrences=4,
            min_sessions=2,
            session_stress=0.0,
        )
        assert strict["patterns_found"] == 0
        # ...but moderate stress lowers the bar to 3, so it consolidates.
        stressed = plan_cls_consolidation(
            mems,
            [],
            _exact_sim,
            cluster_threshold=0.9,
            min_occurrences=4,
            min_sessions=2,
            session_stress=sm.STRESS_ENHANCE_PEAK,
        )
        assert stressed["effective_min_occurrences"] < 4
        assert stressed["patterns_found"] >= 1


# ── Extreme stress impairs (raises the recurrence bar) ───────────────────────
class TestExtremeImpairs:
    def test_extreme_stress_raises_bar(self):
        eff = stress_scaled_min_occurrences(3, 1.0)
        assert eff > 3  # gain<1 => bar raised above base

    def test_pattern_just_above_bar_now_skipped(self):
        # A 3-member cluster clears base bar 3...
        mems = _cluster(3)
        ok = plan_cls_consolidation(
            mems,
            [],
            _exact_sim,
            cluster_threshold=0.9,
            min_occurrences=3,
            min_sessions=2,
            session_stress=0.0,
        )
        assert ok["patterns_found"] >= 1
        # ...but extreme stress raises the bar above 3, so it no longer does.
        impaired = plan_cls_consolidation(
            mems,
            [],
            _exact_sim,
            cluster_threshold=0.9,
            min_occurrences=3,
            min_sessions=2,
            session_stress=1.0,
        )
        assert impaired["effective_min_occurrences"] > 3
        assert impaired["patterns_found"] == 0


# ── Ablation guard ───────────────────────────────────────────────────────────
class TestAblationGuard:
    def test_ablation_flattens_bar_at_all_stress(self, monkeypatch):
        monkeypatch.setenv("CORTEX_ABLATE_STRESS_MODULATION", "1")
        for s in (0.0, 0.5, 1.0):
            assert stress_scaled_min_occurrences(3, s) == 3

    def test_ablation_disables_enhancement(self, monkeypatch):
        monkeypatch.setenv("CORTEX_ABLATE_STRESS_MODULATION", "1")
        # Same 3-member/base-4 cluster that moderate stress rescued above stays
        # unconsolidated when the mechanism is ablated.
        mems = _cluster(3)
        plan = plan_cls_consolidation(
            mems,
            [],
            _exact_sim,
            cluster_threshold=0.9,
            min_occurrences=4,
            min_sessions=2,
            session_stress=sm.STRESS_ENHANCE_PEAK,
        )
        assert plan["consolidation_gain"] == pytest.approx(1.0)
        assert plan["effective_min_occurrences"] == 4
        assert plan["patterns_found"] == 0

    def test_ablation_disables_impairment(self, monkeypatch):
        monkeypatch.setenv("CORTEX_ABLATE_STRESS_MODULATION", "1")
        # The 3-member/base-3 cluster that extreme stress skipped above still
        # consolidates when ablated (bar stays at 3).
        mems = _cluster(3)
        plan = plan_cls_consolidation(
            mems,
            [],
            _exact_sim,
            cluster_threshold=0.9,
            min_occurrences=3,
            min_sessions=2,
            session_stress=1.0,
        )
        assert plan["effective_min_occurrences"] == 3
        assert plan["patterns_found"] >= 1


# ── Handler-side session-stress derivation ───────────────────────────────────
class TestHandlerStressDerivation:
    def test_calm_batch_is_neutral(self):
        from mcp_server.handlers.consolidation.cls import _compute_session_stress

        batch = [
            {"content": "all tests pass, shipped it", "emotional_valence": 0.4},
            {"content": "clean refactor merged", "emotional_valence": 0.3},
        ]
        assert _compute_session_stress(batch) == pytest.approx(0.0)

    def test_fraught_batch_has_stress(self):
        from mcp_server.handlers.consolidation.cls import _compute_session_stress

        batch = [
            {
                "content": "URGENT production outage, everything failed",
                "emotional_valence": -0.8,
            },
            {
                "content": "error after error, it crashed again, deadline blown",
                "emotional_valence": -0.7,
            },
        ]
        stress = _compute_session_stress(batch)
        assert stress > 0.0
        # Both memories negative => error-rate channel maxed.
        assert stress >= sm.STRESS_W_ERROR

    def test_empty_batch_neutral(self):
        from mcp_server.handlers.consolidation.cls import _compute_session_stress

        assert _compute_session_stress([]) == pytest.approx(0.0)
