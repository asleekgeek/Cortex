"""Synaptic Tagging & Capture (STC) — retroactive memory strengthening.

source: ADR-0279"""

from __future__ import annotations

from typing import Any
from mcp_server.core.ablation import Mechanism, is_mechanism_disabled

# source: ADR-0279


# source: ADR-0279


_DEFAULT_TRIGGER_IMPORTANCE: float = 0.7

# source: ADR-0279


_DEFAULT_MAX_WEAK_IMPORTANCE: float = 0.5

# source: ADR-0279


_DEFAULT_MIN_OVERLAP: float = 0.3

# source: ADR-0279

_DEFAULT_IMPORTANCE_BOOST: float = 0.25

# source: ADR-0279

_DEFAULT_HEAT_BOOST: float = 1.5

# source: ADR-0279


_DEFAULT_TAG_WINDOW_HOURS: float = 48.0

# source: ADR-0279


_DEFAULT_MAX_PROMOTIONS: int = 5

# source: ADR-0279


_BISTABLE_THRESHOLD: float = 0.5


def bistable_consolidation(z: float, dt: float = 1.0) -> float:
    """Evaluate the Luboeinski bistable consolidation ODE.

    source: ADR-0279

    Parameters
    ----------
    z : Current consolidation state in [0, 1].
    dt : Time step for Euler integration. Default 1.0 (one discrete step).

    Returns
    -------
    Updated z, clamped to [0, 1].
    """
    dz = z * (1.0 - z) * (z - _BISTABLE_THRESHOLD)
    z_new = z + dz * dt
    return max(0.0, min(1.0, z_new))


def compute_initial_z(
    has_prp: bool,
    overlap: float,
) -> float:
    """Compute the initial consolidation variable z for a tagged synapse.

    In the Luboeinski model, z must exceed 0.5 to converge to full
    consolidation. PRPs from a strong event push z above the threshold
    proportionally to spatial proximity (entity overlap).

    Without PRPs (weak event only), z starts below threshold and will
    decay to 0 — the tag was set but no capture occurs.

    Parameters
    ----------
    has_prp : Whether PRPs are available (strong event occurred nearby).
    overlap : Entity overlap ratio [0, 1] — proxy for spatial proximity.
    """
    if not has_prp:
        # Tag set but no PRPs available — z below threshold, will decay.
        return overlap * 0.4  # max 0.4 < 0.5 threshold

    # source: ADR-0279

    return _BISTABLE_THRESHOLD + overlap * _BISTABLE_THRESHOLD


def _score_candidate(
    mem: dict[str, Any],
    new_memory_entities: set[str],
    max_weak_importance: float,
    tag_window_hours: float,
    min_overlap: float,
) -> tuple[float, dict[str, Any]] | None:
    """Score a single memory as a tagging candidate.

    A candidate must be:
    - Weak (importance <= max_weak_importance) — already-strong memories
      are already in late-LTP and don't need capture.
    - Recent (age <= tag_window_hours) — the synaptic tag has not expired.
    - Sharing entities with the triggering memory — proxy for dendritic
      proximity required for PRP diffusion.

    Returns (overlap, candidate_dict) or None if ineligible.
    """
    if mem.get("importance", 0) > max_weak_importance:
        return None
    if mem.get("age_hours", 999) > tag_window_hours:
        return None

    mem_entities = mem.get("entities", set())
    if not mem_entities:
        return None

    intersection = new_memory_entities & mem_entities
    if not intersection:
        return None

    # source: ADR-0279

    overlap = len(intersection) / min(len(new_memory_entities), len(mem_entities))
    if overlap < min_overlap:
        return None

    # source: ADR-0279

    z_initial = compute_initial_z(has_prp=True, overlap=overlap)
    z_final = bistable_consolidation(z_initial)

    return (
        overlap,
        {
            "memory_id": mem["id"],
            "overlap": round(overlap, 4),
            "matched_entities": sorted(intersection),
            "consolidation_z": round(z_final, 4),
        },
    )


def find_tagging_candidates(
    new_memory_entities: set[str],
    new_memory_importance: float,
    existing_memories: list[dict[str, Any]],
    trigger_importance: float = _DEFAULT_TRIGGER_IMPORTANCE,
    max_weak_importance: float = _DEFAULT_MAX_WEAK_IMPORTANCE,
    min_overlap: float = _DEFAULT_MIN_OVERLAP,
    tag_window_hours: float = _DEFAULT_TAG_WINDOW_HOURS,
    max_promotions: int = _DEFAULT_MAX_PROMOTIONS,
) -> list[dict[str, Any]]:
    """Find weak memories eligible for synaptic tag capture.

    source: ADR-0279

    Returns
    -------
    List of dicts with 'memory_id', 'overlap', 'matched_entities',
    and 'consolidation_z'.
    """
    # source: ADR-0279
    if new_memory_importance < trigger_importance or not new_memory_entities:
        return []

    candidates: list[tuple[float, dict[str, Any]]] = []
    for mem in existing_memories:
        result = _score_candidate(
            mem,
            new_memory_entities,
            max_weak_importance,
            tag_window_hours,
            min_overlap,
        )
        if result is not None:
            candidates.append(result)

    # Rank by overlap — closer synapses capture PRPs first.
    candidates.sort(key=lambda x: x[0], reverse=True)
    return [c[1] for c in candidates[:max_promotions]]


