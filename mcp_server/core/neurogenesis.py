"""Temporal-context dimension weighting and separation metrics.

source: ADR-0208"""

from __future__ import annotations

import math

from mcp_server.shared.linear_algebra import (
    cosine_similarity,
    norm,
    scale,
)

# ── Configuration ─────────────────────────────────────────────────────────

# source: ADR-0208

# source: ADR-0208
_NORM_EPSILON = 1e-10

# source: ADR-0208

# source: ADR-0208
_NEUROGENESIS_BOOST = 0.3

# source: ADR-0208

# source: ADR-0208
_SEPARATION_THRESHOLD = 0.75


# ── Temporal Separation Weights ──────────────────────────────────────────


def _compute_boost_magnitude(
    hours_since_creation: float,
    maturation_hours: float,
    boost: float,
) -> float:
    """Compute the neurogenesis boost magnitude based on memory maturity."""
    maturity = 1.0 - math.exp(-hours_since_creation / maturation_hours)
    immaturity = 1.0 - maturity
    return boost * immaturity


def _apply_dimension_boosts(
    weights: list[float],
    hours_since_creation: float,
    boost_magnitude: float,
) -> None:
    """Apply time-varying dimension boosts to weight vector (in-place)."""
    embedding_dim = len(weights)
    # source: ADR-0208

    _hours_per_bucket = 6.0
    _bucket_stride = 7
    _boosted_fraction = 0.1
    time_bucket = int(hours_since_creation / _hours_per_bucket)
    boosted_start = (time_bucket * _bucket_stride) % embedding_dim
    boosted_count = max(1, int(embedding_dim * _boosted_fraction))

    for i in range(boosted_count):
        dim_idx = (boosted_start + i) % embedding_dim
        weights[dim_idx] = 1.0 + boost_magnitude


def compute_temporal_separation_weights(
    hours_since_creation: float,
    embedding_dim: int,
    *,
    boost: float = _NEUROGENESIS_BOOST,
    # source: ADR-0208
    maturation_hours: float = 48.0,
) -> list[float]:
    """Compute dimension-specific weights for temporal-context encoding.

    source: ADR-0208

    Args:
        hours_since_creation: Age of the memory in hours.
        embedding_dim: Dimensionality of embeddings.
        boost: Extra weight applied to the boosted dimension subset at age 0.
        maturation_hours: Time-constant over which the boost decays.

    Returns:
        Per-dimension weight vector (length = embedding_dim).
    """
    boost_magnitude = _compute_boost_magnitude(
        hours_since_creation,
        maturation_hours,
        boost,
    )
    weights = [1.0] * embedding_dim
    _apply_dimension_boosts(weights, hours_since_creation, boost_magnitude)
    return weights


def apply_temporal_weights(
    embedding: list[float],
    weights: list[float],
) -> list[float]:
    """Apply temporal separation weights to an embedding.

    Element-wise multiplication followed by renormalization.

    Returns:
        Temporally-weighted embedding (unit norm).
    """
    if len(embedding) != len(weights):
        return list(embedding)

    # source: ADR-0208

    weighted = [e * w for e, w in zip(embedding, weights, strict=True)]
    weighted_norm = norm(weighted)
    if weighted_norm > _NORM_EPSILON:
        weighted = scale(weighted, 1.0 / weighted_norm)
    return weighted


# ── Separation Metrics ────────────────────────────────────────────────────


def compute_separation_index(
    original_embedding: list[float],
    separated_embedding: list[float],
) -> float:
    """Compute how much an embedding was changed by pattern separation.

    Returns 0.0 if unchanged, approaches 1.0 if completely orthogonalized.
    """
    sim = cosine_similarity(original_embedding, separated_embedding)
    return max(0.0, 1.0 - sim)


def compute_interference_score(
    embedding: list[float],
    neighbor_embeddings: list[list[float]],
    *,
    threshold: float = _SEPARATION_THRESHOLD,
) -> float:
    """Compute how much interference pressure a memory faces.

    Returns average similarity to neighbors above threshold, weighted
    by how far above threshold each neighbor is. Score of 0.0 means
    no interference pressure.
    """
    if not neighbor_embeddings:
        return 0.0

    excess_similarities = []
    for neighbor in neighbor_embeddings:
        sim = cosine_similarity(embedding, neighbor)
        if sim > threshold:
            excess_similarities.append(sim - threshold)

    if not excess_similarities:
        return 0.0

    avg_excess = sum(excess_similarities) / len(neighbor_embeddings)
    return min(1.0, avg_excess / (1.0 - threshold))
