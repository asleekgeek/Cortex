"""Targeted memory reactivation (F2) — cue-directed bias over the replay set.

Cortex's offline consolidation pass (``sleep_compute`` / the F1 NREM phase in
``sleep_phases.run_nrem_phase``) selects *which* memories get replayed by a
single criterion: heat. A bounded min-heap keeps the ``max_replay`` hottest
memories and enriches them; nothing lets an outside signal say "this cycle,
preferentially reconsolidate memories about topic X." Human sleep is not so
indifferent: re-presenting a cue (an odor, a sound) that was paired with
specific material during prior learning, delivered during slow-wave sleep,
biases consolidation toward *those* cued memories — targeted memory
reactivation (TMR). F2 adds exactly that hook: an optional cue that re-weights
the replay set before the offline pass, so cue-related memories preferentially
enter and lead the bounded replay selection.

Neuroscience basis (DOIs verified against Crossref in-session):
  - Rasch, Büchel, Gais & Born (2007), "Odor Cues During Slow-Wave Sleep
    Prompt Declarative Memory Consolidation," Science 315(5817):1426-1429
    (doi:10.1126/science.1138581). The core TMR result: re-presenting a
    learning-paired odor cue during SWS selectively reactivates and
    strengthens the cued declarative memories — cueing biases *which* memories
    consolidate, which is the single behavior this module operationalises.
  - Oudiette & Paller (2013), "Upgrading the sleeping brain with targeted
    memory reactivation," Trends in Cognitive Sciences 17(3):142-149
    (doi:10.1016/j.tics.2013.01.006). Review establishing TMR as a general
    method (odor and sound cues) for biasing sleep-dependent consolidation
    toward selected memories — the anchor for treating a cue as a topic filter
    over the replay set rather than an odor-specific effect.

Design (pure business logic — no I/O; all storage stays with the caller):
  - ``cue_match_score`` — a deterministic lexical match in [0,1] between a cue
    (a topic / tag / entity / free-text string) and a memory's searchable text
    (content + tags + domain + entities). Jaccard-style cue coverage: fraction
    of cue tokens present in the memory. This mirrors
    ``attentional_control.relevance_score`` (same query-coverage shape); it is
    lexical, not semantic — a caller holding a vector similarity may pass a
    precomputed score instead.
  - ``replay_priority`` — the priority the replay selector should rank by:
    ``heat + CUE_BOOST * cue_match_score``. With no cue (``None`` / empty /
    all-whitespace) the boost term is exactly zero, so priority == heat — the
    pre-F2 selection criterion, unchanged.
  - ``rerank_replay_set`` — re-rank (and optionally truncate to ``max_replay``)
    a candidate memory list by ``replay_priority``. With no cue this is a plain
    heat-descending sort, i.e. exactly the ordering the heat-heap already
    produces — identity. With a cue, cue-matching memories are boosted up the
    ranking and preferentially retained when the set is truncated.

Behavior-preserving default. Every entry point treats "no cue" as identity:
same set, same heat ordering as before F2. A cue only ever *adds* a
non-negative boost, so it can promote cued memories but never demotes a memory
below where its heat alone would place it relative to an equally-cued peer.

Ablation guard. The guard is applied at the wiring site (``sleep_compute`` /
``sleep_phases``), matching F1's pattern where ``sleep_phases`` — not the pure
core — reads the env var: when ``CORTEX_ABLATE_TARGETED_REACTIVATION=1``
(Mechanism.TARGETED_REACTIVATION) the caller passes ``cue=None``, so the replay
set is selected exactly as it was pre-F2. This module stays pure (no os/env
import) so it is trivially testable and the ablation decision lives with the
consolidation orchestrator.

Honesty note (zetetic standard, matching attentional_control.py /
source_monitoring.py / sleep_phases.py): this is a deterministic cue-matching
RE-WEIGHT of the replay set, not a biophysical model of sleep spindles, slow
oscillations, or odor-evoked reactivation. "TMR" here is a functional analogy
for one thing the 2007 result establishes — that a cue biases *which* memories
consolidate. There are no spindles, no slow-wave/spindle coupling, and no
odor/sound modality: the "cue" is a text topic and the match is lexical token
overlap (or a caller-supplied precomputed score). ``CUE_BOOST`` is a single
hand-tuned constant, not a gain learned against a consolidation-benefit signal.
The boost is additive and non-negative, so with no cue the module is a strict
no-op over the existing heat-based selection.
"""

from __future__ import annotations

import re
from typing import Any, Callable

# ── Constants ────────────────────────────────────────────────────────────────
# How much a full cue match adds to a memory's replay priority, in the same
# units as heat. Hand-tuned: 1.0 lets a fully cue-matching memory compete with
# a distinctly hotter one (heat is typically in ~[0,1]) without erasing heat as
# the primary criterion — a partially-cued warm memory still loses to a much
# hotter uncued one. Not a learned gain; see the module honesty note.
CUE_BOOST = 1.0

_WORD_RE = re.compile(r"[a-z0-9]+")


# ── Cue matching (lexical, in [0,1]) ─────────────────────────────────────────


def _tokens(text: str) -> set[str]:
    """Lower-cased alphanumeric token set (mirrors attentional_control._tokens)."""
    return set(_WORD_RE.findall((text or "").lower()))


def _memory_text(memory: dict[str, Any]) -> str:
    """Assemble the searchable text a cue is matched against.

    Content plus the structured fields that carry topicality — tags, domain,
    and entities — so a cue can hit a memory by its tag/entity even when the
    word is absent from the body. Missing/None fields are skipped; list fields
    (tags, entities) are flattened to their string items.
    """
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

    ``cue_score`` defaults to ``cue_match_score(cue, memory)``; a caller holding
    a semantic (vector) match may pass it directly and the lexical path is
    skipped. With no cue and no precomputed score the boost term is exactly
    zero, so the return value is the memory's ``heat`` — the pre-F2 selection
    criterion, unchanged (identity).
    """
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

    Sorts ``memories`` by ``replay_priority`` descending (heat plus the cue
    boost), a stable sort so equal-priority ties keep their input order. When
    ``max_replay`` is given the list is truncated to that many after ranking, so
    cue-matching memories preferentially survive a bounded selection.

    Identity guarantee: with no cue (``None`` / empty / whitespace) every
    priority equals the memory's heat, so the result is a plain
    heat-descending sort — exactly the ordering the heat-heap in
    ``sleep_compute`` already produces — optionally truncated to ``max_replay``.
    A cue only adds a non-negative boost; it never reorders two memories that
    match the cue equally.

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
