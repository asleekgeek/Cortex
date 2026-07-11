"""Tests for core.wiki_citation_seed — pure candidate classification
(M-D7, INC7.7)."""

from __future__ import annotations

from mcp_server.core.wiki_citation_seed import (
    SeedCandidate,
    SeedDecision,
    SeedReliability,
    classify_seed_candidates,
)


def _candidate(page_id: int, memory_id: int, domain: str = "") -> SeedCandidate:
    return SeedCandidate(
        page_id=page_id,
        memory_id=memory_id,
        domain=domain,
        reliability=SeedReliability.HIGH_DIRECT_MEMORY_ID,
    )


class TestClassifySeedCandidates:
    def test_empty_input_returns_empty_output(self):
        assert classify_seed_candidates([], set()) == []

    def test_candidate_not_in_existing_pairs_is_insert(self):
        candidate = _candidate(page_id=1, memory_id=100)
        decisions = classify_seed_candidates([candidate], existing_pairs=set())
        assert decisions == [SeedDecision(candidate=candidate, action="insert")]

    def test_candidate_already_in_existing_pairs_is_skip_existing(self):
        candidate = _candidate(page_id=1, memory_id=100)
        decisions = classify_seed_candidates([candidate], existing_pairs={(1, 100)})
        assert decisions == [SeedDecision(candidate=candidate, action="skip_existing")]

    def test_preserves_input_order_and_count(self):
        candidates = [_candidate(page_id=i, memory_id=i * 10) for i in range(1, 6)]
        decisions = classify_seed_candidates(
            candidates, existing_pairs={(2, 20), (4, 40)}
        )
        assert len(decisions) == len(candidates)
        assert [d.candidate.page_id for d in decisions] == [1, 2, 3, 4, 5]
        assert [d.action for d in decisions] == [
            "insert",
            "skip_existing",
            "insert",
            "skip_existing",
            "insert",
        ]

    def test_different_page_same_memory_id_is_distinct_pair(self):
        # (page_id, memory_id) is the dedup key -- a memory cited by two
        # different pages must not collide with each other.
        c1 = _candidate(page_id=1, memory_id=100)
        c2 = _candidate(page_id=2, memory_id=100)
        decisions = classify_seed_candidates([c1, c2], existing_pairs={(1, 100)})
        assert decisions[0].action == "skip_existing"
        assert decisions[1].action == "insert"

    def test_same_page_different_memory_id_is_distinct_pair(self):
        c1 = _candidate(page_id=1, memory_id=100)
        c2 = _candidate(page_id=1, memory_id=200)
        decisions = classify_seed_candidates([c1, c2], existing_pairs={(1, 100)})
        assert decisions[0].action == "skip_existing"
        assert decisions[1].action == "insert"

    def test_no_candidate_is_dropped_regardless_of_action(self):
        candidates = [_candidate(page_id=i, memory_id=i) for i in range(1, 4)]
        existing = {(1, 1), (2, 2), (3, 3)}
        decisions = classify_seed_candidates(candidates, existing_pairs=existing)
        assert len(decisions) == 3
        assert all(d.action == "skip_existing" for d in decisions)
