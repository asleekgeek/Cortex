"""Recollection vs. familiarity — dual-process retrieval (C2).

source: ADR-0168"""

from __future__ import annotations

from dataclasses import dataclass

# source: ADR-0168


FAMILIARITY_THRESHOLD: float = 0.92

# source: ADR-0168


FAMILIARITY_MARGIN: float = 0.10

# Method tags for the FamiliaritySignal.method field.
METHOD_VECTOR = "vector"  # faithful: max cosine over real embeddings
METHOD_SCORE_PROXY = "score_proxy"  # fallback: fused WRRF score, never skips
METHOD_EMPTY = "empty"  # no candidates / no similarities
METHOD_DISABLED = "disabled"  # ablation guard fired upstream

# source: ADR-0168

_MIN_CANDIDATES_FOR_MARGIN = 2


@dataclass
class FamiliaritySignal:
    """The a-contextual familiarity read over a candidate set.

    source: ADR-0168"""

    familiarity: float
    mean: float
    margin: float
    n: int
    method: str = METHOD_VECTOR


def familiarity_signal_as_dict(signal: "FamiliaritySignal") -> dict:
    """Serialize familiarity signal as a dictionary.

    source: ADR-0168
    """
    return {
        "familiarity": round(signal.familiarity, 6),
        "mean": round(signal.mean, 6),
        "margin": round(signal.margin, 6),
        "n": signal.n,
        "method": signal.method,
    }


@dataclass
class TriageResult:
    """The outcome of an early familiarity triage over a candidate set.

    source: ADR-0168"""

    candidates: list[dict]
    signal: FamiliaritySignal
    recollection_needed: bool
    shortcut: bool = False


# ── (a) the gate ────────────────────────────────────────────────────────────
def familiarity_score(similarities: list[float]) -> float:
    """The a-contextual familiarity gate: MAX similarity over the set.

    source: ADR-0168"""
    if not similarities:
        return 0.0
    return max(float(s) for s in similarities)


# ── (b) the full signal ───────────────────────────────────────────────────────
def assess_familiarity(
    similarities: list[float],
    *,
    method: str = METHOD_VECTOR,
) -> FamiliaritySignal:
    """Compute the familiarity gate plus its supporting scalars.

    ``similarities`` is a per-candidate similarity list (cosine in [-1, 1] for
    the vector method). Empty input yields a zeroed signal tagged
    ``METHOD_EMPTY``.
    """
    sims = [float(s) for s in similarities]
    n = len(sims)
    if n == 0:
        return FamiliaritySignal(0.0, 0.0, 0.0, 0, METHOD_EMPTY)
    ordered = sorted(sims, reverse=True)
    top = ordered[0]
    mean = sum(sims) / n
    # source: ADR-0168
    margin = ordered[0] - ordered[1] if n >= _MIN_CANDIDATES_FOR_MARGIN else ordered[0]
    return FamiliaritySignal(top, mean, margin, n, method)


# source: ADR-0168
def recollection_needed(
    signal: FamiliaritySignal,
    *,
    threshold: float = FAMILIARITY_THRESHOLD,
    margin: float = FAMILIARITY_MARGIN,
) -> bool:
    """True iff the query needs slow contextual recollection.

    source: ADR-0168"""
    if signal.n == 0:
        return True
    if signal.method != METHOD_VECTOR:
        # A proxy signal (e.g. fused WRRF score) is not an a-contextual vector
        # similarity; we do not trust it to license skipping recollection.
        return True
    dominant = signal.n < _MIN_CANDIDATES_FOR_MARGIN or signal.margin >= margin
    sufficient = signal.familiarity >= threshold and dominant
    return not sufficient


def triage(
    candidates: list[dict],
    similarities: list[float],
    *,
    allow_shortcut: bool = False,
    threshold: float = FAMILIARITY_THRESHOLD,
    margin: float = FAMILIARITY_MARGIN,
    method: str = METHOD_VECTOR,
) -> TriageResult:
    """Early familiarity triage over a candidate set (C2).

    source: ADR-0168

    Pure: fetches nothing. The caller supplies the similarities (see
    ``recall_pipeline.familiarity_triage`` for the bulk-embedding read that
    produces them).
    """
    signal = assess_familiarity(similarities, method=method)
    aligned = len(similarities) == len(candidates)
    annotated: list[dict] = []
    for i, c in enumerate(candidates):
        c_out = dict(c)
        if aligned:
            c_out["familiarity"] = round(float(similarities[i]), 6)
        annotated.append(c_out)
    rec = recollection_needed(signal, threshold=threshold, margin=margin)
    shortcut = bool(allow_shortcut and not rec and signal.method == METHOD_VECTOR)
    return TriageResult(
        candidates=annotated,
        signal=signal,
        recollection_needed=rec,
        shortcut=shortcut,
    )
