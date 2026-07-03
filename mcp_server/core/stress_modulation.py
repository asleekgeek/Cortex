"""Stress-hormone (glucocorticoid) modulation (D1) — a session-stress signal
scaling offline consolidation strength along an inverted-U.

Stress hormones (glucocorticoids and adrenal catecholamines) do not switch
memory consolidation on or off; they *modulate* it, and the modulation is
biphasic. Moderate post-learning arousal ENHANCES the consolidation of the
event, while extreme stress IMPAIRS it — the same inverted-U that the arousal /
emotional-tagging path (``emotional_tagging.py``) already applies to per-memory
importance, now applied to the *offline consolidation* pass as a whole. Cortex
has the arousal machinery (``emotional_tagging.compute_arousal`` /
``arousal_inverted_u_bump``) but no *session-level* stress signal feeding the
consolidation strength: a session full of errors, failures, and deadline
pressure consolidates exactly like a calm one. D1 derives a scalar session
stress from those signals and scales the consolidation gain by it.

Neuroscience basis (DOIs verified against Crossref in-session):
  - Roozendaal & McGaugh (2011), "Memory modulation," Behavioral Neuroscience
    125:797-824 (doi:10.1037/a0026187). Adrenal stress hormones modulate the
    consolidation of emotionally arousing experiences via the basolateral
    amygdala; the effect on memory strength is an inverted-U — moderate levels
    enhance, high levels impair — which this module operationalises as a
    stress-scaled consolidation gain.
  - McGaugh (2000), "Memory--a century of consolidation," Science 287:248-251
    (doi:10.1126/science.287.5451.248). Consolidation is a time-dependent,
    modulable process: post-event neuromodulatory/hormonal state adjusts how
    strongly a memory is fixed — the licence for a scalar post-session gain on
    the consolidation path rather than a change to encoding.
  - Hebb (1955), "Drives and the C.N.S. (conceptual nervous system),"
    Psychological Review 62:243-254 (doi:10.1037/h0041823). The arousal
    inverted-U ("Hebb's curve") this module reuses for the enhancement lobe.
    NOTE: the inverted-U on arousal is Hebb's, NOT Yerkes & Dodson (1908) —
    that 1908 study measured stimulus intensity vs. task difficulty and never
    plotted performance against arousal. Do not miscite it here.

Design (pure business logic — no I/O; all inputs supplied by the caller):
  - ``compute_session_stress`` — combine a per-session error rate, urgency /
    deadline lexical density, and failure-marker density into one scalar in
    [0, 1]. 0 = a calm session (no errors, no urgency, no failures); 1 = a
    maximally fraught one. Weights are fixed engineering constants.
  - ``detect_stress_markers`` — count urgency/deadline and failure lexical hits
    in session text, REUSING the exact lexicon ``emotional_tagging.py`` already
    defines (``_URGENCY_DOMAIN_RE`` for urgency/deadline, ``_ERROR_DOMAIN_RE``
    for failures) so D1's "urgency/deadline language" and "failure density" are
    the same words the emotional path keys on — not a second, drifting lexicon.
  - ``consolidation_gain`` — map the stress scalar through the inverted-U to a
    multiplier on consolidation strength. REUSES the exact Hebb bump factored
    out of ``emotional_tagging`` (``arousal_inverted_u_bump``) for the
    enhancement lobe; adds a quadratic OVERLOAD penalty above an onset so that
    EXTREME stress drives the gain BELOW 1.0 (impairment) — the falling arm of
    the inverted-U that a bump-above-1.0 alone cannot express.
  - ``assess_session_stress`` — the full pipeline: text + error rate in, the
    stress scalar, the consolidation gain, and the component breakdown out.

Ablation guard. When ``CORTEX_ABLATE_STRESS_MODULATION=1``
(Mechanism.STRESS_MODULATION), ``consolidation_gain`` returns 1.0 for every
stress level — the consolidation pass runs at its unmodulated strength, exactly
as before D1. The default is also behavior-preserving at the boundary: a neutral
session (stress = 0) yields gain 1.0 whether or not the mechanism is enabled, so
D1 only changes behaviour when there IS session stress to modulate by.

Honesty note (zetetic standard, matching attentional_control.py /
source_monitoring.py / extinction.py). THIS IS A DESIGN INFERENCE — an
engineering heuristic, NOT a validated glucocorticoid model, and it is labelled
so deliberately. What is grounded: the *direction* Roozendaal & McGaugh (2011)
and McGaugh (2000) establish — that a post-event stress/arousal state modulates
consolidation strength biphasically (moderate enhances, extreme impairs). What
is invented: (1) the "session stress" scalar is a proxy assembled from a lexical
urgency/failure count and a caller-supplied error rate — it is NOT a measured
cortisol/adrenaline level and there is no claim that these text signals track
circulating glucocorticoids; (2) the gain curve is a deterministic function with
fixed constants (peak location/height, overload onset/penalty), fit to give a
sensible inverted-U over [0, 1], NOT parameters estimated from any dose-response
data; (3) the mapping from "session stress" to "consolidation gain" is a
one-parameter engineering modulation of the write/consolidation path, not a
model of the basolateral-amygdala circuit those papers describe. The inverted-U
SHAPE is Hebb (1955); the specific parameterization is modern and this module's
own. No source supplies rate laws at this store's timescale. A neutral session
changes nothing (gain 1.0) — the modulation is opt-in on the presence of stress.
"""

