"""Hierarchical predictive coding -- Fristonian multi-level novelty gate.

source: ADR-0189"""

from __future__ import annotations

import math

from mcp_server.core.predictive_coding_flat import (
    compute_embedding_novelty,
    compute_entity_novelty,
    compute_structural_novelty,
    compute_temporal_novelty,
)
from mcp_server.core.predictive_coding_gate import (
    PrecisionState,
    neuromodulate_precisions,
)
from mcp_server.core.predictive_coding_signals import (
    HierarchicalPrediction,
    PredictionLevel,
    compute_entity_errors,
    compute_schema_errors,
    compute_sensory_errors,
    compute_sensory_prediction,
)
from mcp_server.core.forward_model import prediction_error, scalar_of
from mcp_server.core.predictive_coding_signals import extract_sensory_features
from mcp_server.core.ablation import Mechanism, is_mechanism_disabled

__all__ = [
    "PredictionLevel",
    "HierarchicalPrediction",
    "PrecisionState",
    "compute_sensory_prediction",
    "compute_sensory_errors",
    "compute_entity_errors",
    "compute_schema_errors",
    "compute_hierarchical_novelty",
    "compute_embedding_novelty",
    "compute_entity_novelty",
    "compute_temporal_novelty",
    "compute_structural_novelty",
    "neuromodulate_precisions",
]


# source: ADR-0189


# source: ADR-0189

_DEFAULT_LEVEL_PRECISIONS = [1.0, 1.0, 1.0]  # Sensory, Entity, Schema


def _level_precisions(
    precision_state: PrecisionState | None,
    ne_level: float,
    ach_level: float,
) -> list[float]:
    """Cross-level precisions pi_i, neuromodulated by NE (gain) and ACh (ratio).

    source: ADR-0189"""
    base = (
        precision_state.level_precisions
        if precision_state is not None
        else list(_DEFAULT_LEVEL_PRECISIONS)
    )
    return neuromodulate_precisions(base, ne_level, ach_level)


# -- Main orchestrator ---------------------------------------------------------


def _compute_prediction_levels(
    content: str,
    new_entity_names: list[str],
    known_entity_names: set[str],
    recent_memories_features: list[dict[str, float]],
    schema_match_score: float,
    schema_free_energy: float,
    schema_predictions: dict[str, float] | None,
    schema_precisions: dict[str, float] | None,
    domain_familiarity: float,
) -> list[PredictionLevel]:
    """Compute prediction errors at all three hierarchical levels."""
    sensory_pred, sensory_prec = compute_sensory_prediction(recent_memories_features)
    level_0 = compute_sensory_errors(content, sensory_pred, sensory_prec)
    level_1 = compute_entity_errors(
        new_entity_names,
        known_entity_names,
        schema_predictions,
        schema_precisions,
    )
    level_2 = compute_schema_errors(
        schema_match_score,
        schema_free_energy,
        domain_familiarity,
    )
    return [level_0, level_1, level_2]


def _aggregate_novelty(
    levels: list[PredictionLevel],
    level_precisions: list[float],
) -> tuple[float, float]:
    """Combine per-level free energies into total free energy + novelty score.

    source: ADR-0189"""
    # source: ADR-0189

    total_fe = sum(
        prec * level.free_energy
        for prec, level in zip(level_precisions, levels, strict=True)
    )
    # source: ADR-0189

    novelty = 1.0 / (1.0 + math.exp(-3.0 * (total_fe - 0.5)))
    return total_fe, max(0.0, min(1.0, novelty))


def _forward_model_error(
    content: str,
    recent_memories_features: list[dict[str, float]],
) -> float:
    """B3 cerebellar forward-model corrective-error term for the novelty score.

    source: ADR-0189

    Distinct from the Level-0 sensory novelty (which scores the new item against
    the per-feature mean/variance of recent items): this scores the new item
    against a *corrected running estimate of the trajectory*, the genuinely-new
    B3 contribution (see forward_model.py honesty note). Kept small and additive.
    """

    if not recent_memories_features:
        return 0.0
    trajectory = [scalar_of(f) for f in recent_memories_features]
    actual = scalar_of(extract_sensory_features(content))
    return abs(prediction_error(trajectory, actual))


def compute_hierarchical_novelty(
    content: str,
    new_entity_names: list[str],
    known_entity_names: set[str],
    recent_memories_features: list[dict[str, float]],
    *,
    schema_match_score: float = 0.0,
    schema_free_energy: float = 0.0,
    schema_predictions: dict[str, float] | None = None,
    schema_precisions: dict[str, float] | None = None,
    domain_familiarity: float = 0.5,
    ach_level: float = 0.5,
    ne_level: float = 1.0,
    precision_state: PrecisionState | None = None,
    include_forward_model: bool = False,
) -> HierarchicalPrediction:
    """Run the full hierarchical predictive coding pipeline.

    source: ADR-0189"""
    levels = _compute_prediction_levels(
        content,
        new_entity_names,
        known_entity_names,
        recent_memories_features,
        schema_match_score,
        schema_free_energy,
        schema_predictions,
        schema_precisions,
        domain_familiarity,
    )

    level_precisions = _level_precisions(precision_state, ne_level, ach_level)
    total_fe, novelty = _aggregate_novelty(levels, level_precisions)

    fm_error = 0.0
    if include_forward_model:
        if not is_mechanism_disabled(Mechanism.FORWARD_MODEL):
            fm_error = _forward_model_error(content, recent_memories_features)
            if fm_error > 0.0:
                total_fe = total_fe + fm_error
                novelty = 1.0 / (1.0 + math.exp(-3.0 * (total_fe - 0.5)))
                novelty = max(0.0, min(1.0, novelty))

    return HierarchicalPrediction(
        levels=levels,
        total_free_energy=round(total_fe, 6),
        novelty_score=round(novelty, 4),
    )
