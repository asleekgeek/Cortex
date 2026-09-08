"""Consolidation cascade — stage advancement and reconsolidation logic.

source: ADR-0117"""

from __future__ import annotations

from mcp_server.core.cascade_stages import (
    _STAGE_PROPERTIES,
    ConsolidationStage,
)
from mcp_server.core.ablation import Mechanism, is_mechanism_disabled

# ── Stage Transitions ─────────────────────────────────────────────────────

# source: ADR-0117

# source: ADR-0117
_LABILE_IMPORTANCE_THRESHOLD = 0.3  # "importance > 0.3 (moderately important)"
_EARLY_LTP_IMPORTANCE_BOOST = 0.4  # "importance > 0.4 (strong encoding)"
_SCHEMA_FAST_CONSOLIDATION_MATCH = 0.5  # "1 with schema > 0.5"


def _check_labile_advancement(
    dopamine_level: float,
    importance: float,
    hours_in_stage: float = 0.0,
) -> tuple[bool, str, float]:
    """Check LABILE -> EARLY_LTP advancement conditions.

    source: ADR-0117

    Advances if:
      - dopamine_level >= 1.0 (encoding signal present), OR
      - importance > 0.3 (moderately important)
    """
    da_ready = dopamine_level >= 1.0
    importance_ready = importance > _LABILE_IMPORTANCE_THRESHOLD
    readiness = min(1.0, (dopamine_level - 0.5) / 1.5 + importance * 0.5)
    if da_ready or importance_ready:
        return True, ConsolidationStage.EARLY_LTP.value, readiness
    return False, ConsolidationStage.LABILE.value, readiness


def _check_early_ltp_advancement(
    replay_count: int,
    importance: float,
    hours_in_stage: float = 0.0,
) -> tuple[bool, str, float]:
    """Check EARLY_LTP -> LATE_LTP advancement conditions.

    source: ADR-0117

    Advances if:
      - replay_count >= 1 (memory has been replayed/accessed), OR
      - importance > 0.4 (strong encoding)
    """
    replay_ready = replay_count >= 1
    importance_boost = importance > _EARLY_LTP_IMPORTANCE_BOOST
    readiness = min(1.0, replay_count / 2.0 + importance * 0.5)
    if replay_ready or importance_boost:
        return True, ConsolidationStage.LATE_LTP.value, readiness
    return False, ConsolidationStage.EARLY_LTP.value, readiness


def _check_late_ltp_advancement(
    replay_count: int,
    schema_match: float,
    hours_in_stage: float = 0.0,
) -> tuple[bool, str, float]:
    """Check LATE_LTP -> CONSOLIDATED advancement conditions.

    source: ADR-0117

    Advances if:
      - replay_count >= replay_threshold (3 normally, 1 with schema > 0.5)
    """
    replay_threshold = 3 if schema_match < _SCHEMA_FAST_CONSOLIDATION_MATCH else 1
    replay_ready = replay_count >= replay_threshold
    readiness = min(1.0, replay_count / max(replay_threshold, 1))
    if replay_ready:
        return True, ConsolidationStage.CONSOLIDATED.value, readiness
    return False, ConsolidationStage.LATE_LTP.value, readiness


def _check_reconsolidating_advancement(
    hours_in_stage: float,
    effective_min_dwell: float,
) -> tuple[bool, str, float]:
    """Check RECONSOLIDATING -> EARLY_LTP re-stabilization."""
    if hours_in_stage >= effective_min_dwell:
        return True, ConsolidationStage.EARLY_LTP.value, 1.0
    readiness = hours_in_stage / max(effective_min_dwell, 0.01)
    return False, ConsolidationStage.RECONSOLIDATING.value, readiness


def _effective_min_dwell(
    props: object,
    schema_match: float,
    stage: ConsolidationStage | None = None,
) -> float:
    """Compute schema-accelerated minimum dwell time.

    source: ADR-0117

    For earlier stages (LABILE, EARLY_LTP, RECONSOLIDATING):
        Modest linear factor: dwell * (1 - schema_match * 0.2).
        Schema acceleration is a systems consolidation phenomenon;
        synaptic tagging stages are not schema-dependent.
    """
    if stage in (ConsolidationStage.LATE_LTP, ConsolidationStage.CONSOLIDATED):
        # source: ADR-0117

        schema_factor = 15.0 ** (-schema_match)  # source: ADR-0117
    else:
        # source: ADR-0117

        schema_factor = 1.0 - (schema_match * 0.2)  # source: ADR-0117
    return props.min_dwell_hours * schema_factor  # type: ignore[attr-defined]


def compute_advancement_readiness(
    current_stage: str,
    hours_in_stage: float,
    dopamine_level: float = 1.0,
    replay_count: int = 0,
    schema_match: float = 0.0,
    importance: float = 0.5,
) -> tuple[bool, str, float]:
    """Determine if a memory is ready to advance to the next stage.

    Returns (is_ready, next_stage_name, readiness_score_0_to_1).
    """

    if is_mechanism_disabled(Mechanism.CASCADE):
        # No-op: never advance the consolidation stage; memories remain LABILE.
        return False, current_stage, 0.0

    try:
        stage = ConsolidationStage(current_stage)
    except ValueError:
        return False, current_stage, 0.0

    props = _STAGE_PROPERTIES[stage]
    min_dwell = _effective_min_dwell(props, schema_match, stage)

    if hours_in_stage < min_dwell:
        readiness = hours_in_stage / max(min_dwell, 0.01)
        return False, current_stage, min(readiness, 0.99)

    if stage == ConsolidationStage.LABILE:
        return _check_labile_advancement(dopamine_level, importance, hours_in_stage)
    if stage == ConsolidationStage.EARLY_LTP:
        return _check_early_ltp_advancement(replay_count, importance, hours_in_stage)
    if stage == ConsolidationStage.LATE_LTP:
        return _check_late_ltp_advancement(replay_count, schema_match, hours_in_stage)
    if stage == ConsolidationStage.RECONSOLIDATING:
        return _check_reconsolidating_advancement(hours_in_stage, min_dwell)
    return False, current_stage, 1.0


def trigger_reconsolidation(
    current_stage: str,
    mismatch_score: float,
    stability: float = 0.5,
    *,
    mismatch_threshold: float = 0.3,
) -> tuple[bool, str]:
    """Determine if retrieval should trigger reconsolidation.

    Only CONSOLIDATED and LATE_LTP memories can reconsolidate.
    Requires sufficient mismatch between retrieval context and stored context.
    Higher stability means higher mismatch threshold needed.

    Args:
        current_stage: Current consolidation stage.
        mismatch_score: Context mismatch score [0, 1].
        stability: Memory stability [0, 1]. High stability resists reconsolidation.
        mismatch_threshold: Base threshold for triggering reconsolidation.

    Returns:
        (should_reconsolidate, new_stage_name)
    """
    try:
        stage = ConsolidationStage(current_stage)
    except ValueError:
        return False, current_stage

    if stage not in (ConsolidationStage.CONSOLIDATED, ConsolidationStage.LATE_LTP):
        return False, current_stage

    effective_threshold = mismatch_threshold + stability * 0.3

    if mismatch_score >= effective_threshold:
        return True, ConsolidationStage.RECONSOLIDATING.value

    return False, current_stage
