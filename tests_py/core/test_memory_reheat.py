"""Tests for core.memory_reheat — pure per-row heat_base recalibration
decision (I6-D5, INC6.6)."""

from __future__ import annotations

from mcp_server.core.memory_reheat import (
    DEFAULT_REHEAT_TARGET,
    ReheatDecision,
    compute_reheat_target,
)


class TestAlreadyAboveTarget:
    def test_row_at_target_is_never_touched(self):
        decision = compute_reheat_target(
            heat_base_before=0.5,
            effective_heat_before=0.25,
            effective_heat_at_max=0.9,
        )
        assert decision == ReheatDecision(0.5, False, True)

    def test_row_above_target_is_never_touched(self):
        decision = compute_reheat_target(
            heat_base_before=0.6,
            effective_heat_before=0.43,
            effective_heat_at_max=0.9,
        )
        assert decision.changed is False
        assert decision.new_heat_base == 0.6


class TestRaiseToExactTarget:
    def test_ratio_derivation_within_roundtrip_margin(self):
        # eh_at_max = 0.5 -> multiplier is 0.5 (at heat_base=1.0);
        # needed heat_base to reach 0.25 is 0.25 / 0.5 = 0.5, plus the
        # small float32-roundtrip overshoot margin (see
        # _FLOAT32_ROUNDTRIP_MARGIN's module-level comment) -- so the
        # result is slightly ABOVE 0.5, never below.
        decision = compute_reheat_target(
            heat_base_before=0.2,
            effective_heat_before=0.10,
            effective_heat_at_max=0.5,
        )
        assert decision.changed is True
        assert decision.reachable is True
        assert decision.new_heat_base >= 0.5
        assert abs(decision.new_heat_base - 0.5) < 1e-3  # margin is 1e-4 relative

    def test_never_lowers_even_if_needed_is_below_current_heat_base(self):
        # heat_base_before is already higher than the raw ratio would
        # suggest (e.g. floor-clamped eh_before made the ratio misleading
        # upstream) -- the max() floor must win.
        decision = compute_reheat_target(
            heat_base_before=0.6,
            effective_heat_before=0.10,
            effective_heat_at_max=0.5,
        )
        assert decision.new_heat_base >= 0.6

    def test_result_clamped_to_one(self):
        # needed = 0.25 / 0.01 = 25.0, way above the legal ceiling.
        decision = compute_reheat_target(
            heat_base_before=0.01,
            effective_heat_before=0.005,
            effective_heat_at_max=0.26,
        )
        assert decision.new_heat_base <= 1.0


class TestUnreachable:
    def test_eh_at_max_below_target_is_unreachable(self):
        # Even heat_base=1.0 caps effective_heat below the target --
        # a genuine consolidation-stage ceiling, not a solvable case.
        decision = compute_reheat_target(
            heat_base_before=0.1,
            effective_heat_before=0.10,
            effective_heat_at_max=0.10,
        )
        assert decision == ReheatDecision(0.1, False, False)

    def test_unreachable_row_heat_base_is_unchanged(self):
        decision = compute_reheat_target(
            heat_base_before=0.02,
            effective_heat_before=0.02,
            effective_heat_at_max=0.05,
        )
        assert decision.new_heat_base == 0.02
        assert decision.changed is False


class TestFloat32RoundtripMargin:
    """Regression: the campaign's first real apply run (INC6.6, 2026-07-10)
    showed the majority of "reheated" rows still failing effective_heat <
    target on immediate re-scan, because the exact target/eh_at_max ratio
    truncates through the heat_base column's REAL (float4) storage and
    back through effective_heat()'s own float4 boundary and lands
    fractionally under target. The margin must survive a simulated
    float32 round-trip."""

    def test_new_heat_base_survives_a_float32_roundtrip_above_target(self):
        import struct

        target = 0.25
        decision = compute_reheat_target(
            heat_base_before=0.05,
            effective_heat_before=0.05,
            effective_heat_at_max=0.5,
            target=target,
        )
        # Simulate PostgreSQL's REAL (float4) storage truncation.
        as_float32 = struct.unpack("f", struct.pack("f", decision.new_heat_base))[0]
        recomputed_eh = as_float32 * 0.5  # same eh_at_max multiplier
        assert recomputed_eh >= target, (
            f"heat_base={decision.new_heat_base} truncates to {as_float32} "
            f"(float32), recomputed effective_heat={recomputed_eh} < target"
        )


class TestDefaultTargetIsTheMeasuredCliff:
    def test_default_target_is_zero_point_two_five(self):
        assert DEFAULT_REHEAT_TARGET == 0.25

    def test_default_used_when_target_not_passed(self):
        decision = compute_reheat_target(
            heat_base_before=0.1,
            effective_heat_before=0.15,
            effective_heat_at_max=0.6,
        )
        # 0.15 < 0.25 default target -> must be raised, not left alone.
        assert decision.changed is True


class TestProtectedRowShape:
    """Protected/no_decay rows: effective_heat == heat_base * factor
    exactly (no decay multiplier). The ratio derivation must still hold
    since it never assumes a decay branch specifically."""

    def test_protected_row_ratio_still_exact(self):
        # factor=1.0, no decay: eh_before == heat_base_before exactly,
        # eh_at_max == 1.0 exactly (heat_base=1.0, factor=1.0, no decay).
        # needed = 0.25 * (1 + margin), so new_heat_base is slightly
        # above 0.25, never below.
        decision = compute_reheat_target(
            heat_base_before=0.20,
            effective_heat_before=0.20,
            effective_heat_at_max=1.0,
        )
        assert decision.new_heat_base >= 0.25
        assert abs(decision.new_heat_base - 0.25) < 1e-3
