"""Oscillatory phase computation -- theta, gamma, and SWR gating logic.

source: ADR-0212"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

# -- Phase Enumerations -------------------------------------------------------


class ThetaPhase(Enum):
    """Which phase of the theta cycle the system is in.

    Encoding phase (0.0-0.5): High ACh, strong EC->CA1, weak CA3->CA1.
    Retrieval phase (0.5-1.0): Low ACh, weak EC->CA1, strong CA3->CA1.
    Transition zone near 0.5 where the sigmoid crosses 0.5.
    """

    ENCODING = "encoding"
    RETRIEVAL = "retrieval"
    TRANSITION = "transition"


class SWRState(Enum):
    """Sharp-wave ripple state."""

    QUIESCENT = "quiescent"  # Normal operation, no ripple
    RIPPLE = "ripple"  # Active SWR -- replay and plasticity enabled
    REFRACTORY = "refractory"  # Post-ripple cooldown, no new ripple


# source: ADR-0212

# source: ADR-0212


SUPPRESSION_X = 0.7

# source: ADR-0212


SIGMOID_STEEPNESS = 20

# source: ADR-0212

ACH_BASELINE = 0.3

# Transition zone width (fraction of cycle on each side of phase boundary)
TRANSITION_WIDTH = 0.08

# source: ADR-0212
GAMMA_CAPACITY = 7

# source: ADR-0212


# Minimum interval between SWR events (hours)
SWR_MIN_INTERVAL_HOURS = 0.5

# Base probability threshold for SWR triggering
SWR_BASE_PROBABILITY = 0.3

# Duration of a single SWR burst (in consolidation steps)
SWR_BURST_STEPS = 5

# Refractory period after SWR (consolidation steps)
SWR_REFRACTORY_STEPS = 3

# source: ADR-0212

# source: ADR-0212
_SWR_MIN_OPERATIONS = 3

# source: ADR-0212

# source: ADR-0212
_EXP_ARG_CLAMP = 500.0

# source: ADR-0212
# source: ADR-0212
_THETA_HALF_CYCLE = 0.5


# -- Oscillatory State --------------------------------------------------------


@dataclass
class OscillatoryState:
    """Full oscillatory state of the memory system.

    Pure data object -- no side effects. Functions compute state transitions
    and return new states.
    """

    theta_phase: float = 0.0
    gamma_count: int = 0
    swr_state: str = "quiescent"  # Store as string for serialization
    swr_steps_remaining: int = 0
    theta_cycles_total: int = 0
    operations_since_swr: int = 0
    hours_since_last_swr: float = 0.0
    ach_level: float = 0.8  # Start in encoding mode


# source: ADR-0212


def _sigmoid_gate(phase: float, k: float = SIGMOID_STEEPNESS) -> float:
    """Encoding-to-retrieval transition: 0 at phase<<0.5, 1 at phase>>0.5.

    source: ADR-0212"""
    exponent = -k * (phase - 0.5)
    # source: ADR-0212
    if exponent > _EXP_ARG_CLAMP:
        return 0.0
    if exponent < -_EXP_ARG_CLAMP:
        return 1.0
    return 1.0 / (1.0 + math.exp(exponent))


# -- Theta Phase Logic ---------------------------------------------------------


def classify_theta_phase(phase: float) -> ThetaPhase:
    """Classify a theta phase value into encoding, retrieval, or transition.

    Phase 0.0-0.5 is encoding (strong EC->CA1, high ACh).
    Phase 0.5-1.0 is retrieval (strong CA3->CA1, low ACh).
    Narrow bands around 0.0, 0.5 are transitions (blended behavior).
    """
    phase = phase % 1.0

    if phase < TRANSITION_WIDTH or phase > (1.0 - TRANSITION_WIDTH):
        return ThetaPhase.TRANSITION
    if abs(phase - 0.5) < TRANSITION_WIDTH:
        return ThetaPhase.TRANSITION

    if phase < _THETA_HALF_CYCLE:
        return ThetaPhase.ENCODING
    return ThetaPhase.RETRIEVAL


def compute_encoding_strength(phase: float) -> float:
    """EC->CA1 gain: 1.0 during encoding, (1-X)=0.3 during retrieval.

    source: ADR-0212"""
    phase = phase % 1.0
    gate = _sigmoid_gate(phase)
    return 1.0 - gate * SUPPRESSION_X


def compute_retrieval_strength(phase: float) -> float:
    """CA3->CA1 gain: (1-X)=0.3 during encoding, 1.0 during retrieval.

    source: ADR-0212"""
    phase = phase % 1.0
    gate = _sigmoid_gate(phase)
    return (1.0 - SUPPRESSION_X) + gate * SUPPRESSION_X


def compute_ach_from_phase(phase: float) -> float:
    """ACh level: ~1.0 during encoding, ACH_BASELINE=0.3 during retrieval.

    source: ADR-0212"""
    phase = phase % 1.0
    gate = _sigmoid_gate(phase)
    return 1.0 - gate * (1.0 - ACH_BASELINE)


# -- Gamma Binding -------------------------------------------------------------


def can_bind_item(gamma_count: int, capacity: int = GAMMA_CAPACITY) -> bool:
    """Check if there's gamma capacity to bind another item this theta cycle."""
    return gamma_count < capacity


