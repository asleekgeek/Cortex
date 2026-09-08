"""Interference detection — proactive and retroactive interference helpers.

source: ADR-0194"""

from __future__ import annotations

from mcp_server.shared.linear_algebra import cosine_similarity
from mcp_server.shared.similarity import jaccard_similarity
from mcp_server.core.cascade_stages import compute_interference_resistance

# source: ADR-0194


# source: ADR-0194

_INTERFERENCE_THRESHOLD = 0.7

# source: ADR-0194


_CONTEXT_DISCOUNT = 0.3

# source: ADR-0194


_CRITICAL_INTERFERENCE = 0.85

# source: ADR-0194

# source: ADR-0194
_NEAR_DUPLICATE_SIMILARITY = 0.9

# source: ADR-0194

# source: ADR-0194
_COLD_HEAT = 0.2

# source: ADR-0194
# source: ADR-0194
_NEGLIGIBLE_RISK = 0.2


# ── Resolution Hints ─────────────────────────────────────────────────────


def _suggest_pi_resolution(score: float, similarity: float, stage: str) -> str:
    """Suggest resolution strategy for proactive interference.

    source: ADR-0194"""
    if score >= _CRITICAL_INTERFERENCE:
        return "pattern_separation"
    if similarity > _NEAR_DUPLICATE_SIMILARITY:
        return "merge_or_update"
    if stage == "consolidated":
        return "context_binding"
    return "normal_encoding"


def _suggest_ri_resolution(score: float, stage: str, heat: float) -> str:
    """Suggest resolution strategy for retroactive interference.

    source: ADR-0194"""
    if score >= _CRITICAL_INTERFERENCE:
        return "protect_old_memory"
    if stage in ("labile", "early_ltp"):
        return "accelerate_consolidation"
    if heat < _COLD_HEAT:
        return "accept_overwrite"
    return "orthogonalize_at_sleep"


# ── Proactive Interference ───────────────────────────────────────────────


def _compute_pi_score(
    sim: float,
    entity_overlap: float,
    heat_factor: float,
    stage: str,
    context_match: float,
) -> float:
    """Compute proactive interference score from component signals.

    source: ADR-0194"""
    stage_factor = {
        "consolidated": 1.2,
        "late_ltp": 1.0,
        "early_ltp": 0.8,
        "labile": 0.5,
    }.get(stage, 0.7)

    return (
        sim * 0.4 + entity_overlap * 0.25 + heat_factor * 0.2 + stage_factor * 0.15
    ) * context_match


def _compute_pi_context_match(mem: dict) -> float:
    """Context discount: different directories reduce interference.

    source: ADR-0194"""
    if mem.get("directory_context") and mem["directory_context"] != mem.get(
        "new_directory", ""
    ):
        return 1.0 - _CONTEXT_DISCOUNT
    return 1.0


def _build_pi_result(
    mem: dict,
    sim: float,
    entity_overlap: float,
    score: float,
    stage: str,
) -> dict:
    """Build a proactive interference result dict."""
    return {
        "memory_id": mem.get("id"),
        "similarity": round(sim, 4),
        "entity_overlap": round(entity_overlap, 4),
        "interference_score": round(score, 4),
        "interference_type": "proactive",
        "resolution_hint": _suggest_pi_resolution(score, sim, stage),
    }


def _evaluate_pi_candidate(
    mem: dict,
    new_embedding: list[float],
    new_entity_set: set[str],
    threshold: float,
) -> dict | None:
    """Evaluate one existing memory for proactive interference."""
    emb = mem.get("embedding")
    if not emb or len(emb) != len(new_embedding):
        return None

    sim = cosine_similarity(new_embedding, emb)
    if sim < threshold:
        return None

    mem_entities = set(mem.get("entities", []))
    entity_overlap = (
        jaccard_similarity(new_entity_set, mem_entities)
        if (new_entity_set or mem_entities)
        else 0.0
    )

    stage = mem.get("consolidation_stage", "labile")
    score = _compute_pi_score(
        sim, entity_overlap, mem.get("heat", 0.5), stage, _compute_pi_context_match(mem)
    )
    if score < threshold * 0.7:
        return None

    return _build_pi_result(mem, sim, entity_overlap, score, stage)


