"""One-shot seed of ``wiki.citations`` for pages created BEFORE the
flow-forward write-path landed (I6-D7/INC6.8, ``insert_citation`` wired
into ``wiki_write``'s completion handler — 2026-07-10). M-D7/INC7.7.

INC6.8 explicitly rejected a retroactive backfill for the (then) 154
existing pages ("Q5 ... arbitrage par défaut ... AUCUN backfill
rétroactif" — ``inc6.8-wiki-citations-flow`` memory) *unless the
provenance is not fabricated*. This module seeds exactly the citations
that are NOT fabricated: pages whose ``wiki.pages.memory_id`` column
already carries a verified, FK-constrained pointer to the memory that
authored them (``wiki_migrate.py::_memory_id_from_rel_path`` — the
migration writer that populated this column parses the page's own
filename convention, ``<memory_id>-<slug>.md``, and drops any id that
does not resolve to an existing ``memories`` row before writing —
``_existing_memory_ids``). That is a fact already asserted by the
schema (``UNIQUE REFERENCES memories(id)``), not an inference.

Two other candidate sources were considered and REJECTED for this seed,
per the reliability audit in the campaign report:

- ``wiki.page_sources`` (page -> source *file* edges, 559 rows): wrong
  entity type. It records which source files a page documents, not
  which memories authored it — there is no column to derive a
  memory_id from without a fuzzy string/path match (the same
  string-hash-equality join flagged as a "real precision limit" for
  the unrelated cortex-viz FILE-node edge, ``cortex-viz-wiki-source-
  edges`` memory). Fabricating a memory_id from a file path is exactly
  the provenance fabrication INC6.8/Q5 refused for the retro-link case.
- ``wiki.drafts.memory_id`` (32 published drafts, 20 with memory_id
  set): measured (this campaign's dry-run, live DB query) to be an
  EXACT 1:1 duplicate of the ``wiki.pages.memory_id`` set already
  covered — same 20 (page_id, memory_id) pairs, zero net-new rows.
  Kept as a documented reliability tier (not silently dropped) but
  contributes nothing additional; see ``SeedSource.DRAFT_PUBLISHED``.

Pure logic, no I/O — mirrors ``core/memory_reheat.py``'s DI split
(coding-standards.md §2, Dependency Rule: core imports stdlib only).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SeedReliability(str, Enum):
    """Fiability tier of a candidate (page_id, memory_id) pair.

    HIGH: an exact FK-constrained pointer already asserted by the
    schema — no inference performed by this campaign.
    LOW: would require inferring a memory_id from a non-memory join key
    (e.g. a file path in ``wiki.page_sources``) — categorically
    excluded from this seed's candidate generation (see infra layer);
    kept here only so the taxonomy is documented in one place.
    """

    HIGH_DIRECT_MEMORY_ID = "high_direct_memory_id"
    LOW_INFERRED_FILE_PATH = "low_inferred_file_path"


@dataclass(frozen=True)
class SeedCandidate:
    """One (page, memory) pair proposed for a ``wiki.citations`` row.

    Precondition: ``page_id`` and ``memory_id`` reference existing rows
    in ``wiki.pages`` / ``memories`` respectively (enforced by the
    infra query's join, not re-checked here).
    """

    page_id: int
    memory_id: int
    domain: str
    reliability: SeedReliability


@dataclass(frozen=True)
class SeedDecision:
    """The classify step's verdict for one candidate."""

    candidate: SeedCandidate
    action: str  # "insert" | "skip_existing"


def classify_seed_candidates(
    candidates: list[SeedCandidate],
    existing_pairs: set[tuple[int, int]],
) -> list[SeedDecision]:
    """Classify each candidate as insertable or already-cited.

    Precondition: ``existing_pairs`` is the exact set of (page_id,
    memory_id) pairs already present in ``wiki.citations`` at scan
    time (infra layer's ``list_existing_page_memory_citations``, scoped
    to the same page_ids as ``candidates``) — a snapshot, not a live
    view; a concurrent writer between scan and apply is still safe
    because ``insert_citation``'s ``ON CONFLICT DO NOTHING`` on
    ``uq_wiki_citations_page_memory`` is the final authority (this
    function only makes the dry-run count accurate, it is not itself
    the source of correctness).
    Postcondition: returns exactly ``len(candidates)`` decisions, one
    per input, in the same order; a candidate's action is
    ``"skip_existing"`` iff its (page_id, memory_id) pair is in
    ``existing_pairs``, else ``"insert"``. No candidate is dropped
    silently — every one is journaled by the caller regardless of
    action, honoring §8's "no fabricated success" discipline (an
    idempotent re-run must show 0 ``insert`` decisions, not 0
    candidates).
    """
    decisions: list[SeedDecision] = []
    for candidate in candidates:
        pair = (candidate.page_id, candidate.memory_id)
        action = "skip_existing" if pair in existing_pairs else "insert"
        decisions.append(SeedDecision(candidate=candidate, action=action))
    return decisions


__all__ = [
    "SeedCandidate",
    "SeedDecision",
    "SeedReliability",
    "classify_seed_candidates",
]
