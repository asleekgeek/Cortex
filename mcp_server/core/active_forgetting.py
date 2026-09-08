"""Core: active_forgetting — two independent dopaminergic forgetting circuits.

source: ADR-0098"""

from __future__ import annotations

from typing import Iterable

from mcp_server.core.cascade_stages import get_stage_properties_by_name
from mcp_server.core.curation import MERGE_THRESHOLD
from mcp_server.core.ablation import Mechanism, is_mechanism_disabled

# source: ADR-0098


TAU_DUP = MERGE_THRESHOLD

# source: ADR-0098

# source: ADR-0098
PRESSURE_LEAK_LAMBDA = 0.85
PERMANENT_ACCUM_THRESHOLD = 1.25662

# source: ADR-0098

# source: ADR-0098
ACUTE_OVERLAP_THRESHOLD = 0.575
ACUTE_RECENCY_WINDOW_HOURS = 13.0

# source: ADR-0098

# source: ADR-0098
CORTICAL_AVAILABILITY_BETA = 0.5


def cortical_availability(hippocampal_dependency: float) -> float:
    """Bounded, strictly-positive modulation factor for permanent-circuit pressure.

    source: ADR-0098"""
    dep = max(0.0, min(1.0, hippocampal_dependency))
    return 1.0 - CORTICAL_AVAILABILITY_BETA * dep


def chronic_interference(
    newer_sims: Iterable[float], tau_dup: float = TAU_DUP
) -> float:
    """Redundancy-gated excess noisy-OR over newer-neighbour similarities.

    Only neighbours at or above the near-duplicate cutoff ``tau_dup`` count as
    genuine retroactive interferers; each contributes its *excess* over the
    cutoff, rescaled to [0, 1]:

        source: ADR-0098"""
    product = 1.0
    span = 1.0 - tau_dup
    for s in newer_sims:
        s = max(0.0, min(1.0, float(s)))
        if s >= tau_dup:
            excess = 1.0 if span <= 0.0 else (s - tau_dup) / span
            product *= 1.0 - excess
    return 1.0 - product


def forgetting_pressure(
    stage: str,
    chronic: float,
    *,
    hippocampal_dependency: float = 0.0,
) -> float:
    """Instantaneous permanent-circuit pressure.

    ``= chronic × stage_vulnerability × cortical_availability(dep)``.

    source: ADR-0098"""
    vuln = get_stage_properties_by_name(stage).interference_vulnerability
    availability = cortical_availability(hippocampal_dependency)
    return max(0.0, chronic) * vuln * availability


def update_pressure_accum(
    prev_accum: float,
    stage: str,
    chronic: float,
    recently_active: bool,
    lam: float = PRESSURE_LEAK_LAMBDA,
    *,
    hippocampal_dependency: float = 0.0,
) -> float:
    """Advance the leaky integrator one cycle: ``λ·accum_{t-1} + pressure_t``.

    A sleep-protected (``recently_active``) cycle contributes ``pressure_t = 0``
    and lets the accumulator leak down — sleep inhibits the ongoing forgetting
    signal but does not erase accumulated erosion. ``lam`` ∈ [0, 1): the per-cycle
    retention of past pressure (1 − λ is natural recovery when interference abates).
    ``hippocampal_dependency`` (CLS-B gate C, default 0.0 = no modulation) is
    forwarded to ``forgetting_pressure`` — see its docstring.
    """
    pressure = (
        0.0
        if recently_active
        else forgetting_pressure(
            stage, chronic, hippocampal_dependency=hippocampal_dependency
        )
    )
    return lam * max(0.0, prev_accum) + pressure


def is_permanent_forgetting(
    accum: float,
    is_pinned: bool,
    recently_active: bool,
    theta: float = PERMANENT_ACCUM_THRESHOLD,
) -> bool:
    """Decide the Rac1 (permanent) circuit from the accumulated pressure.

    ``accum`` is the post-update leaky-integrator value for this cycle.
    ``is_pinned`` is user protection or an anchor (heat == 1.0); ``recently_active``
    means replayed/accessed this cycle (sleep quiets the ongoing forgetting
    signal). Either exempts the memory. Otherwise it is forgotten once *sustained*
    chronic-interference pressure overcomes the accumulation threshold.
    """
    if is_pinned or recently_active:
        return False
    return accum >= theta


def is_transient_forgetting(
    acute_overlap: float,
    acute_age_hours: float,
    is_pinned: bool,
    recently_active: bool,
) -> bool:
    """Decide the DAMB (transient) circuit: transiently suppress retrieval?

    source: ADR-0098"""
    if is_pinned or recently_active:
        return False
    return (
        acute_overlap >= ACUTE_OVERLAP_THRESHOLD
        and acute_age_hours <= ACUTE_RECENCY_WINDOW_HOURS
    )


# source: ADR-0058


def should_extinguish(
    accum: float,
    is_pinned: bool,
    recently_active: bool,
    *,
    already_stale: bool = False,
    theta: float = PERMANENT_ACCUM_THRESHOLD,
) -> bool:
    """Decide whether to reversibly deprecate a memory.

    source: ADR-0098
    """

    if is_mechanism_disabled(Mechanism.EXTINCTION):
        return False
    if is_pinned or recently_active or already_stale:
        return False
    return accum >= theta
