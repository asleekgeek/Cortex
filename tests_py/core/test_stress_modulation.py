"""Tests for mcp_server.core.stress_modulation — D1 stress-hormone
(glucocorticoid) modulation of consolidation strength.

D1 is a DESIGN INFERENCE (an engineering heuristic), not a validated
glucocorticoid model: a session-stress proxy (error rate + urgency/failure
lexical density) mapped through an inverted-U to a consolidation-gain multiplier.
The properties under test are the ones the science constrains — the DIRECTION of
the inverted-U (moderate stress enhances, extreme impairs), reuse of the exact
Hebb (1955) bump the emotional-tagging path uses, and the neutral (stress = 0)
identity that makes the modulation opt-in.
"""

import math

import pytest

from mcp_server.core import stress_modulation as sm
from mcp_server.core.emotional_tagging import arousal_inverted_u_bump


class TestComputeSessionStress:
    def test_all_zero_is_calm(self):
        # The neutral case: a calm session scores exactly 0.
        assert sm.compute_session_stress(0.0, 0, 0) == pytest.approx(0.0)

    def test_max_all_channels_is_one(self):
        # Every channel maxed => scalar reaches exactly 1.0 (weights sum to 1).
        s = sm.compute_session_stress(1.0, sm.STRESS_MARKER_CAP, sm.STRESS_MARKER_CAP)
        assert s == pytest.approx(1.0)

    def test_error_rate_weighted_highest(self):
        # Error rate carries more weight than either lexical channel alone.
        only_err = sm.compute_session_stress(1.0, 0, 0)
        only_urg = sm.compute_session_stress(0.0, sm.STRESS_MARKER_CAP, 0)
        only_fail = sm.compute_session_stress(0.0, 0, sm.STRESS_MARKER_CAP)
        assert only_err > only_urg
        assert only_err > only_fail
        assert only_err == pytest.approx(sm.STRESS_W_ERROR)

    def test_channel_weights(self):
        assert sm.compute_session_stress(0.0, sm.STRESS_MARKER_CAP, 0) == pytest.approx(
            sm.STRESS_W_URGENCY
        )
        assert sm.compute_session_stress(0.0, 0, sm.STRESS_MARKER_CAP) == pytest.approx(
            sm.STRESS_W_FAILURE
        )

    def test_monotonic_in_error_rate(self):
        a = sm.compute_session_stress(0.2, 1, 1)
        b = sm.compute_session_stress(0.6, 1, 1)
        assert b > a

    def test_clamps_error_rate(self):
        assert sm.compute_session_stress(5.0, 0, 0) == pytest.approx(sm.STRESS_W_ERROR)
        assert sm.compute_session_stress(-3.0, 0, 0) == pytest.approx(0.0)

    def test_hits_capped(self):
        # Hits beyond the cap do not push the channel past its full weight.
        big = sm.compute_session_stress(0.0, 100, 0)
        exact = sm.compute_session_stress(0.0, sm.STRESS_MARKER_CAP, 0)
        assert big == pytest.approx(exact)

    def test_bounded_unit_interval(self):
        for e in (0.0, 0.5, 1.0):
            for u in (0, 2, 5):
                for f in (0, 2, 5):
                    s = sm.compute_session_stress(e, u, f)
                    assert 0.0 <= s <= 1.0


class TestDetectStressMarkers:
    def test_no_markers_in_calm_text(self):
        m = sm.detect_stress_markers("everything works, tests pass, shipped it")
        assert m["urgency"] == 0
        # NOTE: 'failed'/'fixed' etc absent; a clean success line has no failures.
        assert m["failure"] == 0

    def test_urgency_and_deadline_language(self):
        m = sm.detect_stress_markers("this is URGENT, hard deadline, production outage")
        assert m["urgency"] >= 2

    def test_failure_markers(self):
        m = sm.detect_stress_markers(
            "error, exception, traceback, it crashed and failed"
        )
        assert m["failure"] >= 2

    def test_reuses_emotional_tagging_lexicon(self):
        # D1 keys on the SAME words emotional_tagging.detect_emotions does — not
        # a second, drifting lexicon. A shared urgency word must register in both.
        from mcp_server.core.emotional_tagging import detect_emotions

        text = "critical blocking deadline asap"
        assert sm.detect_stress_markers(text)["urgency"] > 0
        assert detect_emotions(text)["urgency"] > 0

    def test_empty_text(self):
        assert sm.detect_stress_markers("") == {"urgency": 0, "failure": 0}
        assert sm.detect_stress_markers(None) == {"urgency": 0, "failure": 0}

    def test_hits_capped_at_marker_cap(self):
        m = sm.detect_stress_markers("error " * 50)
        assert m["failure"] == sm.STRESS_MARKER_CAP