def gamma_binding_strength(position: int, capacity: int = GAMMA_CAPACITY) -> float:
    """Compute binding strength for the Nth item in a gamma sequence.

    First item gets strongest binding (primacy), last item gets a recency boost.
    Middle items weaken. Models the serial position effect.
    Returns value in [0.5, 1.0].
    """
    if capacity <= 1:
        return 1.0

    primacy = math.exp(-0.5 * position)
    recency = math.exp(-0.5 * (capacity - 1 - position))
    raw = max(primacy, recency)
    return 0.5 + 0.5 * min(raw, 1.0)


# -- Sharp-Wave Ripple Logic ---------------------------------------------------


def _compute_swr_probability(
    operations_since_swr: int,
    hours_since_last_swr: float,
    accumulated_importance: float,
    base_probability: float,
) -> float:
    """Compute SWR trigger probability from contributing factors.

    source: ADR-0212"""
    op_factor = min(operations_since_swr / 20.0, 1.0)
    imp_factor = min(accumulated_importance / 5.0, 1.0)
    time_factor = min(hours_since_last_swr / 4.0, 1.0)

    return base_probability * (0.4 * op_factor + 0.3 * imp_factor + 0.3 * time_factor)


def should_generate_swr(
    operations_since_swr: int,
    hours_since_last_swr: float,
    accumulated_importance: float = 0.0,
    *,
    min_interval_hours: float = SWR_MIN_INTERVAL_HOURS,
    base_probability: float = SWR_BASE_PROBABILITY,
) -> bool:
    """Determine whether to generate a sharp-wave ripple event.

    source: ADR-0212"""
    if hours_since_last_swr < min_interval_hours:
        return False
    if operations_since_swr < _SWR_MIN_OPERATIONS:
        return False

    probability = _compute_swr_probability(
        operations_since_swr,
        hours_since_last_swr,
        accumulated_importance,
        base_probability,
    )
    return probability >= base_probability * 0.5


def _compute_heat_score(heat: float) -> float:
    """Compute inverted-U heat score for replay priority.

    Moderate heat memories need replay most -- too hot means already active,
    too cold means not worth replaying. Peak at heat=0.5.
    """
    return max(0.0, 1.0 - 4.0 * (heat - 0.5) ** 2)


def compute_replay_priority(
    heat: float,
    importance: float,
    surprise: float,
    access_count: int,
    hours_since_creation: float,
) -> float:
    """Compute which memories should be replayed during an SWR event.

    source: ADR-0212

    Returns replay priority score [0, 1].
    """
    heat_score = _compute_heat_score(heat)
    rehearsal_need = 1.0 / (1.0 + access_count * 0.5)
    recency = math.exp(-hours_since_creation / 168.0)  # Week time constant

    priority = (
        importance * 0.35
        + heat_score * 0.20
        + surprise * 0.20
        + rehearsal_need * 0.15
        + recency * 0.10
    )
    return min(1.0, max(0.0, priority))
