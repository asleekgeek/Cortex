"""Homeostatic plasticity — network-level stability mechanisms.

source: ADR-0191"""

from __future__ import annotations
from mcp_server.core.ablation import Mechanism, is_mechanism_disabled

# ── Configuration ─────────────────────────────────────────────────────────

# source: ADR-0191
_TARGET_HEAT = 0.4

# source: ADR-0191

_SCALING_RATE = 0.05

# source: ADR-0191
_BCM_THETA_DECAY = 0.95

# source: ADR-0191
_MIN_GLOBAL_EXCITABILITY = 0.1
_MAX_GLOBAL_EXCITABILITY = 0.9

# source: ADR-0191

_TARGET_ACTIVE_FRACTION = 0.3


# source: ADR-0191


def compute_scaling_factor(
    current_avg_heat: float,
    target_heat: float = _TARGET_HEAT,
    scaling_rate: float = _SCALING_RATE,
) -> float:
    """Compute a multiplicative scaling factor from current and target heat.

    source: ADR-0191

    Since delta_w = alpha * w * (r_target - r_actual), the new weight is:
        w_new = w + delta_w = w * (1 + alpha * (r_target - r_actual))

    source: ADR-0191

    Args:
        current_avg_heat: Current domain-average heat (r_actual).
        target_heat: Target average heat (r_target).
        scaling_rate: Rate constant alpha. Controls convergence speed.

    Returns:
        Multiplicative scaling factor. Apply to all heats in domain.
    """

    if is_mechanism_disabled(Mechanism.HOMEOSTATIC_PLASTICITY):
        # No-op: factor 1.0 -> no scaling applied.
        return 1.0
    return 1.0 + scaling_rate * (target_heat - current_avg_heat)


def apply_synaptic_scaling(
    heats: list[float],
    scaling_factor: float,
) -> list[float]:
    """Apply multiplicative scaling to a list of heat values.

    source: ADR-0191"""
    return [max(0.0, min(1.0, h * scaling_factor)) for h in heats]


# ── Metaplasticity (BCM Threshold) ────────────────────────────────────────


def compute_bcm_threshold(
    recent_activity_levels: list[float],
    current_threshold: float = 0.5,
    decay: float = _BCM_THETA_DECAY,
) -> float:
    """Compute the sliding BCM modification threshold.

    source: ADR-0191

    Args:
        recent_activity_levels: Recent activity levels (e.g., heat values).
        current_threshold: Current BCM threshold.
        decay: EMA decay rate.

    Returns:
        Updated BCM threshold.
    """
    if not recent_activity_levels:
        return current_threshold

    avg_squared = sum(a * a for a in recent_activity_levels) / len(
        recent_activity_levels
    )
    return decay * current_threshold + (1 - decay) * avg_squared


def compute_ltp_ltd_modulation(
    memory_heat: float,
    bcm_threshold: float,
) -> tuple[float, float]:
    """Compute LTP/LTD rate modulation using the BCM phi function.

    source: ADR-0191

    When c > theta_m: phi > 0 -> LTP.
    When 0 < c < theta_m: phi < 0 -> LTD.

    We convert phi into (ltp_multiplier, ltd_multiplier) pair, both in [0, 2]:
    - phi > 0: ltp_mult = 1 + phi (clamped to 2), ltd_mult = max(0, 1 - phi)
    - phi < 0: ltd_mult = 1 + |phi| (clamped to 2), ltp_mult = max(0, 1 - |phi|)

    Returns:
        (ltp_multiplier, ltd_multiplier). Both in [0, 2].
    """
    phi = memory_heat * (memory_heat - bcm_threshold)

    if phi >= 0:
        ltp_mult = min(2.0, 1.0 + phi)
        ltd_mult = max(0.0, 1.0 - phi)
    else:
        abs_phi = abs(phi)
        ltd_mult = min(2.0, 1.0 + abs_phi)
        ltp_mult = max(0.0, 1.0 - abs_phi)

    return ltp_mult, ltd_mult


# ── Intrinsic Excitability Regulation ─────────────────────────────────────


def compute_excitability_adjustment(
    excitabilities: list[float],
    *,
    target_active_fraction: float = _TARGET_ACTIVE_FRACTION,
    active_threshold: float = 0.5,
) -> float:
    """Compute global excitability adjustment for engram slots.

    source: ADR-0191

    Returns:
        Additive adjustment. Positive = boost, negative = dampen.
    """
    if not excitabilities:
        return 0.0

    active_count = sum(1 for e in excitabilities if e >= active_threshold)
    current_fraction = active_count / len(excitabilities)
    deviation = target_active_fraction - current_fraction
    return deviation * 0.1


def apply_excitability_bounds(
    excitability: float,
    adjustment: float = 0.0,
) -> float:
    """Apply global adjustment and clamp excitability to safe bounds.

    source: ADR-0191"""
    return max(
        _MIN_GLOBAL_EXCITABILITY,
        min(_MAX_GLOBAL_EXCITABILITY, excitability + adjustment),
    )


# source: ADR-0191


# source: ADR-0191


_DEFAULT_COHORT_SIGMA = 0.5

# source: ADR-0191


_DEFAULT_COHORT_STRENGTH = 0.3


def detect_hot_cohort(
    heats: list[float],
    mean: float,
    std: float,
    cohort_threshold_sigma: float = _DEFAULT_COHORT_SIGMA,
) -> list[int]:
    """Return indices of memories in the hot cohort (heat > mean + sigma*std).

    Pre: heats is a non-empty list of floats; mean/std describe its first
    two moments.
    Post: returns a (possibly empty) list of indices i such that
    heats[i] > mean + sigma*std. Indices are unique and in input order.

    source: ADR-0191"""
    if not heats or std <= 0:
        return []
    threshold = mean + cohort_threshold_sigma * std
    return [i for i, h in enumerate(heats) if h > threshold]


def apply_cohort_correction(
    heats: list[float],
    cohort_indices: list[int],
    target_mean: float,
    correction_strength: float = _DEFAULT_COHORT_STRENGTH,
) -> list[float]:
    """Subtractively pull the hot cohort toward target_mean; others untouched.

    Pre: heats values are in [0, 1]; cohort_indices are valid indices into
    heats; correction_strength in [0, 1]; target_mean in [0, 1].
    Post: returned list has the same length as heats. For i in
    cohort_indices: result[i] = clamp(heats[i] - strength*(heats[i] -
    target_mean), 0, 1). For i not in cohort: result[i] == heats[i].

    source: ADR-0191"""
    cohort_set = set(cohort_indices)
    result: list[float] = []
    for i, h in enumerate(heats):
        if i in cohort_set:
            delta = correction_strength * (h - target_mean)
            new = max(0.0, min(1.0, h - delta))
            result.append(new)
        else:
            result.append(h)
    return result