def compute_tag_boosts(
    overlap: float,
    current_importance: float,
    current_heat: float,
    importance_boost: float = _DEFAULT_IMPORTANCE_BOOST,
    heat_boost: float = _DEFAULT_HEAT_BOOST,
) -> dict[str, float]:
    """Compute boost values for a captured synapse (E-LTP -> L-LTP).

    source: ADR-0279

    Parameters
    ----------
    overlap : Entity overlap ratio [0, 1] — proxy for PRP diffusion reach.
    current_importance : Current importance of the weak (E-LTP) memory.
    current_heat : Current heat of the weak memory.
    importance_boost : Base additive importance boost. 0.25.
    heat_boost : Base multiplicative heat boost. 1.5.
    source: ADR-0279

    Returns
    -------
    Dict with 'new_importance', 'new_heat', 'importance_delta',
    'heat_delta', and 'consolidation_z'.
    """
    # Bistable consolidation from Luboeinski: z above 0.5 converges to 1.
    z = compute_initial_z(has_prp=True, overlap=overlap)
    z = bistable_consolidation(z)

    # Scale boosts by both overlap and consolidation state.
    # When z -> 1.0 (full consolidation), the full boost is applied.
    scaled_importance = importance_boost * overlap * z
    new_importance = min(1.0, current_importance + scaled_importance)

    scaled_heat = 1.0 + (heat_boost - 1.0) * overlap * z
    new_heat = min(1.0, current_heat * scaled_heat)

    return {
        "new_importance": round(new_importance, 4),
        "new_heat": round(new_heat, 4),
        "importance_delta": round(new_importance - current_importance, 4),
        "heat_delta": round(new_heat - current_heat, 4),
        "consolidation_z": round(z, 4),
    }


def _boost_candidate(
    candidate: dict[str, Any],
    existing_memories: list[dict[str, Any]],
    importance_boost: float,
    heat_boost: float,
) -> dict[str, Any] | None:
    """Look up the candidate memory and compute its capture boost."""
    mem = next(
        (m for m in existing_memories if m["id"] == candidate["memory_id"]),
        None,
    )
    if not mem:
        return None
    boosts = compute_tag_boosts(
        overlap=candidate["overlap"],
        current_importance=mem.get("importance", 0.5),
        current_heat=mem.get("heat", 0.1),
        importance_boost=importance_boost,
        heat_boost=heat_boost,
    )
    return {**candidate, **boosts}


def apply_synaptic_tags(
    new_memory_entities: set[str],
    new_memory_importance: float,
    existing_memories: list[dict[str, Any]],
    trigger_importance: float = _DEFAULT_TRIGGER_IMPORTANCE,
    max_weak_importance: float = _DEFAULT_MAX_WEAK_IMPORTANCE,
    min_overlap: float = _DEFAULT_MIN_OVERLAP,
    tag_window_hours: float = _DEFAULT_TAG_WINDOW_HOURS,
    max_promotions: int = _DEFAULT_MAX_PROMOTIONS,
    importance_boost: float = _DEFAULT_IMPORTANCE_BOOST,
    heat_boost: float = _DEFAULT_HEAT_BOOST,
) -> list[dict[str, Any]]:
    """Full STC pipeline: find tagged synapses and compute capture boosts.

    Implements the complete Synaptic Tagging & Capture sequence:
    1. Strong event (importance >= threshold) triggers PRP synthesis.
    2. Scan for weak memories with active tags (recent + entity overlap).
    3. Compute bistable consolidation z for each (Luboeinski model).
    4. Apply PRP-modulated boosts to importance and heat.
    """

    if is_mechanism_disabled(Mechanism.SYNAPTIC_TAGGING):
        # No-op: no retroactive promotion of weak memories.
        return []

    candidates = find_tagging_candidates(
        new_memory_entities=new_memory_entities,
        new_memory_importance=new_memory_importance,
        existing_memories=existing_memories,
        trigger_importance=trigger_importance,
        max_weak_importance=max_weak_importance,
        min_overlap=min_overlap,
        tag_window_hours=tag_window_hours,
        max_promotions=max_promotions,
    )

    results = []
    for candidate in candidates:
        boosted = _boost_candidate(
            candidate,
            existing_memories,
            importance_boost,
            heat_boost,
        )
        if boosted is not None:
            results.append(boosted)

    return results
