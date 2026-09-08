"""Targeted memory reactivation (F2) — cue-directed bias over the replay set.

source: ADR-0281"""

from __future__ import annotations

import re
from typing import Any, Callable

# source: ADR-0281


CUE_BOOST = 1.0

_WORD_RE = re.compile(r"[a-z0-9]+")


# ── Cue matching (lexical, in [0,1]) ─────────────────────────────────────────


def _tokens(text: str) -> set[str]:
    """Lower-cased alphanumeric token set (mirrors attentional_control._tokens)."""
    return set(_WORD_RE.findall((text or "").lower()))


def _memory_text(memory: dict[str, Any]) -> str:
    """Assemble the searchable text a cue is matched against.

    source: ADR-0281"""
    parts: list[str] = [str(memory.get("content", "") or "")]
    for key in ("tags", "entities"):
        val = memory.get(key) or []
        if isinstance(val, (list, tuple, set)):
            parts.extend(str(v) for v in val)
        else:
            parts.append(str(val))
    domain = memory.get("domain")
    if domain:
        parts.append(str(domain))
    return " ".join(parts)


def cue_match_score(cue: str | None, memory: dict[str, Any]) -> float:
    """Lexical match of ``cue`` to a memory's searchable text, in [0,1].

    Jaccard-style cue coverage: the fraction of the cue's tokens that appear in
    the memory (content + tags + domain + entities). Returns 0.0 when the cue
    is empty/None/whitespace (no cue → no boost) or when the memory has no
    matchable text. This is a lexical proxy, not a semantic similarity; a
    caller with a vector score should bypass this and pass a precomputed score
    to ``rerank_replay_set``/``replay_priority``.
    """
    cue_tokens = _tokens(cue or "")
    if not cue_tokens:
        return 0.0
    mem_tokens = _tokens(_memory_text(memory))
    if not mem_tokens:
        return 0.0
    return len(cue_tokens & mem_tokens) / len(cue_tokens)


# ── Replay priority (heat + cue boost) ───────────────────────────────────────


def replay_priority(
    memory: dict[str, Any],
    cue: str | None = None,
    *,
    boost: float = CUE_BOOST,
    cue_score: float | None = None,
) -> float:
    """Priority used to rank a memory for replay: ``heat + boost * cue_score``.

    source: ADR-0281"""
    heat = float(memory.get("heat", 0) or 0)
    if cue_score is None:
        cue_score = cue_match_score(cue, memory)
    return heat + boost * cue_score


# ── Replay-set re-ranking / filtering ────────────────────────────────────────


def rerank_replay_set(
    memories: list[dict[str, Any]],
    cue: str | None = None,
    *,
    max_replay: int | None = None,
    boost: float = CUE_BOOST,
    score_fn: Callable[[str | None, dict[str, Any]], float] | None = None,
) -> list[dict[str, Any]]:
    """Re-rank (and optionally truncate) a candidate replay set by priority.

    source: ADR-0281

    ``score_fn`` overrides the lexical ``cue_match_score`` (e.g. a semantic
    similarity ``(cue, memory) -> float`` in [0,1]); the boost math is
    unchanged.
    """
    scorer = score_fn or cue_match_score
    has_cue = bool((cue or "").strip())

    def priority(mem: dict[str, Any]) -> float:
        if not has_cue:
            return float(mem.get("heat", 0) or 0)
        return replay_priority(mem, cue, boost=boost, cue_score=scorer(cue, mem))

    ranked = sorted(memories, key=priority, reverse=True)
    if max_replay is not None:
        return ranked[:max_replay]
    return ranked