from __future__ import annotations

from typing import Any

from mcp_server.core.ablation import Mechanism, is_mechanism_disabled
from mcp_server.core.emotional_tagging import (
    _ERROR_DOMAIN_RE,
    _URGENCY_DOMAIN_RE,
    arousal_inverted_u_bump,
)

# ── Session-stress scalar weights (fixed engineering constants) ───────────────
# The three signals that compose session stress and how much each contributes.
# They sum to 1.0, so with every signal at its max the scalar reaches exactly
# 1.0. Error rate is weighted highest — a session that keeps erroring is the
# clearest stress signal; urgency/deadline language and failure-marker density
# are secondary lexical proxies.
STRESS_W_ERROR = 0.5  # weight on the caller-supplied error rate
STRESS_W_URGENCY = 0.25  # weight on urgency/deadline lexical density
STRESS_W_FAILURE = 0.25  # weight on failure-marker lexical density

# Lexical densities are counts normalized by this cap (hits >= cap => full 1.0
# on that channel). Matches the cap emotional_tagging.detect_emotions uses (3).
STRESS_MARKER_CAP = 3

# ── Consolidation-gain inverted-U constants (fixed engineering values) ────────
# Enhancement lobe: the Hebb bump (reused from emotional_tagging) peaks at this
# stress level, adding this much to the base gain of 1.0. Peak at 0.5 (moderate
# stress optimal) adding +0.35 => peak gain 1.35.
STRESS_ENHANCE_PEAK = 0.5
STRESS_ENHANCE_HEIGHT = 0.35

# Overload (impairment) lobe: above this stress onset a quadratic penalty grows,
# pulling the gain below 1.0 at extreme stress. At stress 1.0 the penalty equals
# STRESS_OVERLOAD_PENALTY, giving gain ≈ 0.71 (impaired consolidation).
STRESS_OVERLOAD_ONSET = 0.6
STRESS_OVERLOAD_PENALTY = 0.55

# Absolute floor on the gain so consolidation is never fully suppressed even at
# maximal stress (impairment, not shutdown).
STRESS_GAIN_FLOOR = 0.5


def detect_stress_markers(text: str) -> dict[str, int]:
    """Count urgency/deadline and failure lexical markers in session text.

    Reuses the exact compiled lexicons ``emotional_tagging`` defines:
    ``_URGENCY_DOMAIN_RE`` (urgent/critical/blocking/deadline/asap/…) for the
    urgency/deadline channel and ``_ERROR_DOMAIN_RE`` (error/exception/failed/
    failure/bug/crash/…) for the failure channel. Counts are capped at
    ``STRESS_MARKER_CAP`` so a single fraught sentence cannot dominate.

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

    ``error_rate`` is a caller-supplied fraction in [0, 1] (e.g. failed actions
    / total actions this session); it is clamped. ``urgency_hits`` and
    ``failure_hits`` are lexical marker counts (see ``detect_stress_markers``),
    normalized by ``marker_cap`` into [0, 1] channels. The three channels are
    combined with the fixed weights ``STRESS_W_ERROR`` / ``STRESS_W_URGENCY`` /
    ``STRESS_W_FAILURE`` (which sum to 1.0) and the result is clamped to [0, 1].

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
    inverted-U (gain < 1.0) — extreme stress that weakens rather than
    strengthens consolidation.

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
