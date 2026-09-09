"""Seed wiki citations from page and memory evidence.

source: ADR-0293
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SeedReliability(str, Enum):
    """Fiability tier of a candidate (page_id, memory_id) pair.

    source: ADR-0293"""

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

    Precondition: existing_pairs is the scan-time (page_id, memory_id) set
    from wiki.citations for the candidate page IDs.
    Postcondition: returns one decision per candidate in input order; action
    is skip_existing iff the pair exists, otherwise insert. No candidates
    are silently dropped. Concurrent insertions are handled by the writer.
    source: ADR-0293"""
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
