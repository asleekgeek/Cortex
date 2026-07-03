"""Tests for targeted_reactivation (F2) — cue-directed bias over the replay set.

Pure-logic tests: cued memories rank higher; no cue = identity (parity with a
plain heat sort); partial match; empty set. No I/O, no ablation env here (the
ablation guard lives at the wiring site; see test_targeted_reactivation_wiring).
"""

import pytest

from mcp_server.core.targeted_reactivation import (
    CUE_BOOST,
    cue_match_score,
    replay_priority,
    rerank_replay_set,
)


def _mem(mid, heat, content="", tags=None, domain="", entities=None):
    return {
        "id": mid,
        "heat": heat,
        "content": content,
        "tags": tags or [],
        "domain": domain,
        "entities": entities or [],
    }


class TestCueMatchScore:
    def test_no_cue_is_zero(self):
        m = _mem(1, 0.5, content="anything about postgres")
        assert cue_match_score(None, m) == 0.0
        assert cue_match_score("", m) == 0.0
        assert cue_match_score("   ", m) == 0.0

    def test_full_match_content(self):
        m = _mem(1, 0.5, content="the postgres keyset pagination bug")
        assert cue_match_score("postgres", m) == pytest.approx(1.0)

    def test_partial_match_multi_token_cue(self):
        # 1 of 2 cue tokens present → 0.5 coverage.
        m = _mem(1, 0.5, content="the postgres migration ran")
        assert cue_match_score("postgres spindles", m) == pytest.approx(0.5)

    def test_no_overlap_is_zero(self):
        m = _mem(1, 0.5, content="unrelated content about cats")
        assert cue_match_score("postgres", m) == 0.0

    def test_matches_via_tags(self):
        m = _mem(1, 0.5, content="body text", tags=["postgres", "storage"])
        assert cue_match_score("postgres", m) == pytest.approx(1.0)

    def test_matches_via_domain(self):
        m = _mem(1, 0.5, content="body text", domain="database")
        assert cue_match_score("database", m) == pytest.approx(1.0)

    def test_matches_via_entities(self):
        m = _mem(1, 0.5, content="body text", entities=["PostgreSQL"])
        assert cue_match_score("postgresql", m) == pytest.approx(1.0)

    def test_empty_memory_text_is_zero(self):
        m = _mem(1, 0.5, content="")
        assert cue_match_score("postgres", m) == 0.0

    def test_case_insensitive(self):
        m = _mem(1, 0.5, content="POSTGRES rocks")
        assert cue_match_score("Postgres", m) == pytest.approx(1.0)


class TestReplayPriority:
    def test_no_cue_equals_heat(self):
        m = _mem(1, 0.42, content="postgres")
        assert replay_priority(m, None) == pytest.approx(0.42)

    def test_cue_adds_boost(self):
        m = _mem(1, 0.4, content="postgres keyset pagination")
        # full match → heat + CUE_BOOST * 1.0
        assert replay_priority(m, "postgres") == pytest.approx(0.4 + CUE_BOOST)

    def test_partial_cue_partial_boost(self):
        m = _mem(1, 0.4, content="postgres only")
        # 1/2 cue tokens → boost * 0.5
        assert replay_priority(m, "postgres spindles") == pytest.approx(
            0.4 + CUE_BOOST * 0.5
        )

    def test_precomputed_score_bypasses_lexical(self):
        m = _mem(1, 0.4, content="totally unrelated")
        # caller-supplied semantic score wins over the (zero) lexical match
        assert replay_priority(m, "postgres", cue_score=0.75) == pytest.approx(
            0.4 + CUE_BOOST * 0.75
        )


class TestRerankReplaySet:
    def test_no_cue_is_heat_descending_identity(self):
        mems = [
            _mem(1, 0.2, content="cold postgres"),
            _mem(2, 0.9, content="hot unrelated"),
            _mem(3, 0.5, content="warm postgres"),
        ]
        ranked = rerank_replay_set(mems, None)
        # exactly a heat-descending sort — same as the heat-heap ordering
        assert [m["id"] for m in ranked] == [2, 3, 1]

    def test_no_cue_matches_plain_sorted(self):
        mems = [_mem(i, h) for i, h in [(1, 0.1), (2, 0.7), (3, 0.3)]]
        ranked = rerank_replay_set(mems, "")
        expected = sorted(mems, key=lambda m: m["heat"], reverse=True)
        assert [m["id"] for m in ranked] == [m["id"] for m in expected]

    def test_cue_promotes_matching_memory(self):
        mems = [
            _mem(1, 0.2, content="postgres keyset pagination"),  # cued, cool
            _mem(2, 0.9, content="hot but unrelated to the cue"),  # hotter, uncued
        ]
        # Without cue, mem 2 leads; with a strong cue, mem 1 is promoted above it
        # (0.2 + 1.0 = 1.2 > 0.9).
        no_cue = rerank_replay_set(mems, None)
        assert no_cue[0]["id"] == 2
        cued = rerank_replay_set(mems, "postgres")
        assert cued[0]["id"] == 1

    def test_cue_truncation_keeps_cued(self):
        mems = [
            _mem(1, 0.30, content="unrelated a"),
            _mem(2, 0.29, content="unrelated b"),
            _mem(3, 0.10, content="the postgres cue topic"),  # cued but coolest
        ]
        # max_replay=2: without a cue, mem 3 is dropped (coolest); with the cue,
        # mem 3's boost (0.1 + 1.0 = 1.1) keeps it and drops an uncued warmer one.
        no_cue = rerank_replay_set(mems, None, max_replay=2)
        assert [m["id"] for m in no_cue] == [1, 2]
        cued = rerank_replay_set(mems, "postgres", max_replay=2)
        assert 3 in [m["id"] for m in cued]
        assert len(cued) == 2

    def test_equal_cue_match_preserves_heat_order(self):
        # Two memories match the cue equally → heat still breaks the tie.
        mems = [
            _mem(1, 0.3, content="postgres one"),
            _mem(2, 0.6, content="postgres two"),
        ]
        cued = rerank_replay_set(mems, "postgres")
        assert [m["id"] for m in cued] == [2, 1]

    def test_empty_set(self):
        assert rerank_replay_set([], "postgres") == []
        assert rerank_replay_set([], None) == []

    def test_max_replay_none_returns_all(self):
        mems = [_mem(i, 0.5) for i in range(5)]
        assert len(rerank_replay_set(mems, None)) == 5

    def test_stable_sort_ties(self):
        # All equal heat, no cue → input order preserved (stable).
        mems = [_mem(i, 0.5) for i in [3, 1, 2]]
        ranked = rerank_replay_set(mems, None)
        assert [m["id"] for m in ranked] == [3, 1, 2]

    def test_score_fn_override(self):
        mems = [
            _mem(1, 0.2, content="alpha"),
            _mem(2, 0.3, content="beta"),
        ]

        # semantic scorer that only likes mem 1
        def sem(cue, mem):
            return 1.0 if mem["id"] == 1 else 0.0

        ranked = rerank_replay_set(mems, "anything", score_fn=sem)
        # mem1: 0.2 + 1.0 = 1.2 > mem2: 0.3 + 0.0
        assert ranked[0]["id"] == 1
