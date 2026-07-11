"""Tests for core.distillation (INC7.8/M-D8) — pure dossier assembly.

No DB, no I/O: every builder receives plain dicts/tuples and returns
DistillDossier objects. Covers: error->success pairing (entity overlap +
temporal window + no-double-claim), co-access connected components, the
idempotence marker's determinism, and the CurationCluster adapter.
"""

from __future__ import annotations

from mcp_server.core.distillation import (
    DistillDossier,
    build_co_access_dossiers,
    build_error_success_dossiers,
    dossier_from_cluster,
    dossier_marker_tag,
)


def _mem(id_, content, created_at, domain="cortex"):
    return {"id": id_, "content": content, "created_at": created_at, "domain": domain}


class TestDossierMarkerTag:
    def test_deterministic_regardless_of_order(self):
        assert dossier_marker_tag([3, 1, 2]) == dossier_marker_tag([1, 2, 3])

    def test_deduplicates(self):
        assert dossier_marker_tag([1, 1, 2]) == dossier_marker_tag([1, 2])

    def test_different_sets_differ(self):
        assert dossier_marker_tag([1, 2]) != dossier_marker_tag([1, 3])


class TestDistillDossierPostInit:
    def test_sorts_and_dedupes_memory_ids(self):
        d = DistillDossier(
            kind="entity_family", topic="x", domain="cortex", memory_ids=[3, 1, 1, 2]
        )
        assert d.memory_ids == [1, 2, 3]

    def test_marker_auto_set_from_ids(self):
        d = DistillDossier(
            kind="entity_family", topic="x", domain="cortex", memory_ids=[5, 7]
        )
        assert d.marker == dossier_marker_tag([5, 7])

    def test_explicit_marker_preserved(self):
        d = DistillDossier(
            kind="entity_family",
            topic="x",
            domain="cortex",
            memory_ids=[5, 7],
            marker="custom",
        )
        assert d.marker == "custom"


class TestBuildErrorSuccessDossiers:
    def test_pairs_error_with_nearest_later_shared_entity_success(self):
        errors = [
            _mem(
                1,
                "write_gate.py raised ValueError on bad input",
                "2026-07-01T00:00:00+00:00",
            )
        ]
        successes = [
            _mem(
                2,
                "write_gate.py fixed: ValueError now caught",
                "2026-07-01T02:00:00+00:00",
            ),
            _mem(3, "unrelated_module.py refactor done", "2026-07-01T01:00:00+00:00"),
        ]
        dossiers = build_error_success_dossiers(errors, successes, window_hours=24.0)
        assert len(dossiers) == 1
        assert dossiers[0].kind == "error_success"
        assert dossiers[0].memory_ids == [1, 2]

    def test_success_outside_window_not_paired(self):
        errors = [
            _mem(1, "write_gate.py raised ValueError", "2026-07-01T00:00:00+00:00")
        ]
        successes = [
            _mem(2, "write_gate.py fixed ValueError", "2026-07-10T00:00:00+00:00")
        ]
        dossiers = build_error_success_dossiers(errors, successes, window_hours=24.0)
        assert dossiers == []

    def test_success_before_error_not_paired(self):
        errors = [
            _mem(1, "write_gate.py raised ValueError", "2026-07-01T12:00:00+00:00")
        ]
        successes = [
            _mem(2, "write_gate.py fixed ValueError", "2026-07-01T00:00:00+00:00")
        ]
        dossiers = build_error_success_dossiers(errors, successes, window_hours=24.0)
        assert dossiers == []

    def test_memory_tagged_both_error_and_success_never_self_pairs(self):
        """Regression (found live on the dev-DB dry-run, INC7.8): a
        memory carrying BOTH 'error' and 'success' tags appears in both
        input lists with the SAME id. Without the succ_id != err_id
        guard, it "pairs with itself" (delta=0, trivially shares its own
        entities) and produces a 1-member dossier."""
        both = _mem(
            1,
            "write_gate.py raised ValueError, then fixed",
            "2026-07-01T00:00:00+00:00",
        )
        dossiers = build_error_success_dossiers([both], [both], window_hours=24.0)
        assert dossiers == []

    def test_no_shared_entity_not_paired(self):
        errors = [
            _mem(1, "write_gate.py raised ValueError", "2026-07-01T00:00:00+00:00")
        ]
        successes = [
            _mem(2, "totally_different_module.py refactor", "2026-07-01T01:00:00+00:00")
        ]
        dossiers = build_error_success_dossiers(errors, successes, window_hours=24.0)
        assert dossiers == []

    def test_a_success_is_claimed_by_at_most_one_error(self):
        errors = [
            _mem(1, "write_gate.py raised ValueError", "2026-07-01T00:00:00+00:00"),
            _mem(2, "write_gate.py raised TypeError", "2026-07-01T00:30:00+00:00"),
        ]
        successes = [
            _mem(3, "write_gate.py fixed all errors", "2026-07-01T01:00:00+00:00")
        ]
        dossiers = build_error_success_dossiers(errors, successes, window_hours=24.0)
        assert len(dossiers) == 1
        claimed = {mid for d in dossiers for mid in d.memory_ids if mid == 3}
        assert len(claimed) == 1

    def test_max_dossiers_respected(self):
        errors = [
            _mem(i, f"module_{i}.py raised ValueError", f"2026-07-01T00:0{i}:00+00:00")
            for i in range(5)
        ]
        successes = [
            _mem(
                100 + i,
                f"module_{i}.py fixed ValueError",
                f"2026-07-01T01:0{i}:00+00:00",
            )
            for i in range(5)
        ]
        dossiers = build_error_success_dossiers(
            errors, successes, window_hours=24.0, max_dossiers=2
        )
        assert len(dossiers) == 2

    def test_empty_inputs(self):
        assert build_error_success_dossiers([], [], window_hours=24.0) == []


