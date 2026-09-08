"""Pattern separation core — dentate gyrus orthogonalization and sparsification.

source: ADR-0253"""

from __future__ import annotations

from mcp_server.shared.linear_algebra import (
    cosine_similarity,
    dot,
    norm,
    scale,
    subtract,
)
from mcp_server.core.ablation import Mechanism, is_mechanism_disabled

# ── Configuration ─────────────────────────────────────────────────────────

# source: ADR-0253


_SEPARATION_THRESHOLD = 0.75

# source: ADR-0253

_IDENTITY_THRESHOLD = 0.95

# source: ADR-0253

_MIN_POST_SEPARATION_SIMILARITY = 0.3

# source: ADR-0253

# source: ADR-0253
_DEGENERATE_NORM_EPSILON = 1e-10

# source: ADR-0253


_SPARSITY_TARGET = 0.04


# ── Interference Detection ───────────────────────────────────────────────


def detect_interference_risk(
    new_embedding: list[float],
    existing_embeddings: list[list[float]],
    *,
    threshold: float = _SEPARATION_THRESHOLD,
    identity_threshold: float = _IDENTITY_THRESHOLD,
) -> list[tuple[int, float]]:
    """Detect which existing memories create interference risk for a new memory.

    Returns indices and similarities of memories that are similar enough to
    interfere but not identical (those are duplicates, not interference).

    Returns:
        List of (index, similarity) tuples, sorted by similarity descending.
    """
    risks: list[tuple[int, float]] = []
    for i, existing in enumerate(existing_embeddings):
        sim = cosine_similarity(new_embedding, existing)
        if threshold <= sim < identity_threshold:
            risks.append((i, sim))
    risks.sort(key=lambda x: x[1], reverse=True)
    return risks


# ── Orthogonalization ────────────────────────────────────────────────────


def _project_away_from_single(
    result: list[float],
    interferer: list[float],
    original: list[float],
    strength: float,
    min_similarity: float,
) -> list[float]:
    """Project result away from a single interferer, preserving semantic content.

    source: ADR-0253"""
    interferer_norm = norm(interferer)
    if interferer_norm < _DEGENERATE_NORM_EPSILON:
        return result

    projection_coeff = dot(result, interferer) / (interferer_norm**2)
    projection = scale(interferer, projection_coeff * strength)
    candidate = subtract(result, projection)

    candidate_norm = norm(candidate)
    if candidate_norm < _DEGENERATE_NORM_EPSILON:
        return result

    candidate = scale(candidate, 1.0 / candidate_norm)

    sim_with_original = cosine_similarity(original, candidate)
    if sim_with_original >= min_similarity:
        return candidate
    return result


def _normalize_result(result: list[float]) -> list[float]:
    """Normalize to unit length if non-degenerate."""
    result_norm = norm(result)
    if result_norm > _DEGENERATE_NORM_EPSILON:
        return scale(result, 1.0 / result_norm)
    return result


def orthogonalize_embedding(
    new_embedding: list[float],
    interfering_embeddings: list[list[float]],
    *,
    strength: float = 0.5,
    min_similarity: float = _MIN_POST_SEPARATION_SIMILARITY,
) -> tuple[list[float], float]:
    """Orthogonalize a new embedding away from interfering memories.

    Uses a Gram-Schmidt-like projection: subtract the component of the new
    embedding that lies in the subspace spanned by interfering memories.
    Strength controls how aggressively we separate (0=no change,
    1=full orthogonalization).

    Returns:
        Tuple of (orthogonalized_embedding, separation_index).
        separation_index = 1.0 - cosine_similarity(original, orthogonalized).
    """

    if is_mechanism_disabled(Mechanism.PATTERN_SEPARATION):
        # No-op: identity, zero separation.
        return list(new_embedding), 0.0
    if not interfering_embeddings:
        return list(new_embedding), 0.0

    result = list(new_embedding)
    dim = len(result)

    for interferer in interfering_embeddings:
        if len(interferer) != dim:
            continue
        result = _project_away_from_single(
            result, interferer, new_embedding, strength, min_similarity
        )

    result = _normalize_result(result)
    separation_index = 1.0 - cosine_similarity(new_embedding, result)
    return result, max(0.0, separation_index)


# ── Sparsification ───────────────────────────────────────────────────────


def apply_sparsification(
    embedding: list[float],
    *,
    sparsity: float = _SPARSITY_TARGET,
) -> list[float]:
    """Apply DG-like sparsification to an embedding.

    Zeroes out the smallest dimensions to achieve target sparsity.
    This simulates the DG's sparse activation pattern where only a few
    percent of granule cells are active.

    Note: this is a lossy operation. The caller should store the original
    embedding for later reference.

    Returns:
        Sparsified embedding (same length, many dimensions zeroed).
    """
    dim = len(embedding)
    k = max(1, int(dim * sparsity))

    indexed = [(abs(v), i) for i, v in enumerate(embedding)]
    indexed.sort(reverse=True)
    keep_indices = {idx for _, idx in indexed[:k]}

    result = [v if i in keep_indices else 0.0 for i, v in enumerate(embedding)]

    result_norm = norm(result)
    if result_norm > _DEGENERATE_NORM_EPSILON:
        result = scale(result, 1.0 / result_norm)

    return result
