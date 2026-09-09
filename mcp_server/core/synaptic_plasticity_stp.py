"""Tsodyks-Markram short-term plasticity, noise injection, and phase gating.

source: ADR-0278"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

# -- Tsodyks-Markram STP Constants (adapted timescale) -------------------------

# source: ADR-0278

_U_INCREMENT: float = 0.2

# source: ADR-0278

_TAU_F_HOURS: float = 0.5

# source: ADR-0278

_TAU_D_HOURS: float = 2.0

_NOISE_SCALE: float = 0.01

# -- Weight Bounds (shared with hebbian module) --------------------------------

_MIN_WEIGHT: float = 0.01
_MAX_WEIGHT: float = 2.0


# -- Synaptic State (Tsodyks-Markram) ------------------------------------------


@dataclass
class SynapticState:
    """Per-edge Tsodyks-Markram STP state.

    u: utilization parameter (facilitation). Starts at 0, boosted by U on
       each spike, decays with tau_F. Represents residual Ca2+ in terminal.
    x: available resources (1 = full vesicle pool, 0 = depleted). Starts at 1,
       depleted by u*x on each spike, recovers with tau_D.
    access_count: for noise scaling (Bayesian evidence accumulation).
    hours_since_last_access: for continuous recovery between spikes.
    """

    u: float = 0.0
    x: float = 1.0
    access_count: int = 0
    hours_since_last_access: float = 0.0


# -- Release Probability (Tsodyks-Markram) -------------------------------------


def compute_effective_release_probability(state: SynapticState) -> float:
    """Effective release: u_eff * x.

    source: ADR-0278

    u_eff = U + u * (1 - U): facilitation-boosted utilization.
    x: available vesicle fraction.
    Product gives transmission probability, clamped to [0.05, 0.95].
    """
    u_eff = _U_INCREMENT + state.u * (1.0 - _U_INCREMENT)
    p_eff = u_eff * state.x
    return max(0.05, min(0.95, p_eff))


def stochastic_transmit(
    state: SynapticState,
    rng: random.Random | None = None,
) -> bool:
    """Determine if a synaptic signal propagates (probabilistic).

    Returns True with probability = effective release probability.
    """
    p = compute_effective_release_probability(state)
    r = (rng or random).random()
    return r < p


# -- Tsodyks-Markram Dynamics --------------------------------------------------


def update_short_term_dynamics(
    state: SynapticState,
    hours_elapsed: float,
    is_access: bool = False,
) -> SynapticState:
    """Tsodyks-Markram STP update.

    source: ADR-0278

    Between spikes (continuous recovery):
      u(t) = u0 * exp(-t / tau_F)
      x(t) = 1 - (1 - x0) * exp(-t / tau_D)

    At spike (discrete update):
      u_new = u + U * (1 - u)      (facilitation boost)
      x_new = x - u_new * x        (vesicle depletion)

    Returns new SynapticState (original not mutated).
    """
    u, x = _recover_between_spikes(state.u, state.x, hours_elapsed)

    access_count = state.access_count
    hours_since = hours_elapsed

    if is_access:
        u, x, access_count, hours_since = _apply_spike(u, x, access_count)

    return SynapticState(
        u=round(u, 6),
        x=round(x, 6),
        access_count=access_count,
        hours_since_last_access=hours_since,
    )


def _recover_between_spikes(
    u: float,
    x: float,
    hours_elapsed: float,
) -> tuple[float, float]:
    """Continuous recovery: u decays to 0, x recovers to 1.

    source: ADR-0278"""
    if hours_elapsed <= 0:
        return u, x

    u_new = u * math.exp(-hours_elapsed / _TAU_F_HOURS)
    x_new = 1.0 - (1.0 - x) * math.exp(-hours_elapsed / _TAU_D_HOURS)
    return u_new, x_new


def _apply_spike(
    u: float,
    x: float,
    access_count: int,
) -> tuple[float, float, int, float]:
    """Spike event: facilitation boost + vesicle depletion.

    source: ADR-0278"""
    u_new = u + _U_INCREMENT * (1.0 - u)
    x_new = x - u_new * x
    x_new = max(0.0, x_new)
    return u_new, x_new, access_count + 1, 0.0


# -- Noise Injection -----------------------------------------------------------


def compute_noisy_weight_update(
    delta_w: float,
    access_count: int,
    noise_scale: float = _NOISE_SCALE,
    rng: random.Random | None = None,
) -> float:
    """Add Gaussian noise to a weight update, scaled by 1/sqrt(evidence).

    More observations (higher access_count) -> less noise -> more stable updates.
    """
    if access_count <= 0:
        evidence_factor = 1.0
    else:
        evidence_factor = 1.0 / math.sqrt(access_count)

    sigma = noise_scale * evidence_factor
    noise = (rng or random).gauss(0.0, sigma)
    return delta_w + noise


# source: ADR-0278


def phase_modulate_plasticity(
    delta_w: float,
    theta_phase: float,
    is_ltp: bool = True,
) -> float:
    """Modulate plasticity magnitude by theta phase.

    source: ADR-0278

    Encoding phase (0.0-0.5): LTP amplified, LTD suppressed.
    Retrieval phase (0.5-1.0): LTP suppressed, LTD amplified.
    Cosine envelope for smooth transition.
    """
    raw = math.cos(2.0 * math.pi * (theta_phase - 0.25))
    encoding_strength = 0.65 + 0.35 * raw

    if is_ltp:
        return delta_w * encoding_strength

    retrieval_strength = 0.65 - 0.35 * raw
    return delta_w * retrieval_strength