class TestConsolidationGain:
    def test_neutral_stress_is_identity(self):
        # The load-bearing default: stress 0 => gain 1.0 => consolidation unchanged.
        assert sm.consolidation_gain(0.0) == pytest.approx(1.0)

    def test_moderate_stress_enhances(self):
        # Moderate stress lifts the gain above 1.0 (enhancement lobe).
        assert sm.consolidation_gain(sm.STRESS_ENHANCE_PEAK) > 1.0

    def test_extreme_stress_impairs(self):
        # Extreme stress drives the gain below 1.0 (impairment lobe) — the
        # falling arm of the inverted-U (Roozendaal & McGaugh 2011).
        assert sm.consolidation_gain(1.0) < 1.0

    def test_inverted_u_shape(self):
        # gain rises then falls across the stress range.
        gains = [sm.consolidation_gain(s / 10.0) for s in range(0, 11)]
        peak_idx = gains.index(max(gains))
        assert 0 < peak_idx < 10  # peak is interior, not at an endpoint
        # rising up to the peak, then non-increasing after it
        assert all(gains[i] <= gains[i + 1] + 1e-9 for i in range(peak_idx))
        assert all(
            gains[i] >= gains[i + 1] - 1e-9 for i in range(peak_idx, len(gains) - 1)
        )

    def test_peak_near_enhance_peak(self):
        # The enhancement peak sits at STRESS_ENHANCE_PEAK before overload bites.
        peak_gain = sm.consolidation_gain(sm.STRESS_ENHANCE_PEAK)
        assert peak_gain == pytest.approx(1.0 + sm.STRESS_ENHANCE_HEIGHT, abs=1e-3)

    def test_no_overload_below_onset(self):
        # Below the overload onset the gain is exactly 1 + the Hebb bump (no
        # penalty term) — proving the enhancement lobe is the reused curve.
        s = sm.STRESS_OVERLOAD_ONSET / 2.0
        expected = 1.0 + arousal_inverted_u_bump(
            s, peak=sm.STRESS_ENHANCE_PEAK, peak_height=sm.STRESS_ENHANCE_HEIGHT
        )
        assert sm.consolidation_gain(s) == pytest.approx(round(expected, 4))

    def test_gain_floored(self):
        # Even at max stress the gain never falls below the floor (impairment,
        # not full shutdown).
        assert sm.consolidation_gain(1.0) >= sm.STRESS_GAIN_FLOOR

    def test_clamps_input(self):
        assert sm.consolidation_gain(-1.0) == pytest.approx(
            1.0
        )  # clamps to 0 => identity
        assert sm.consolidation_gain(5.0) == pytest.approx(sm.consolidation_gain(1.0))


class TestReuseOfExistingCurve:
    """D1 must REUSE the existing Hebb inverted-U, not duplicate it."""

    def test_enhancement_lobe_is_shared_bump(self):
        # The enhancement lobe equals arousal_inverted_u_bump with D1's params —
        # the exact function emotional_tagging.compute_importance_boost uses.
        for s in (0.1, 0.3, 0.5):
            expected = 1.0 + arousal_inverted_u_bump(
                s, peak=sm.STRESS_ENHANCE_PEAK, peak_height=sm.STRESS_ENHANCE_HEIGHT
            )
            assert sm.consolidation_gain(s) == pytest.approx(round(expected, 4))

    def test_default_bump_matches_emotional_tagging_curve(self):
        # The factored bump reproduces the emotional-tagging default (peak 1.57
        # at arousal 0.7) byte-for-byte — the reuse is genuine, not a fork.
        def old_inline(a):
            b = 1.0 / 0.7
            c = 0.57 * b * math.e
            return 1.0 + c * a * math.exp(-b * a)

        for a in (0.0, 0.2, 0.5, 0.7, 1.0):
            assert 1.0 + arousal_inverted_u_bump(a) == pytest.approx(old_inline(a))


class TestIsImpairing:
    def test_neutral_not_impairing(self):
        assert sm.is_impairing(0.0) is False

    def test_moderate_not_impairing(self):
        assert sm.is_impairing(sm.STRESS_ENHANCE_PEAK) is False

    def test_extreme_is_impairing(self):
        assert sm.is_impairing(1.0) is True


class TestAssessSessionStress:
    def test_calm_session_no_change(self):
        out = sm.assess_session_stress("all tests pass, clean and shipped", 0.0)
        assert out["stress"] == pytest.approx(0.0)
        assert out["consolidation_gain"] == pytest.approx(1.0)
        assert out["is_impairing"] is False

    def test_fraught_session_has_stress(self):
        out = sm.assess_session_stress(
            "URGENT production outage, error after error, it crashed and failed", 0.5
        )
        assert out["stress"] > 0.0
        assert out["markers"]["urgency"] >= 1
        assert out["markers"]["failure"] >= 1

    def test_output_shape(self):
        out = sm.assess_session_stress("deadline", 0.3)
        assert set(out) == {
            "stress",
            "consolidation_gain",
            "is_impairing",
            "markers",
            "error_rate",
        }
        assert set(out["markers"]) == {"urgency", "failure"}

    def test_error_rate_echoed_clamped(self):
        assert sm.assess_session_stress("", 5.0)["error_rate"] == pytest.approx(1.0)


class TestAblationGuard:
    def test_ablation_flattens_gain(self, monkeypatch):
        monkeypatch.setenv("CORTEX_ABLATE_STRESS_MODULATION", "1")
        # Every stress level returns the unmodulated 1.0.
        for s in (0.0, 0.3, 0.5, 0.8, 1.0):
            assert sm.consolidation_gain(s) == pytest.approx(1.0)

    def test_ablation_disables_impairment(self, monkeypatch):
        monkeypatch.setenv("CORTEX_ABLATE_STRESS_MODULATION", "1")
        assert sm.is_impairing(1.0) is False

    def test_enabled_by_default(self):
        # Without the env var the mechanism modulates (extreme stress impairs).
        assert sm.consolidation_gain(1.0) < 1.0
