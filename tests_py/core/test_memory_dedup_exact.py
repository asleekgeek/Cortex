"""Tests for core.memory_dedup_exact — pure survivor election for exact-
duplicate memory groups (I6-D1, INC6.3)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from mcp_server.core.memory_dedup_exact import (
    DuplicateMember,
    ElectionResult,
    elect_survivor,
)


def _dt(iso: str) -> datetime:
    return datetime.fromisoformat(iso).replace(tzinfo=timezone.utc)


class TestHighestHeatWins:
    def test_strictly_highest_effective_heat_is_survivor(self):
        members = [
            DuplicateMember(id=1, effective_heat=0.19, created_at=_dt("2026-01-01")),
            DuplicateMember(id=2, effective_heat=0.43, created_at=_dt("2026-02-01")),
            DuplicateMember(id=3, effective_heat=0.24, created_at=_dt("2026-03-01")),
        ]
        result = elect_survivor(members)
        assert result == ElectionResult(survivor_id=2, superseded_ids=(1, 3))

    def test_order_in_list_does_not_matter(self):
        members = [
            DuplicateMember(id=3, effective_heat=0.24, created_at=_dt("2026-03-01")),
            DuplicateMember(id=2, effective_heat=0.43, created_at=_dt("2026-02-01")),
            DuplicateMember(id=1, effective_heat=0.19, created_at=_dt("2026-01-01")),
        ]
        result = elect_survivor(members)
        assert result.survivor_id == 2
        assert set(result.superseded_ids) == {1, 3}


class TestTieBreakByOldest:
    def test_equal_heat_oldest_created_at_wins(self):
        members = [
            DuplicateMember(id=10, effective_heat=0.30, created_at=_dt("2026-05-01")),
            DuplicateMember(id=11, effective_heat=0.30, created_at=_dt("2026-01-01")),
            DuplicateMember(id=12, effective_heat=0.30, created_at=_dt("2026-03-01")),
        ]
        result = elect_survivor(members)
        assert result == ElectionResult(survivor_id=11, superseded_ids=(10, 12))

    def test_heat_beats_age_when_both_differ(self):
        # id=1 is older but colder; id=2 is younger but hotter -> heat wins.
        members = [
            DuplicateMember(id=1, effective_heat=0.10, created_at=_dt("2020-01-01")),
            DuplicateMember(id=2, effective_heat=0.20, created_at=_dt("2026-01-01")),
        ]
        result = elect_survivor(members)
        assert result.survivor_id == 2


class TestSupersededIdsExcludeSurvivor:
    def test_survivor_never_appears_in_superseded_ids(self):
        members = [
            DuplicateMember(id=5, effective_heat=1.0, created_at=_dt("2026-01-01")),
            DuplicateMember(id=6, effective_heat=0.5, created_at=_dt("2026-01-01")),
        ]
        result = elect_survivor(members)
        assert result.survivor_id not in result.superseded_ids
        assert len(result.superseded_ids) == len(members) - 1


class TestGroupSizeGuard:
    def test_single_member_raises(self):
        with pytest.raises(ValueError):
            elect_survivor(
                [
                    DuplicateMember(
                        id=1, effective_heat=0.5, created_at=_dt("2026-01-01")
                    )
                ]
            )

    def test_empty_list_raises(self):
        with pytest.raises(ValueError):
            elect_survivor([])


class TestLargerGroup:
    def test_five_member_group_one_survivor_four_superseded(self):
        members = [
            DuplicateMember(id=i, effective_heat=0.1 * i, created_at=_dt("2026-01-01"))
            for i in range(1, 6)
        ]
        result = elect_survivor(members)
        assert result.survivor_id == 5  # highest heat: 0.5
        assert set(result.superseded_ids) == {1, 2, 3, 4}
        assert len(result.superseded_ids) == 4