class TestBuildCoAccessDossiers:
    def test_connected_component_above_min_size(self):
        pairs = [(1, 2, 0.9), (2, 3, 0.8), (1, 3, 0.7)]
        dossiers = build_co_access_dossiers(pairs, min_cluster_size=3)
        assert len(dossiers) == 1
        assert dossiers[0].memory_ids == [1, 2, 3]
        assert dossiers[0].kind == "co_access_family"

    def test_component_below_min_size_dropped(self):
        pairs = [(1, 2, 0.9)]
        dossiers = build_co_access_dossiers(pairs, min_cluster_size=3)
        assert dossiers == []

    def test_two_disjoint_components(self):
        pairs = [(1, 2, 0.9), (2, 3, 0.8), (10, 11, 0.9), (11, 12, 0.8)]
        dossiers = build_co_access_dossiers(pairs, min_cluster_size=3)
        assert len(dossiers) == 2
        member_sets = {tuple(d.memory_ids) for d in dossiers}
        assert (1, 2, 3) in member_sets
        assert (10, 11, 12) in member_sets

    def test_avg_heat_computed_from_heat_by_id(self):
        pairs = [(1, 2, 0.9), (2, 3, 0.8)]
        heat_by_id = {1: 0.2, 2: 0.4, 3: 0.6}
        dossiers = build_co_access_dossiers(
            pairs, heat_by_id=heat_by_id, min_cluster_size=3
        )
        assert len(dossiers) == 1
        assert abs(dossiers[0].avg_heat - 0.4) < 1e-9

    def test_empty_pairs(self):
        assert build_co_access_dossiers([]) == []

    def test_max_dossiers_respected(self):
        # 3 disjoint triangles, cap to 2 dossiers.
        pairs = [
            (1, 2, 0.9),
            (2, 3, 0.8),
            (10, 11, 0.9),
            (11, 12, 0.8),
            (20, 21, 0.9),
            (21, 22, 0.8),
        ]
        dossiers = build_co_access_dossiers(pairs, min_cluster_size=3, max_dossiers=2)
        assert len(dossiers) == 2


class _FakeCluster:
    def __init__(self):
        self.topic = "write_gate"
        self.domain = "cortex"
        self.memory_ids = [7, 8, 9]
        self.entities = ["write_gate", "gate"]
        self.avg_heat = 0.42


class TestDossierFromCluster:
    def test_field_mapping(self):
        d = dossier_from_cluster(_FakeCluster())
        assert d.kind == "entity_family"
        assert d.topic == "write_gate"
        assert d.domain == "cortex"
        assert d.memory_ids == [7, 8, 9]
        assert d.entities == ["write_gate", "gate"]
        assert d.avg_heat == 0.42
        assert d.marker == dossier_marker_tag([7, 8, 9])

    def test_oversized_cluster_capped(self):
        """Regression (found live on the dev-DB dry-run, INC7.8): one
        real entity_family cluster had 53 members — build_clusters does
        not bound cluster size itself."""
        cluster = _FakeCluster()
        cluster.memory_ids = list(range(1, 54))  # 53 members
        d = dossier_from_cluster(cluster)
        assert len(d.memory_ids) <= 12
