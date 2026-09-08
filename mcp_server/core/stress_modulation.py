"""Stress-hormone (glucocorticoid) modulation (D1) — a session-stress signal
scaling offline consolidation strength along an inverted-U.

source: ADR-0272"""

from __future__ import annotations

from typing import Any

from mcp_server.core.ablation import Mechanism, is_mechanism_disabled
from mcp_server.core.emotional_tagging import (
    _ERROR_DOMAIN_RE,
    _URGENCY_DOMAIN_RE,
    arousal_inverted_u_bump,
)

# source: ADR-0272


STRESS_W_ERROR = 0.5  # weight on the caller-supplied error rate
STRESS_W_URGENCY = 0.25  # weight on urgency/deadline lexical density
STRESS_W_FAILURE = 0.25  # weight on failure-marker lexical density

# Lexical densities are counts normalized by this cap (hits >= cap => full 1.0
# on that channel). Matches the cap emotional_tagging.detect_emotions uses (3).
STRESS_MARKER_CAP = 3

# source: ADR-0272


STRESS_ENHANCE_PEAK = 0.5
STRESS_ENHANCE_HEIGHT = 0.35

# Overload (impairment) lobe: above this stress onset a quadratic penalty grows,
# pulling the gain below 1.0 at extreme stress. At stress 1.0 the penalty equals
# STRESS_OVERLOAD_PENALTY, giving gain ≈ 0.71 (impaired consolidation).
STRESS_OVERLOAD_ONSET = 0.6
STRESS_OVERLOAD_PENALTY = 0.55

# source: ADR-0272

STRESS_GAIN_FLOOR = 0.5


def detect_stress_markers(text: str) -> dict[str, int]:
    """Count urgency/deadline and failure lexical markers in session text.

    source: ADR-0272

    Returns ``{"urgency": <int>, "failure": <int>}`` — raw capped hit counts
    (not yet normalized). Empty/blank text yields zeros.
    """
    if not text:
        return {"urgency": 0, "failure": 0}
    urgency = min(len(_URGENCY_DOMAIN_RE.findall(text)), STRESS_MARKER_CAP)
    failure = min(len(_ERROR_DOMAIN_RE.findall(text)), STRESS_MARKER_CAP)
    return {"urgency": urgency, "failure": failure}


def compute_session_stress(
    error_rate: float = 0.0,
    urgency_hits: int = 0,
    failure_hits: int = 0,
    *,
    marker_cap: int = STRESS_MARKER_CAP,
) -> float:
    """Combine error rate + urgency/deadline density + failure density into a
    single session-stress scalar in [0, 1].

    source: ADR-0272

    Preconditions: ``error_rate`` any float (clamped to [0, 1]); ``*_hits >= 0``;
    ``marker_cap > 0``.
    Postconditions: returns a value in [0, 1]; all-zero inputs return exactly
    0.0 (a calm session — the neutral case that leaves consolidation unchanged).
    """
    e = max(0.0, min(1.0, error_rate))
    cap = max(1, marker_cap)
    u = max(0.0, min(1.0, urgency_hits / cap))
    f = max(0.0, min(1.0, failure_hits / cap))
    stress = STRESS_W_ERROR * e + STRESS_W_URGENCY * u + STRESS_W_FAILURE * f
    return round(max(0.0, min(1.0, stress)), 4)


def consolidation_gain(stress: float) -> float:
    """Map a session-stress scalar to a consolidation-strength multiplier along
    the inverted-U (moderate stress enhances, extreme stress impairs).

    ``gain(s) = 1.0 + enhance(s) - overload(s)`` where:
      - ``enhance(s)`` is the Hebb bump reused verbatim from
        ``emotional_tagging.arousal_inverted_u_bump`` (peak ``STRESS_ENHANCE_PEAK``,
        height ``STRESS_ENHANCE_HEIGHT``) — the enhancement lobe;
      - ``overload(s)`` is a quadratic penalty that is 0 below
        ``STRESS_OVERLOAD_ONSET`` and grows to ``STRESS_OVERLOAD_PENALTY`` at
        stress 1.0 — the impairment lobe that drives the gain below 1.0 at
        extreme stress (a bump-above-1.0 alone can only enhance).
    The result is floored at ``STRESS_GAIN_FLOOR`` (impairment, not shutdown).

    Ablation. When ``CORTEX_ABLATE_STRESS_MODULATION=1`` this returns 1.0 for
    every ``stress`` — the unmodulated consolidation strength. Independently of
    ablation, ``stress = 0`` returns exactly 1.0 (the neutral, behavior-
    preserving case): D1 only changes consolidation when there is stress.

    Preconditions: ``stress`` any float (clamped to [0, 1]).
    Postconditions: returns a value in [STRESS_GAIN_FLOOR, ~1.35]; ``stress==0``
    returns 1.0; moderate stress returns > 1.0; extreme stress returns < 1.0.
    """
    if is_mechanism_disabled(Mechanism.STRESS_MODULATION):
        # No-op: consolidation runs at its unmodulated strength.
        return 1.0

    s = max(0.0, min(1.0, stress))
    if s == 0.0:
        return 1.0

    enhance = arousal_inverted_u_bump(
        s, peak=STRESS_ENHANCE_PEAK, peak_height=STRESS_ENHANCE_HEIGHT
    )
    over_frac = max(0.0, s - STRESS_OVERLOAD_ONSET) / (1.0 - STRESS_OVERLOAD_ONSET)
    overload = STRESS_OVERLOAD_PENALTY * over_frac * over_frac
    gain = 1.0 + enhance - overload
    return round(max(STRESS_GAIN_FLOOR, gain), 4)


def is_impairing(stress: float) -> bool:
    """True iff this stress level puts consolidation on the IMPAIRING arm of the
    inverted-U (gain < 1.0) — extreme stress that weakens rather than strengthens
    consolidation.

    source: ADR-0272

        Returns False whenever the mechanism is ablated (gain is a flat 1.0) or the
        stress is neutral/moderate (gain >= 1.0).
    """
    return consolidation_gain(stress) < 1.0


def assess_session_stress(
    text: str = "",
    error_rate: float = 0.0,
) -> dict[str, Any]:
    """Full D1 pipeline: session text + error rate → stress, gain, components.

    Detects urgency/deadline and failure markers in ``text`` (reusing the
    emotional-tagging lexicons), combines them with ``error_rate`` into the
    session-stress scalar, and maps that to the consolidation gain. Returns
    everything a caller / cortex-viz needs:

      {
        "stress": <float 0..1>,            # the session-stress scalar
        "consolidation_gain": <float>,     # inverted-U multiplier
        "is_impairing": <bool>,            # on the falling (gain<1) arm?
        "markers": {"urgency": int, "failure": int},
        "error_rate": <float 0..1>,        # clamped input, for transparency
      }

    A calm session (no markers, error_rate 0) returns stress 0.0 and gain 1.0 —
    no change to consolidation.
    """
    markers = detect_stress_markers(text)
    stress = compute_session_stress(
        error_rate=error_rate,
        urgency_hits=markers["urgency"],
        failure_hits=markers["failure"],
    )
    gain = consolidation_gain(stress)
    return {
        "stress": stress,
        "consolidation_gain": gain,
        "is_impairing": gain < 1.0,
        "markers": markers,
        "error_rate": round(max(0.0, min(1.0, error_rate)), 4),
    }
