"""Habituation & sensitization (E1) — response decrement to repeated stimuli.

source: ADR-0187"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

# source: ADR-0187

# source: ADR-0187


HABITUATION_RATE = 0.35

# source: ADR-0187


MIN_RESPONSE_GAIN = 0.15

# source: ADR-0187


SPONTANEOUS_RECOVERY_PER_HOUR = 0.7

# Criteria 8/9: a salient event raises responsiveness transiently. Peak factor
# applied immediately after the event (a 60% amplification at full salience).
SENSITIZATION_PEAK = 1.6

# Sensitization decays linearly back to 1.0 over this window (hours). A salient
# burst amplifies related inputs for a bounded time, not permanently.
SENSITIZATION_DECAY_HOURS = 6.0

# Importance at/above which an event counts as "salient" enough to sensitize.
SALIENCE_THRESHOLD = 0.7

_WS_RE = re.compile(r"\s+")
_NONWORD_RE = re.compile(r"[^\w\s]")


# ── Stimulus signature (criterion 4: specificity) ─────────────────────────────


def stimulus_signature(content: str) -> str:
    """Normalise content to a stimulus-identity key for specificity matching.

    source: ADR-0187"""
    s = _NONWORD_RE.sub(" ", (content or "").lower())
    return _WS_RE.sub(" ", s).strip()


# ── Component gains ───────────────────────────────────────────────────────────


def effective_repeats(repeat_count: int, hours_since_last: float | None) -> float:
    """Repeat count discounted by spontaneous recovery (criterion 2).

    source: ADR-0187"""
    n = max(0, repeat_count)
    if hours_since_last is None or hours_since_last <= 0.0:
        return float(n)
    recovered = SPONTANEOUS_RECOVERY_PER_HOUR * hours_since_last
    return max(0.0, n - recovered)


def response_gain(repeat_count: int, hours_since_last: float | None = None) -> float:
    """Habituation response gain in [MIN_RESPONSE_GAIN, 1.0] (criteria 1 & 2).

    First presentation (effective repeats 0) returns 1.0 — no habituation on a
    stimulus never seen before. Each subsequent near-identical presentation
    decrements the gain exponentially toward the floor. Spontaneous recovery is
    folded in via ``hours_since_last``.
    """
    n = effective_repeats(repeat_count, hours_since_last)
    gain = math.exp(-HABITUATION_RATE * n)
    return max(MIN_RESPONSE_GAIN, min(1.0, gain))


def is_salient(importance: float, threshold: float = SALIENCE_THRESHOLD) -> bool:
    """True iff an event's importance clears the sensitization threshold."""
    return importance >= threshold


def sensitization_factor(
    salience: float,
    hours_since_salient: float | None,
) -> float:
    """Transient responsiveness boost after a salient event (criteria 8/9).

    Returns a factor >= 1.0: peak (scaled by ``salience`` in [0,1]) immediately
    after the event, decaying linearly to 1.0 over SENSITIZATION_DECAY_HOURS.
    With no recorded salient event (``hours_since_salient`` is None) or once the
    window has elapsed, returns the baseline 1.0.
    """
    if hours_since_salient is None or hours_since_salient < 0.0:
        return 1.0
    if hours_since_salient >= SENSITIZATION_DECAY_HOURS:
        return 1.0
    s = max(0.0, min(1.0, salience))
    remaining = 1.0 - (hours_since_salient / SENSITIZATION_DECAY_HOURS)
    peak_boost = (SENSITIZATION_PEAK - 1.0) * s
    return 1.0 + peak_boost * remaining


# ── Combined outcome (write-gate facing) ──────────────────────────────────────


@dataclass
class HabituationOutcome:
    """The result of one habituation/sensitization pass over a novelty score.

    source: ADR-0187"""

    signature: str
    modulated_novelty: float
    response_gain: float
    sensitization: float
    combined_gain: float
    effective_repeats: float
    suppressed: bool


def habituation_outcome_as_dict(outcome: "HabituationOutcome") -> dict:
    """Serialize habituation outcome as a dictionary.

    source: ADR-0187
    """
    return {
        "signature": outcome.signature,
        "modulated_novelty": round(outcome.modulated_novelty, 4),
        "response_gain": round(outcome.response_gain, 4),
        "sensitization": round(outcome.sensitization, 4),
        "combined_gain": round(outcome.combined_gain, 4),
        "effective_repeats": round(outcome.effective_repeats, 4),
        "suppressed": outcome.suppressed,
    }


def habituate_novelty(
    novelty: float,
    content: str,
    repeat_count: int,
    hours_since_last: float | None = None,
    salience: float = 0.0,
    hours_since_salient: float | None = None,
) -> HabituationOutcome:
    """Apply habituation + sensitization to a novelty score.

    ``novelty``              — the gate's combined novelty in [0, 1].
    ``content``              — raw stimulus text (signed via stimulus_signature).
    ``repeat_count``         — prior presentations of this signature (caller-
                               supplied from the store; 0 = first time).
    ``hours_since_last``     — idle time since the last presentation of this
                               signature (drives spontaneous recovery); None if
                               unknown / never seen.
    ``salience``             — importance of the most recent salient event in
                               [0, 1] (0 = none).
    ``hours_since_salient``  — elapsed hours since that salient event; None if
                               there was none.

    source: ADR-0187"""
    sig = stimulus_signature(content)
    rgain = response_gain(repeat_count, hours_since_last)
    sfactor = sensitization_factor(salience, hours_since_salient)
    combined = rgain * sfactor
    modulated = max(0.0, min(1.0, novelty * combined))
    eff = effective_repeats(repeat_count, hours_since_last)
    return HabituationOutcome(
        signature=sig,
        modulated_novelty=modulated,
        response_gain=rgain,
        sensitization=sfactor,
        combined_gain=combined,
        effective_repeats=eff,
        suppressed=combined < 1.0,
    )
