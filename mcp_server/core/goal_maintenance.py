"""Goal / task-set maintenance (A3) — a sustained goal vector that biases
processing toward goal-relevant information.

source: ADR-0185"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# source: ADR-0185


GOAL_WRITE_WEIGHT: float = 0.15

# source: ADR-0185


GOAL_RECALL_WEIGHT: float = 0.15

# source: ADR-0185


_MIN_KEYWORD_LEN: int = 3

# source: ADR-0185


_STOP_WORDS = frozenset({"the", "and", "for", "with", "that", "this", "from"})

_WORD_RE = re.compile(r"[a-z0-9]+")


# ── Goal vector ──────────────────────────────────────────────────────────────
@dataclass
class GoalVector:
    """A sustained goal / task-set representation (A3).

    Three feature families lifted from the prospective trigger schema:

    ``keywords``     — lowercased content tokens the active task is about.
    ``entities``     — lowercased named entities the task concerns.
    ``directories``  — lowercased working-directory fragments the task is
                       scoped to.

    source: ADR-0185"""

    keywords: frozenset[str] = field(default_factory=frozenset)
    entities: frozenset[str] = field(default_factory=frozenset)
    directories: tuple[str, ...] = ()
    label: str = ""


def goal_vector_is_active(goal: "GoalVector") -> bool:
    """True iff the goal carries any keyword, entity, or directory signal.

    source: ADR-0185"""
    return bool(goal.keywords or goal.entities or goal.directories)


def goal_vector_as_dict(goal: "GoalVector") -> dict:
    return {
        "label": goal.label,
        "keywords": sorted(goal.keywords),
        "entities": sorted(goal.entities),
        "directories": list(goal.directories),
        "is_active": goal_vector_is_active(goal),
    }


# The canonical inactive goal — a module-level singleton the caller can use when
# no task is in play. Sharing one instance makes the "no active goal" identity
# path allocation-free.
EMPTY_GOAL = GoalVector()


def _tokenize(text: str) -> list[str]:
    """Lowercase word-boundary tokens, filtered like the prospective extractor."""
    return [
        w
        for w in _WORD_RE.findall(text.lower())
        if len(w) >= _MIN_KEYWORD_LEN and w not in _STOP_WORDS
    ]


def build_goal_from_triggers(
    triggers: list[dict] | None,
    *,
    label: str = "",
) -> GoalVector:
    """Promote a set of active prospective triggers into a sustained goal vector.

    Consumes the SAME trigger dicts ``core.prospective`` produces and stores
    ({``trigger_type``, ``trigger_condition``, optional ``target_directory``}).
    Each contributes to the goal by its type:

      - ``keyword_match``   → its condition tokens join the goal keywords.
      - ``entity_match``    → its condition (a single entity name) joins the
                              goal entities.
      - ``directory_match`` → its ``target_directory`` (or condition) joins the
                              goal directories.
      - ``time_based``      → contributes nothing to the goal surface (a clock
                              condition is not a content/task signal).

    An empty or None trigger list yields ``EMPTY_GOAL`` (inactive). This is the
    promotion step A3 is built on: prospective triggers are momentary,
    event-driven checks; the goal vector holds their content forward as the
    task-set that biases subsequent writes and recalls while it is active.
    """
    if not triggers:
        return EMPTY_GOAL

    keywords: set[str] = set()
    entities: set[str] = set()
    directories: list[str] = []

    for trig in triggers:
        ttype = trig.get("trigger_type", "")
        condition = (trig.get("trigger_condition") or "").strip()
        if ttype == "keyword_match":
            keywords.update(_tokenize(condition))
        elif ttype == "entity_match":
            if condition:
                entities.add(condition.lower())
        elif ttype == "directory_match":
            target = (trig.get("target_directory") or condition).strip().lower()
            if target:
                directories.append(target)
        # time_based and unknown types contribute no task-content signal.

    if not (keywords or entities or directories):
        return EMPTY_GOAL

    return GoalVector(
        keywords=frozenset(keywords),
        entities=frozenset(entities),
        directories=tuple(directories),
        label=label,
    )


def build_goal_from_task(
    task: str,
    *,
    entities: list[str] | None = None,
    directory: str = "",
    label: str = "",
) -> GoalVector:
    """Build a goal vector directly from an explicit current-task description.

    A convenience alternative to ``build_goal_from_triggers`` for callers that
    already know the current task (e.g. an agent-supplied focus string) rather
    than harvesting it from stored prospective triggers. The task text is
    tokenized into keywords with the same filter; ``entities`` and ``directory``
    populate the other two families. An empty task with no entities/directory
    yields ``EMPTY_GOAL``.
    """
    keywords = frozenset(_tokenize(task or ""))
    ents = frozenset(e.lower() for e in (entities or []) if e)
    dirs = (directory.strip().lower(),) if directory.strip() else ()
    if not (keywords or ents or dirs):
        return EMPTY_GOAL
    return GoalVector(
        keywords=keywords,
        entities=ents,
        directories=dirs,
        label=label or (task.strip() if task else ""),
    )


# ── Goal relevance ───────────────────────────────────────────────────────────
def _keyword_overlap(goal_keywords: frozenset[str], content: str) -> float:
    """Fraction of goal keywords present (word-boundary) in the content."""
    if not goal_keywords:
        return 0.0
    content_tokens = set(_WORD_RE.findall(content.lower()))
    if not content_tokens:
        return 0.0
    hit = sum(1 for kw in goal_keywords if kw in content_tokens)
    return hit / len(goal_keywords)


def _entity_overlap(goal_entities: frozenset[str], entities: list[str] | None) -> float:
    """Fraction of goal entities present in the candidate's entity list."""
    if not goal_entities:
        return 0.0
    cand = {e.lower() for e in (entities or []) if e}
    if not cand:
        return 0.0
    hit = sum(1 for ge in goal_entities if ge in cand)
    return hit / len(goal_entities)


