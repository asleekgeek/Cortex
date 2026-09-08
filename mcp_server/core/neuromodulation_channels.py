"""Individual neuromodulator channel computations.

source: ADR-0209"""

from __future__ import annotations

# source: ADR-0209


DA_ALPHA = 0.3  # DA phasic RPE bursts (~100ms in biology)
NE_ALPHA = 0.2  # LC phasic responses (~seconds in biology)
ACH_ALPHA = 0.4  # ACh tracks theta oscillations (~200ms cycle)
SER_ALPHA = 0.15  # 5-HT tonic modulation (minutes/hours in biology)

# source: ADR-0209


_DA_NE_COUPLING = -0.15  # High DA dampens NE (success reduces arousal)
_NE_ACH_COUPLING = 0.2  # High NE boosts ACh (arousal enhances encoding)
_SER_DA_COUPLING = -0.1  # High 5-HT dampens DA (inhibition reduces reward sensitivity)
_ACH_SER_COUPLING = -0.15  # High ACh dampens 5-HT (encoding reduces exploration)

# source: ADR-0209


NE_HABITUATION_RATE = 0.05
NE_HABITUATION_DECAY = 0.02


# ── Channel Computation Functions ──────────────────────────────────────


def compute_dopamine_rpe(
    outcome_positive: bool,
    outcome_negative: bool,
    memory_importance: float,
    da_baseline: float,
) -> tuple[float, float]:
    """Rescorla-Wagner RPE.

    source: ADR-0209

    Implements single-CS Rescorla-Wagner:
      delta = actual - V(s)                    (prediction error)
      V(s) := V(s) + alpha*beta * delta        (learning rule)
      DA = 1.0 + delta                         (firing rate mapping)

    source: ADR-0209

    Returns:
        (da_level, updated_baseline).
    """
    # source: ADR-0209
    if outcome_positive:
        actual = 0.7 + memory_importance * 0.3
    elif outcome_negative:
        actual = 0.2 - memory_importance * 0.1
    else:
        actual = 0.5

    # Rescorla-Wagner: delta = lambda - V(s)
    delta = actual - da_baseline
    # Schultz: DA firing = baseline * (1 + delta), clamped to [0, 3x baseline]
    da = max(0.0, min(3.0, 1.0 + delta))

    # source: ADR-0209

    new_baseline = da_baseline + 0.1 * (actual - da_baseline)
    new_baseline = max(0.1, min(0.9, new_baseline))

    return da, new_baseline


def compute_norepinephrine_arousal(
    error_encountered: bool,
    current_ne: float,
    ne_adaptation: float,
) -> tuple[float, float]:
    """Update arousal and adaptation from error feedback.

    source: ADR-0209

    Returns:
        (ne_level, updated_adaptation).
    """
    if error_encountered:
        burst = 0.5 * (1.0 - ne_adaptation)
        ne = min(2.0, current_ne + burst)
        new_adapt = min(0.8, ne_adaptation + NE_HABITUATION_RATE)
    else:
        ne = current_ne + 0.1 * (1.0 - current_ne)
        new_adapt = max(0.0, ne_adaptation - NE_HABITUATION_DECAY)

    return max(0.3, min(2.0, ne)), new_adapt


def compute_serotonin_exploration(
    schema_match: float,
    novel_entities: int,
    total_entities: int,
    current_ser: float,
) -> float:
    """Compute an exploration signal from schema match and entity novelty.

    source: ADR-0209

    Returns:
        Updated 5-HT level (EMA-blended with current).
    """
    novelty_ratio = (
        novel_entities / max(total_entities, 1) if total_entities > 0 else 0.5
    )
    exploitation_signal = schema_match

    target = 0.5 + novelty_ratio * 0.8 - exploitation_signal * 0.5
    target = max(0.3, min(1.8, target))

    return current_ser + SER_ALPHA * (target - current_ser)


def apply_cross_coupling(
    da: float,
    ne: float,
    ach: float,
    ser: float,
) -> tuple[float, float, float, float]:
    """Apply additive cross-channel coupling.

    source: ADR-0209

    Returns:
        Post-coupling (da, ne, ach, ser).
    """
    ne_coupled = ne + _DA_NE_COUPLING * (da - 1.0)
    ach_coupled = ach + _NE_ACH_COUPLING * (ne - 1.0)
    da_coupled = da + _SER_DA_COUPLING * (ser - 1.0)
    ser_coupled = ser + _ACH_SER_COUPLING * (ach - 1.0)

    return (
        max(0.0, min(3.0, da_coupled)),  # source: ADR-0209
        max(0.3, min(2.0, ne_coupled)),
        max(0.3, min(2.0, ach_coupled)),
        max(0.3, min(2.0, ser_coupled)),
    )