def detect_proactive_interference(
    new_memory_embedding: list[float],
    new_memory_entities: list[str],
    existing_memories: list[dict],
    *,
    threshold: float = _INTERFERENCE_THRESHOLD,
) -> list[dict]:
    """Detect old memories that may interfere with encoding a new memory.

    source: ADR-0194

    Args:
        new_memory_embedding: Embedding of the incoming memory.
        new_memory_entities: Entities in the incoming memory.
        existing_memories: List of dicts with 'embedding', 'entities', 'heat',
            'id', 'directory_context', 'consolidation_stage'.
        threshold: Similarity threshold for interference.
    source: ADR-0194

    Returns:
        List of interference descriptors, sorted by severity.
    """
    new_entity_set = set(new_memory_entities)
    interferences = []

    for mem in existing_memories:
        result = _evaluate_pi_candidate(
            mem,
            new_memory_embedding,
            new_entity_set,
            threshold,
        )
        if result is not None:
            interferences.append(result)

    interferences.sort(key=lambda x: x["interference_score"], reverse=True)
    return interferences


# ── Retroactive Interference ─────────────────────────────────────────────


def _compute_vulnerability(
    old_stage: str,
    sim: float,
    old_heat: float,
    old_importance: float,
) -> float:
    """Compute how vulnerable an old memory is to overwriting.

    source: ADR-0194"""

    resistance = compute_interference_resistance(old_stage, sim)
    return (1.0 - resistance) * (1.0 - old_heat * 0.5) * (1.0 - old_importance * 0.3)


def _evaluate_ri_candidate(
    mem: dict,
    new_embedding: list[float],
    new_importance: float,
    threshold: float,
) -> dict | None:
    """Evaluate one existing memory for retroactive interference risk."""
    emb = mem.get("embedding")
    if not emb or len(emb) != len(new_embedding):
        return None

    sim = cosine_similarity(new_embedding, emb)
    if sim < threshold:
        return None

    old_heat = mem.get("heat", 0.5)
    old_importance = mem.get("importance", 0.5)
    old_stage = mem.get("consolidation_stage", "labile")

    vulnerability = _compute_vulnerability(old_stage, sim, old_heat, old_importance)
    overwrite_pressure = new_importance * sim
    risk_score = vulnerability * overwrite_pressure

    # source: ADR-0194
    if risk_score <= _NEGLIGIBLE_RISK:
        return None

    return {
        "memory_id": mem.get("id"),
        "similarity": round(sim, 4),
        "vulnerability": round(vulnerability, 4),
        "overwrite_pressure": round(overwrite_pressure, 4),
        "risk_score": round(risk_score, 4),
        "interference_type": "retroactive",
        "resolution_hint": _suggest_ri_resolution(risk_score, old_stage, old_heat),
    }


def detect_retroactive_interference(
    new_memory_embedding: list[float],
    new_memory_importance: float,
    existing_memories: list[dict],
    *,
    threshold: float = _INTERFERENCE_THRESHOLD,
) -> list[dict]:
    """Detect old memories at risk of being overwritten by a new memory.

    source: ADR-0194

    Args:
        new_memory_embedding: Embedding of the incoming memory.
        new_memory_importance: Importance of the incoming memory.
        existing_memories: List of memory dicts.
        threshold: Similarity threshold for interference.
    source: ADR-0194

    Returns:
        List of at-risk memories with interference descriptors.
    """
    at_risk = []

    for mem in existing_memories:
        result = _evaluate_ri_candidate(
            mem,
            new_memory_embedding,
            new_memory_importance,
            threshold,
        )
        if result is not None:
            at_risk.append(result)

    at_risk.sort(key=lambda x: x["risk_score"], reverse=True)
    return at_risk