def _directory_match(goal_directories: tuple[str, ...], directory: str) -> float:
    """1.0 iff the candidate's directory falls under any goal directory."""
    if not goal_directories or not directory:
        return 0.0
    d = directory.lower()
    return 1.0 if any(gd and gd in d for gd in goal_directories) else 0.0


def goal_relevance(
    goal: GoalVector,
    content: str,
    *,
    entities: list[str] | None = None,
    directory: str = "",
) -> float:
    """Score how well a candidate matches the active goal, in [0, 1].

    The score is the MAX of the three feature-family overlaps (keyword, entity,
    directory) — a candidate is goal-relevant if it matches the task on *any*
    axis, and matching on several does not inflate it past 1.0. An inactive
    goal (``EMPTY_GOAL`` / no signal) scores every candidate 0.0, which drives
    the re-weight factors below to the identity 1.0.

    source: ADR-0185"""
    if not goal_vector_is_active(goal):
        return 0.0
    kw = _keyword_overlap(goal.keywords, content)
    ent = _entity_overlap(goal.entities, entities)
    d = _directory_match(goal.directories, directory)
    return max(kw, ent, d)


# ── Re-weight helpers (the multiplicative nudge) ─────────────────────────────
def goal_write_gain(
    goal: GoalVector,
    content: str,
    *,
    entities: list[str] | None = None,
    directory: str = "",
    weight: float = GOAL_WRITE_WEIGHT,
) -> float:
    """Write-gate gain in [1.0, 1.0 + weight] for a candidate input.

    source: ADR-0185"""
    if not goal_vector_is_active(goal):
        return 1.0
    rel = goal_relevance(goal, content, entities=entities, directory=directory)
    return 1.0 + weight * rel


def goal_recall_multiplier(
    goal: GoalVector,
    content: str,
    *,
    entities: list[str] | None = None,
    directory: str = "",
    weight: float = GOAL_RECALL_WEIGHT,
) -> float:
    """Recall-score multiplier in [1.0, 1.0 + weight] for a candidate memory.

    source: ADR-0185"""
    if not goal_vector_is_active(goal):
        return 1.0
    rel = goal_relevance(goal, content, entities=entities, directory=directory)
    return 1.0 + weight * rel
