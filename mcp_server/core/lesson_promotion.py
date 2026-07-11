"""Pure logic for lesson promotion (M-D6, INC 7.6).

The lesson (a memory tagged ``lesson`` or ``lesson-candidate``) is the
canonical form; ``memory_rules``, ``prospective_memories``, and wiki pages
are *projections* of it (design doc §M-D6). This module classifies a
lesson's likely projection and builds the job payload the in-session LLM
consumes to actually perform (or skip) the promotion — no I/O, mirrors the
role ``core.auto_curator`` plays for ``curate_wiki``'s jobs.

No auto-promotion happens here or anywhere server-side: a rule changes
recall behavior for every future query (high stakes), so the decision
stays with the LLM/user reading the job, exactly like ``curate_wiki``
never calls ``wiki_write`` itself.
"""

from __future__ import annotations

from typing import Any

# Keyword triage — SUGGESTS a promotion kind, never decides one. A lesson
# whose text talks about recall/ranking mechanics is more likely to want a
# memory_rules row; one phrased as a future-conditional ("next time X,
# do Y") is more likely to want a prospective trigger; anything else
# defaults to the documentary catch-all (wiki page). Wrong suggestions
# cost nothing — see ``promotion_instructions`` below: the reviewing LLM
# reads ``content`` itself and may pick any of the three, or none.
_RULE_KEYWORDS = (
    "recall",
    "rerank",
    "rank",
    "boost",
    "penalt",
    "filter",
    "exclude",
    "surface",
    "deprecated",
)
_TRIGGER_KEYWORDS = (
    "next time",
    "before changing",
    "when ",
    "reminder",
    "always check",
    "remember to",
)

_PROMOTED_PREFIX = "promoted:"

VALID_KINDS = ("rule", "trigger", "wiki")


def classify_promotion_kind(content: str) -> str:
    """Suggest a promotion kind for a lesson's content.

    Precondition: ``content`` is any string, possibly empty.
    Postcondition: returns one of ``VALID_KINDS`` — never raises. "rule"
    if a recall/ranking keyword is present, else "trigger" if a
    future-conditional keyword is present, else "wiki" (M-D6's
    documentary third bucket). This is an advisory heuristic label with
    no measured precision — the job it feeds (``build_promotion_job``)
    documents it as a hint the reviewing LLM may override.
    """
    lowered = (content or "").lower()
    if any(kw in lowered for kw in _RULE_KEYWORDS):
        return "rule"
    if any(kw in lowered for kw in _TRIGGER_KEYWORDS):
        return "trigger"
    return "wiki"


def already_promoted(tags: list[str] | None) -> bool:
    """True iff ``tags`` carries any ``promoted:<kind>`` marker.

    Precondition: ``tags`` is a list of strings or None.
    Postcondition: returns True iff at least one tag starts with
    "promoted:" (case-sensitive, matches the convention this module's
    jobs instruct the LLM to write back). Used to exclude lessons that
    already completed one promotion round from future job batches — a
    single promotion path per lesson (M-D6: no parallel/competing
    promotion state to reconcile).
    """
    return any((t or "").startswith(_PROMOTED_PREFIX) for t in (tags or []))


def build_promotion_job(candidate: dict[str, Any]) -> dict[str, Any]:
    """Build one promotion job payload from a raw candidate row.

    Precondition: ``candidate`` has at minimum an ``id`` key; ``content``
    or ``content_preview``, ``tags``, ``useful_count``, ``access_count``,
    ``domain``, ``created_at`` are read if present (see
    ``infrastructure.pg_store_lesson_promotion.list_lesson_promotion_candidates``
    for the exact shape).
    Postcondition: returns a job dict with a ``suggested_kind`` — never
    raises regardless of which optional keys are present.
    """
    content = candidate.get("content_preview") or candidate.get("content") or ""
    return {
        "memory_id": candidate["id"],
        "content": content,
        "suggested_kind": classify_promotion_kind(content),
        "tags": candidate.get("tags") or [],
        "domain": candidate.get("domain"),
        "useful_count": candidate.get("useful_count", 0),
        "access_count": candidate.get("access_count", 0),
        "created_at": candidate.get("created_at"),
    }


def build_promotion_jobs(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build promotion jobs for every candidate, skipping already-promoted ones.

    Precondition: ``candidates`` is a list of rows shaped as documented in
    ``build_promotion_job``.
    Postcondition: ``len(result) <= len(candidates)`` — only candidates
    whose ``tags`` do NOT already carry a ``promoted:*`` marker are
    included (defense-in-depth alongside the SQL-side exclusion in
    ``list_lesson_promotion_candidates``; kept here too because this
    function is the pure, directly-testable boundary).
    """
    return [
        build_promotion_job(c)
        for c in candidates
        if not already_promoted(c.get("tags"))
    ]


_INSTRUCTIONS = (
    "Each job is one lesson memory with usage evidence (recalled or "
    "rated useful at least once — access_count/useful_count > 0). "
    "suggested_kind is a heuristic hint, not a decision: read `content` "
    "and pick whichever of add_rule (recall-shaping rule), "
    "create_trigger (prospective reminder), or wiki_write (documentary "
    "page) actually fits — or promote none if the lesson doesn't "
    "warrant it. When you DO promote a lesson: (1) for a rule or "
    "trigger, call add_rule/create_trigger with "
    "source_memory_id=<memory_id> so the pointer is queryable both ways; "
    "for a wiki page, call wiki_write(..., memory_ids=[<memory_id>]) — "
    "it already inserts the wiki.citations row, no extra param needed; "
    "(2) then call remember(content=<same or refined lesson text>, "
    "supersedes_id=<memory_id>, tags=[...original tags, "
    "'promoted:<rule|trigger|wiki>'], write_class='deliberate', "
    "force=true) to close the loop on the lesson side (append-only — "
    "never edits the original row; force=true is the documented "
    "'sovereign human correction' combination for supersedes_id — the "
    "gate is bypassed but the supersession edge is still posted, since "
    "a promoted lesson is near-identical to its source and would "
    "otherwise fail the novelty check on its own content). No "
    "promotion happens automatically; this call only proposes "
    "candidates."
)


def promotion_instructions() -> str:
    """Static instructions string handed to the reviewing LLM."""
    return _INSTRUCTIONS
