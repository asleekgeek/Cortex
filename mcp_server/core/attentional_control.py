"""Central executive / attentional control (A1) — top-down selection over the
working set.

source: ADR-0106"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

# source: ADR-0106


FOCUS_CAPACITY_DEFAULT = 4

# source: ADR-0106


ATTENTION_TEMPERATURE = 0.5

# How much bottom-up salience (importance, |valence|) adds to top-down relevance.
# 0 = purely goal-driven attention; higher = more stimulus-driven capture.
SALIENCE_WEIGHT = 0.3

_WORD_RE = re.compile(r"[a-z0-9]+")


@dataclass
class AttentionAllocation:
    """The result of one attention-allocation pass.

    source: ADR-0106"""

    focus: list[dict]
    weights: list[float]
    entropy: float
    capacity: int
    overflow: int = 0


def attention_allocation_as_dict(allocation: "AttentionAllocation") -> dict:
    """Serialize attention allocation as a dictionary.

    source: ADR-0106
    """
    return {
        "focus": allocation.focus,
        "weights": [round(w, 4) for w in allocation.weights],
        "entropy": round(allocation.entropy, 4),
        "capacity": allocation.capacity,
        "overflow": allocation.overflow,
    }


# ── Relevance scoring (top-down) ────────────────────────────────────────────
def _tokens(text: str) -> set[str]:
    return set(_WORD_RE.findall((text or "").lower()))


def relevance_score(query: str, content: str) -> float:
    """Lexical top-down relevance of ``content`` to ``query`` in [0,1].

    source: ADR-0106"""
    q = _tokens(query)
    if not q:
        return 0.0
    c = _tokens(content)
    if not c:
        return 0.0
    return len(q & c) / len(q)


# ── The softmax spotlight ───────────────────────────────────────────────────
def _softmax(logits: list[float], temperature: float) -> list[float]:
    """Numerically-stable softmax with temperature.

    source: ADR-0106"""
    if not logits:
        return []
    t = max(temperature, 1e-6)
    scaled = [x / t for x in logits]
    m = max(scaled)
    exps = [math.exp(x - m) for x in scaled]
    total = sum(exps)
    if total <= 0.0:
        n = len(logits)
        return [1.0 / n] * n
    return [e / total for e in exps]


def _entropy(weights: list[float]) -> float:
    """Shannon entropy (nats) of an attention distribution."""
    return -sum(w * math.log(w) for w in weights if w > 0.0)


# ── The allocation pass ─────────────────────────────────────────────────────
def allocate_attention(
    query: str,
    items: list[dict],
    *,
    capacity: int = FOCUS_CAPACITY_DEFAULT,
    temperature: float = ATTENTION_TEMPERATURE,
    salience_weight: float = SALIENCE_WEIGHT,
    precomputed_scores: list[float] | None = None,
) -> AttentionAllocation:
    """Direct the attentional spotlight over ``items`` given the current query.

    source: ADR-0106

    Empty input yields an empty allocation. Fewer items than capacity means all
    are in focus (with their relative weights).
    """
    n = len(items)
    if n == 0:
        return AttentionAllocation(focus=[], weights=[], entropy=0.0, capacity=capacity)

    if precomputed_scores is not None:
        if len(precomputed_scores) != n:
            raise ValueError("precomputed_scores length must match items")
        top_down = list(precomputed_scores)
    else:
        top_down = [relevance_score(query, it.get("content", "")) for it in items]

    # Bottom-up salience: importance + |valence|, scaled. Lets an unbidden but
    # salient item compete for the spotlight (stimulus-driven capture).
    logits: list[float] = []
    # source: ADR-0106

    for score, it in zip(top_down, items, strict=True):
        importance = float(it.get("importance", 0.0) or 0.0)
        valence = abs(float(it.get("valence", 0.0) or 0.0))
        salience = 0.5 * importance + 0.5 * valence
        logits.append(score + salience_weight * salience)

    weights = _softmax(logits, temperature)
    entropy = _entropy(weights)

    order = sorted(range(n), key=lambda i: weights[i], reverse=True)
    focus_idx = order[: max(capacity, 0)]
    focus = []
    for i in focus_idx:
        item = dict(items[i])
        item["attention_weight"] = round(weights[i], 4)
        focus.append(item)

    return AttentionAllocation(
        focus=focus,
        weights=weights,
        entropy=entropy,
        capacity=capacity,
        overflow=max(n - len(focus_idx), 0),
    )


def in_focus_contents(allocation: AttentionAllocation) -> list[str]:
    """Convenience: the ``content`` strings of the in-focus items, best first."""
    return [f.get("content", "") for f in allocation.focus]
