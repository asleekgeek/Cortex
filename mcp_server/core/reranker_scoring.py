"""Score blending math for cross-encoder reranking.

source: ADR-0245"""

from __future__ import annotations

from mcp_server.core import platt_calibration, reranker_calibration


def _compute_retrieval_confidence(
    ce_scores: list[float],
    gate_threshold: float = 0.15,
    suppression: float = 0.1,
) -> float:
    """Compute confidence that retrieval found relevant results.

    source: ADR-0245

    Args:
        ce_scores: Raw cross-encoder scores from FlashRank.
        gate_threshold: Below this max CE, results are likely irrelevant.
            (0.15 default).
        suppression: Score multiplier when gated. (0.1 default).
    source: ADR-0245

    Returns:
        float — 1.0 (sufficient context) or suppression (insufficient).
    """
    if not ce_scores:
        return suppression
    max_ce = max(ce_scores)
    if max_ce >= gate_threshold:
        return 1.0
    return suppression


# source: ADR-0245
_MIN_SCORES_FOR_SPREAD = 2

# source: ADR-0245

# source: ADR-0245
_SPREAD_BOOST_FLOOR = 0.3


def _compute_adaptive_alpha(
    ce_scores: list[float],
    base_alpha: float,
) -> float:
    """Compute per-query alpha from CE score distribution.

    source: ADR-0245

    Args:
        ce_scores: Raw cross-encoder scores from FlashRank.
        base_alpha: Base alpha (0.70).
    source: ADR-0245

    Returns:
        Adaptive alpha in [base_alpha, base_alpha + 0.15].
    """
    if len(ce_scores) < _MIN_SCORES_FOR_SPREAD:
        return base_alpha

    spread = max(ce_scores) - min(ce_scores)
    # Only boost alpha when CE shows high discriminative power.
    # FlashRank scores are typically in [-1, 1], spread ∈ [0, 2].
    # High spread (>0.5) → CE found clear winner → small alpha boost.
    # Low spread → ambiguous → keep base alpha (don't reduce!).
    max_boost = 0.15  # source: ADR-0245
    if spread < _SPREAD_BOOST_FLOOR:
        return base_alpha
    # Linear boost above the floor, capped at max_boost
    normalized = min((spread - _SPREAD_BOOST_FLOOR) / 0.7, 1.0)
    return min(base_alpha + max_boost * normalized, 1.0)


def _blend_scores(
    candidates: list[tuple[int, float]],
    ce_scores: dict[int, float],
    alpha: float,
    adaptive: bool = True,
    apply_platt: bool = False,
) -> list[tuple[int, float]]:
    """Blend WRRF scores with cross-encoder scores, scaled by confidence.

    Retrieval confidence from raw CE scores gates the final blended score.
    When no result strongly matches (low CE), confidence pulls scores down,
    enabling natural abstention for unanswerable queries.

    source: ADR-0245"""
    raw_ce_list = [ce_scores.get(i, 0.0) for i in range(len(candidates))]
    confidence = _compute_retrieval_confidence(raw_ce_list)

    # Per-query adaptive alpha based on CE score distribution
    effective_alpha = _compute_adaptive_alpha(raw_ce_list, alpha) if adaptive else alpha

    # source: ADR-0245

    platt_params = reranker_calibration.get_params() if apply_platt else None

    reranked = []
    for i, (mem_id, wrrf_score) in enumerate(candidates):
        ce = ce_scores.get(i, 0.0)
        ce_for_blend = platt_calibration.calibrate_score(ce, platt_params)
        blended = (1 - effective_alpha) * wrrf_score + effective_alpha * ce_for_blend
        reranked.append((mem_id, blended * confidence))
    reranked.sort(key=lambda x: x[1], reverse=True)
    return reranked
