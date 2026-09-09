"""Cerebellar forward model (B3) — one-step-ahead prediction with error-driven
correction of the estimate.

source: ADR-0180"""

from __future__ import annotations

from dataclasses import dataclass

# source: ADR-0180


CORRECTION_GAIN = 0.5

# source: ADR-0180


ERROR_DEADBAND = 0.05


@dataclass
class ForwardModelState:
    """State of a running scalar forward model.

    ``estimate``   — the current one-step-ahead prediction (updated by
                     corrections; this is what ``predict`` returns).
    ``error``      — the last signed residual (observed - predicted).
    ``corrected``  — the estimate *after* folding in the last correction.
    ``n_updates``  — how many observations have corrected the model.
    """

    estimate: float
    error: float = 0.0
    corrected: float = 0.0
    n_updates: int = 0


def forward_model_state_as_dict(state: "ForwardModelState") -> dict:
    """Serialize forward model state as a dictionary.

    source: ADR-0180
    """
    return {
        "estimate": round(state.estimate, 6),
        "error": round(state.error, 6),
        "corrected": round(state.corrected, 6),
        "n_updates": state.n_updates,
    }


# ── The two primitive operations ────────────────────────────────────────────
def predict(state: ForwardModelState) -> float:
    """One-step-ahead prediction: the forward model's current estimate.

    source: ADR-0180"""
    return state.estimate


def correction(
    predicted: float,
    actual: float,
    *,
    gain: float = CORRECTION_GAIN,
    deadband: float = ERROR_DEADBAND,
) -> tuple[float, float]:
    """Correct a prediction from the observed value; return (error, corrected).

    source: ADR-0180"""
    error = actual - predicted
    if abs(error) <= deadband:
        return error, predicted
    g = max(0.0, min(1.0, gain))
    return error, predicted + g * error


# ── Running the model over a trajectory ─────────────────────────────────────
def run_forward_model(
    trajectory: list[float],
    *,
    gain: float = CORRECTION_GAIN,
    deadband: float = ERROR_DEADBAND,
) -> ForwardModelState:
    """Replay predict→observe→correct across a scalar ``trajectory``.

    The estimate is seeded with the first observation (no error can be scored
    before the model has seen anything), then each subsequent value is predicted
    one step ahead and used to correct the estimate. The returned state's
    ``error`` is the residual for the *last* observation given the model built
    from all earlier ones — i.e. how surprising the most recent step was.

    An empty trajectory yields a zeroed state; a single point yields the seeded
    estimate with zero error (nothing to predict yet).
    """
    if not trajectory:
        return ForwardModelState(estimate=0.0)

    state = ForwardModelState(
        estimate=float(trajectory[0]), corrected=float(trajectory[0])
    )
    for actual in trajectory[1:]:
        pred = predict(state)
        error, corrected = correction(pred, float(actual), gain=gain, deadband=deadband)
        state.estimate = corrected
        state.error = error
        state.corrected = corrected
        state.n_updates += 1
    return state


def prediction_error(
    trajectory: list[float],
    actual: float,
    *,
    gain: float = CORRECTION_GAIN,
    deadband: float = ERROR_DEADBAND,
) -> float:
    """Signed one-step forward-model error of ``actual`` given ``trajectory``.

    source: ADR-0180"""
    if not trajectory:
        return 0.0
    state = run_forward_model(trajectory, gain=gain, deadband=deadband)
    error, _ = correction(predict(state), float(actual), gain=gain, deadband=deadband)
    return error


# ── Vector convenience (reduces a feature dict to the tracked scalar) ────────
def scalar_of(features: dict[str, float]) -> float:
    """Reduce a feature vector to the single scalar the model tracks.

    The forward model is one-dimensional (see the honesty note); a caller
    holding a feature dict (e.g. the sensory feature vector from
    ``predictive_coding_signals.extract_sensory_features``) collapses it to its
    mean activation here before feeding the model. Empty vector → 0.0.
    """
    if not features:
        return 0.0
    vals = list(features.values())
    return sum(vals) / len(vals)
