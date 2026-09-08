"""Hebbian LTP/LTD and STDP updates.

source: ADR-0276"""

from __future__ import annotations

import math
from typing import Any

from mcp_server.core.ablation import Mechanism, is_mechanism_disabled
from mcp_server.core.synaptic_plasticity_stp import (
    _MAX_WEIGHT,
    _MIN_WEIGHT,
)

_LTP_RATE: float = 0.05
_LTD_RATE: float = 0.02
_BCM_THETA_DECAY: float = 0.95
_STDP_A_PLUS: float = 0.03
_STDP_A_MINUS: float = 0.02
_STDP_TAU_PLUS: float = 24.0
_STDP_TAU_MINUS: float = 24.0
# source: ADR-0276

# source: ADR-0276
_STDP_COINCIDENCE_HOURS: float = 0.001


def compute_bcm_phi(
    post_activity: float,
    theta: float,
) -> float:
    """BCM quadratic phi function: phi(c, theta_m) = c * (c - theta_m).

    source: ADR-0276"""
    return post_activity * (post_activity - theta)


def compute_ltp(
    current_weight: float,
    co_activation: float,
    pre_activity: float = 1.0,
    post_activity: float = 1.0,
    theta: float = 0.5,
    ltp_rate: float = _LTP_RATE,
    max_weight: float = _MAX_WEIGHT,
) -> float:
    """BCM LTP: dw = rate * phi(c, theta_m) * d * co_activation.

    source: ADR-0276"""
    phi = compute_bcm_phi(post_activity, theta)
    if phi <= 0:
        return current_weight
    delta = ltp_rate * phi * pre_activity * co_activation
    return min(max_weight, current_weight + delta)


def compute_ltd(
    current_weight: float,
    time_since_co_access_hours: float,
    ltd_rate: float = _LTD_RATE,
    min_weight: float = _MIN_WEIGHT,
    post_activity: float = 0.0,
    theta: float = 0.5,
) -> float:
    """BCM LTD: activity-based depression when 0 < c < theta_m.

    source: ADR-0276"""
    if post_activity > 0:
        phi = compute_bcm_phi(post_activity, theta)
        if phi < 0:
            delta = ltd_rate * abs(phi)
            return max(min_weight, current_weight - delta)
        return current_weight

    if time_since_co_access_hours <= 0:
        return current_weight
    decay = ltd_rate * math.log1p(time_since_co_access_hours / 24.0)
    return max(min_weight, current_weight - decay)


def update_bcm_threshold(
    current_theta: float,
    entity_activity: float,
    decay: float = _BCM_THETA_DECAY,
) -> float:
    """BCM sliding threshold: theta_m = E[c^2].

    source: ADR-0276

    Implemented as EMA: theta_m' = decay * theta_m + (1 - decay) * c^2.
    This is faithful to BCM theory.
    """
    return decay * current_theta + (1.0 - decay) * (entity_activity**2)


def _hebbian_single(
    edge: dict[str, Any],
    co_accessed_pairs: set[tuple[int, int]],
    entity_activities: dict[int, float],
    entity_thresholds: dict[int, float],
    hours: float,
    ltp_rate: float,
    ltd_rate: float,
) -> dict[str, Any]:
    """Process a single edge for Hebbian LTP or LTD."""
    src, tgt = edge["source_entity_id"], edge["target_entity_id"]
    w = edge.get("weight", 1.0)
    pair = (min(src, tgt), max(src, tgt))

    if pair in co_accessed_pairs:
        new_w = compute_ltp(
            w,
            co_activation=1.0,
            pre_activity=entity_activities.get(src, 0.5),
            post_activity=entity_activities.get(tgt, 0.5),
            theta=entity_thresholds.get(tgt, 0.5),
            ltp_rate=ltp_rate,
        )
        action = "ltp" if new_w > w else "none"
    else:
        new_w = compute_ltd(w, hours, ltd_rate=ltd_rate)
        action = "ltd" if new_w < w else "none"

    return {
        **edge,
        "weight": round(new_w, 6),
        "delta": round(new_w - w, 6),
        "action": action,
    }


def apply_hebbian_update(
    edges: list[dict[str, Any]],
    co_accessed_pairs: set[tuple[int, int]],
    entity_activities: dict[int, float],
    entity_thresholds: dict[int, float],
    hours_since_last_update: float = 1.0,
    ltp_rate: float = _LTP_RATE,
    ltd_rate: float = _LTD_RATE,
) -> list[dict[str, Any]]:
    """Apply Hebbian LTP/LTD to a batch of edges."""

    if is_mechanism_disabled(Mechanism.SYNAPTIC_PLASTICITY):
        # source: ADR-0276

        return [
            {
                **edge,
                "weight": edge.get("weight", 1.0),
                "delta": 0.0,
                "action": "none",
            }
            for edge in edges
        ]
    return [
        _hebbian_single(
            edge,
            co_accessed_pairs,
            entity_activities,
            entity_thresholds,
            hours_since_last_update,
            ltp_rate,
            ltd_rate,
        )
        for edge in edges
    ]


def compute_stdp_update(
    current_weight: float,
    delta_t_hours: float,
    a_plus: float = _STDP_A_PLUS,
    a_minus: float = _STDP_A_MINUS,
    tau_plus: float = _STDP_TAU_PLUS,
    tau_minus: float = _STDP_TAU_MINUS,
    min_weight: float = _MIN_WEIGHT,
    max_weight: float = _MAX_WEIGHT,
) -> float:
    """STDP: dt>0 (pre before post) -> LTP, dt<0 -> LTD."""
    if abs(delta_t_hours) < _STDP_COINCIDENCE_HOURS:
        return current_weight
    if delta_t_hours > 0:
        delta_w = a_plus * math.exp(-delta_t_hours / tau_plus)
    else:
        delta_w = -a_minus * math.exp(delta_t_hours / tau_minus)
    new_weight = current_weight + delta_w
    return max(min_weight, min(max_weight, round(new_weight, 6)))


def _stdp_single(
    pair: dict[str, Any],
    a_plus: float,
    a_minus: float,
    tau_plus: float,
    tau_minus: float,
) -> dict[str, Any]:
    """Process a single temporal pair for STDP."""
    dt = pair.get("delta_t_hours", 0)
    w = pair.get("current_weight", 1.0)
    new_w = compute_stdp_update(w, dt, a_plus, a_minus, tau_plus, tau_minus)
    if dt > _STDP_COINCIDENCE_HOURS:
        direction = "causal"
    elif dt < -_STDP_COINCIDENCE_HOURS:
        direction = "anti-causal"
    else:
        direction = "none"
    return {
        "source_entity_id": pair["source_entity_id"],
        "target_entity_id": pair["target_entity_id"],
        "new_weight": new_w,
        "delta": round(new_w - w, 6),
        "direction": direction,
    }


def apply_stdp_batch(
    temporal_pairs: list[dict[str, Any]],
    a_plus: float = _STDP_A_PLUS,
    a_minus: float = _STDP_A_MINUS,
    tau_plus: float = _STDP_TAU_PLUS,
    tau_minus: float = _STDP_TAU_MINUS,
) -> list[dict[str, Any]]:
    """Apply STDP to a batch of temporal entity co-occurrences."""
    return [
        _stdp_single(p, a_plus, a_minus, tau_plus, tau_minus) for p in temporal_pairs
    ]
