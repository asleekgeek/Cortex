"""Write-gate threshold auto-calibration.

source: ADR-0320
"""

from __future__ import annotations

from dataclasses import dataclass

# source: ADR-0320

TARGET_ACCEPTANCE_RATE: float = 0.5  # Shannon binary-entropy max (H(p) peaks at p=0.5).
EMA_DECAY: float = 0.95  # ~20-sample effective memory window.
ADJUSTMENT_STEP: float = 0.02  # Bounded per-update threshold delta.
TOLERANCE_BAND: float = 0.15  # |observed - target| below this -> no adjustment.
MIN_THRESHOLD: float = 0.05  # Floor — below this, almost everything stores.
MAX_THRESHOLD: float = 0.95  # Ceiling — above this, almost nothing stores.
MIN_SAMPLES_BEFORE_ADJUST: int = 20  # source: ADR-0320


@dataclass
class CalibrationState:
    """Per-domain write-gate calibration state.

    source: ADR-0320

    Invariants:
      - 0.0 <= acceptance_ema <= 1.0
      - MIN_THRESHOLD <= threshold <= MAX_THRESHOLD
      - total_observations >= 0
    """

    domain: str = ""
    threshold: float = 0.4  # source: ADR-0320
    acceptance_ema: float = 0.5  # Seed at target; diverges with data.
    total_observations: int = 0
    last_adjustment_at: int = 0  # Observation count when threshold last moved.


# ── EMA update ────────────────────────────────────────────────────────────


def update_acceptance_ema(
    current_ema: float,
    accepted: bool,
    decay: float = EMA_DECAY,
) -> float:
    """Update the accept-rate EMA after one gate decision.

    source: ADR-0320

    Contract:
      pre:  0.0 <= current_ema <= 1.0; 0 < decay < 1.
      post: returned value in [0, 1]; EMA moves toward 1.0 if accepted
            else toward 0.0 at rate (1 - decay).

    The update rule is the standard one-sided exponential moving average:
        EMA' = decay * EMA + (1 - decay) * observation
    with observation = 1 if accepted else 0.
    """
    observation = 1.0 if accepted else 0.0
    new_ema = decay * current_ema + (1.0 - decay) * observation
    # Clamp — floating-point drift, not a real invariant violation.
    return max(0.0, min(1.0, new_ema))


# ── Threshold adjustment ──────────────────────────────────────────────────


def compute_threshold_adjustment(
    current_threshold: float,
    acceptance_ema: float,
    *,
    target: float = TARGET_ACCEPTANCE_RATE,
    step: float = ADJUSTMENT_STEP,
    tolerance: float = TOLERANCE_BAND,
    min_threshold: float = MIN_THRESHOLD,
    max_threshold: float = MAX_THRESHOLD,
) -> float:
    """Return the new threshold given the current EMA.

    Contract:
      pre:  0 <= acceptance_ema <= 1; min <= current_threshold <= max.
      post: returned threshold is in [min, max].
            If |acceptance_ema - target| <= tolerance, threshold unchanged.
            If acceptance_ema > target + tolerance (too permissive), raise
                threshold by `step` (clamped to max).
            If acceptance_ema < target - tolerance (too tight), lower
                threshold by `step` (clamped to min).

    source: ADR-0320"""
    delta = acceptance_ema - target
    if abs(delta) <= tolerance:
        return current_threshold
    direction = step if delta > 0 else -step
    new_threshold = current_threshold + direction
    return max(min_threshold, min(max_threshold, new_threshold))


# ── State lifecycle ────────────────────────────────────────────────────────


def observe_gate_decision(
    state: CalibrationState,
    accepted: bool,
    *,
    min_samples: int = MIN_SAMPLES_BEFORE_ADJUST,
) -> CalibrationState:
    """Record one gate decision and (possibly) adjust the threshold.

    source: ADR-0320
    """
    new_ema = update_acceptance_ema(state.acceptance_ema, accepted)
    new_total = state.total_observations + 1

    if new_total < min_samples:
        return CalibrationState(
            domain=state.domain,
            threshold=state.threshold,
            acceptance_ema=new_ema,
            total_observations=new_total,
            last_adjustment_at=state.last_adjustment_at,
        )

    new_threshold = compute_threshold_adjustment(state.threshold, new_ema)
    new_last_adj = (
        new_total if new_threshold != state.threshold else state.last_adjustment_at
    )
    return CalibrationState(
        domain=state.domain,
        threshold=new_threshold,
        acceptance_ema=new_ema,
        total_observations=new_total,
        last_adjustment_at=new_last_adj,
    )


# ── Registry (per-process, per-domain) ─────────────────────────────────────

_STATES: dict[str, CalibrationState] = {}


def get_state(domain: str, default_threshold: float = 0.4) -> CalibrationState:
    """Fetch or lazily-initialise the calibration state for a domain.

    source: ADR-0320
    """
    key = domain or ""
    if key not in _STATES:
        _STATES[key] = CalibrationState(
            domain=key,
            threshold=default_threshold,
        )
    return _STATES[key]


def record(
    domain: str,
    accepted: bool,
    *,
    default_threshold: float = 0.4,
) -> CalibrationState:
    """Convenience: observe a decision and store the updated state.

    source: ADR-0320
    """
    state = get_state(domain, default_threshold=default_threshold)
    new_state = observe_gate_decision(state, accepted)
    _STATES[domain or ""] = new_state
    return new_state


def reset_all_states() -> None:
    """Test hook: clear the in-process calibration registry.

    source: ADR-0320
    """
    _STATES.clear()


def effective_threshold(
    domain: str,
    default_threshold: float = 0.4,
) -> float:
    """Return the calibration-adjusted threshold for a domain.

    source: ADR-0320
    """
    state = _STATES.get(domain or "")
    if state is None:
        return default_threshold
    return state.threshold
