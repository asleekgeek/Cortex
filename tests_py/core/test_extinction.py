"""Tests for mcp_server.core.extinction — E2 reversible inhibitory learning.

The defining property under test is REVERSIBILITY (Bouton 2004): extinction
suppresses a learned association without erasing it, so the association returns
via spontaneous recovery (time) and reinstatement (one step), and the base
strength is never modified.
"""

import pytest

from mcp_server.core.extinction import (
    apply_extinction,
    spontaneous_recovery,
    reinstate,
    effective_strength,
    is_extinguished,
    deprecate,
    ExtinctionOutcome,
    EXTINCTION_TRIAL_GAIN,
    MAX_EXTINCTION,
    RECOVERY_HALF_LIFE_HOURS,
    RECOVERY_FLOOR,
)


class TestApplyExtinction:
    def test_single_trial_adds_gain_from_zero(self):
        # From 0: new = 0 + gain*(1-0) = gain
        assert apply_extinction(0.0, 1) == pytest.approx(EXTINCTION_TRIAL_GAIN)

    def test_diminishing_returns(self):
        # Each trial adds less than the previous (approaches ceiling).
        one = apply_extinction(0.0, 1)
        two = apply_extinction(0.0, 2)
        assert two > one
        assert (two - one) < one  # second increment smaller than first

    def test_approaches_but_never_exceeds_ceiling(self):
        e = apply_extinction(0.0, 100)
        assert e <= MAX_EXTINCTION
        assert e > 0.99

    def test_zero_trials_is_noop(self):
        assert apply_extinction(0.4, 0) == pytest.approx(0.4)

    def test_monotonic_nondecreasing(self):
        assert apply_extinction(0.5, 1) >= 0.5

    def test_clamps_input(self):
        assert apply_extinction(1.5, 1) == pytest.approx(MAX_EXTINCTION)
        assert 0.0 <= apply_extinction(-0.5, 1) <= 1.0


class TestEffectiveStrength:
    def test_no_extinction_returns_base(self):
        # The load-bearing default: tag 0 => no behaviour change.
        assert effective_strength(0.8, 0.0) == pytest.approx(0.8)

    def test_full_extinction_zeroes_effective(self):
        assert effective_strength(0.8, 1.0) == pytest.approx(0.0)

    def test_partial_extinction_scales(self):
        assert effective_strength(1.0, 0.35) == pytest.approx(0.65)

    def test_base_never_negative(self):
        assert effective_strength(-1.0, 0.5) == 0.0

    def test_bounded_by_base(self):
        for e in (0.0, 0.25, 0.5, 0.75, 1.0):
            assert 0.0 <= effective_strength(0.6, e) <= 0.6


class TestSpontaneousRecovery:
    def test_half_life_halves_tag(self):
        # After one half-life the inhibition is halved (association returns).
        e = spontaneous_recovery(0.8, RECOVERY_HALF_LIFE_HOURS)
        assert e == pytest.approx(0.4, abs=1e-6)

    def test_recovery_returns_association(self):
        # Effective strength RISES back toward base as inhibition decays,
        # while base is untouched.
        base = 0.9
        tag0 = 0.8
        eff0 = effective_strength(base, tag0)
        tag1 = spontaneous_recovery(tag0, RECOVERY_HALF_LIFE_HOURS)
        eff1 = effective_strength(base, tag1)
        assert eff1 > eff0  # association re-expresses over time

    def test_zero_hours_is_noop(self):
        assert spontaneous_recovery(0.5, 0.0) == pytest.approx(0.5)

    def test_snaps_to_zero_below_floor(self):
        # Very long elapsed time drives residual under the floor -> full recovery
        e = spontaneous_recovery(0.5, RECOVERY_HALF_LIFE_HOURS * 20)
        assert e == 0.0

    def test_never_increases_tag(self):
        assert spontaneous_recovery(0.3, 10.0) <= 0.3

    def test_zero_tag_stays_zero(self):
        assert spontaneous_recovery(0.0, 100.0) == 0.0

    def test_floor_constant_sane(self):
        assert 0.0 < RECOVERY_FLOOR < 0.1


class TestReinstate:
    def test_full_restore_by_default(self):
        # Reinstatement collapses the tag => original association restored.
        assert reinstate(0.9) == 0.0

    def test_effective_strength_fully_restored(self):
        base = 0.7
        tag = apply_extinction(0.0, 3)
        assert effective_strength(base, tag) < base  # suppressed
        assert effective_strength(base, reinstate(tag)) == pytest.approx(base)

    def test_never_increases_tag(self):
        assert reinstate(0.2, residual=0.9) == pytest.approx(0.2)

    def test_residual_savings(self):
        # A non-zero residual models extinction "savings".
        assert reinstate(0.9, residual=0.1) == pytest.approx(0.1)


class TestDoesNotErase:
    """Extinction is distinct from active_forgetting: base strength is never
    written by any extinction operation — only the tag moves."""

    def test_apply_then_recover_then_reinstate_roundtrip(self):
        base = 0.85
        tag = 0.0
        # Deprecate three times -> strongly suppressed
        tag = apply_extinction(tag, 3)
        assert effective_strength(base, tag) < base
        # Time passes -> partial spontaneous recovery
        tag = spontaneous_recovery(tag, RECOVERY_HALF_LIFE_HOURS)
        # Reinstate -> exact original effective strength
        tag = reinstate(tag)
        assert effective_strength(base, tag) == pytest.approx(base)

    def test_base_argument_is_read_only_semantics(self):
        # effective_strength derives from base but the functions here only
        # ever return a NEW tag; base is a caller-owned value.
        base = 0.5
        out = deprecate(base, 0.0)
        assert isinstance(out, ExtinctionOutcome)
        # base unchanged in caller's hands
        assert base == 0.5


class TestIsExtinguished:
    def test_below_threshold_false(self):
        assert not is_extinguished(0.3)

    def test_at_threshold_true(self):
        assert is_extinguished(0.5)

    def test_default_zero_false(self):
        assert not is_extinguished(0.0)


class TestDeprecateAblation:
    def test_deprecate_grows_tag_when_enabled(self, monkeypatch):
        monkeypatch.delenv("CORTEX_ABLATE_EXTINCTION", raising=False)
        out = deprecate(0.8, 0.0, trials=1)
        assert out.operation == "extinguish"
        assert out.new_extinction_strength == pytest.approx(EXTINCTION_TRIAL_GAIN)
        assert out.effective_strength < 0.8

    def test_deprecate_noop_when_ablated(self, monkeypatch):
        monkeypatch.setenv("CORTEX_ABLATE_EXTINCTION", "1")
        out = deprecate(0.8, 0.0, trials=1)
        assert out.operation == "noop"
        assert out.new_extinction_strength == 0.0
        # Behaviour-preserving: effective == base when ablated with no prior tag
        assert out.effective_strength == pytest.approx(0.8)

    def test_ablated_preserves_existing_tag(self, monkeypatch):
        monkeypatch.setenv("CORTEX_ABLATE_EXTINCTION", "1")
        out = deprecate(1.0, 0.4, trials=2)
        assert out.new_extinction_strength == pytest.approx(0.4)
        assert out.operation == "noop"
