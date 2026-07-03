"""Unit tests for F1 — NREM/REM two-phase consolidation (sleep_phases.py).

Verifies the pure-logic phase split:
  - NREM phase == the existing single pass (byte-for-byte plan parity);
  - REM phase forms abstract schemas from clusters and recombines overlaps;
  - the orchestrator runs NREM then REM in that fixed order;
  - phase boundaries / counts are reported;
  - edge cases: empty memory set, empty clusters.
"""

from __future__ import annotations

from mcp_server.core import sleep_phases as sp
from mcp_server.core.sleep_compute import run_sleep_compute
from mcp_server.core.schema_extraction import Schema


# ── Fixtures ──────────────────────────────────────────────────────────────────
def _mem(mid, content, heat=1.0, entities=None, tags=None):
    return {
        "id": mid,
        "content": content,
        "heat": heat,
        "importance": 0.5,
        "entities": entities or [],
        "tags": tags or [],
    }


def _cluster(cid, mems, level=1, domain=""):
    return {"cluster_id": cid, "level": level, "memories": mems, "domain": domain}


def _hot_memories():
    # Content > 30 chars so replay enrichment can fire.
    return [
        _mem(1, "The quick brown fox jumps over the lazy dog repeatedly.", heat=5.0),
        _mem(2, "A second memory with enough length to be enriched here.", heat=3.0),
    ]


def _schema_cluster(cid, entity, n=6):
    # n>=5 (min_memories) memories sharing an entity/tag → schema forms.
    mems = [
        _mem(
            100 + cid * 10 + i,
            f"memory about {entity} number {i}",
            entities=[entity],
            tags=[entity],
        )
        for i in range(n)
    ]
    return _cluster(cid, mems, domain="test")


# ── NREM phase: parity with the single pass ───────────────────────────────────
def test_nrem_phase_equals_single_pass():
    mems = _hot_memories()
    clusters = [_cluster(1, mems)]
    nrem = sp.run_nrem_phase([mems], clusters=clusters, directory="d")
    single = run_sleep_compute(mems, clusters=clusters, directory="d")
    assert nrem == single  # NREM reuses the single pass verbatim


def test_nrem_phase_does_exact_replay():
    mems = _hot_memories()
    nrem = sp.run_nrem_phase([mems])
    # Replay produced update dicts keyed by memory_id (exact hippocampal replay).
    assert "replay_updates" in nrem
    replayed_ids = {u["memory_id"] for u in nrem["replay_updates"]}
    assert replayed_ids  # at least one enriched
    assert replayed_ids <= {1, 2}


# ── REM phase: recombination / abstraction ────────────────────────────────────
def test_rem_phase_forms_schema_from_cluster():
    clusters = [_schema_cluster(1, "alpha")]
    rem = sp.run_rem_phase(clusters)
    assert rem["formed_count"] == 1
    assert rem["recombined_count"] == 1
    assert all(isinstance(s, Schema) for s in rem["schemas"])
    assert "alpha" in rem["schemas"][0].entity_signature


def test_rem_phase_recombines_overlapping_schemas():
    # Two clusters sharing the same dominant entity → one merged schema.
    clusters = [_schema_cluster(1, "shared"), _schema_cluster(2, "shared")]
    rem = sp.run_rem_phase(clusters)
    assert rem["formed_count"] == 2
    assert rem["recombined_count"] == 1  # merged into one


def test_rem_phase_keeps_distinct_schemas_separate():
    clusters = [_schema_cluster(1, "alpha"), _schema_cluster(2, "beta")]
    rem = sp.run_rem_phase(clusters)
    assert rem["formed_count"] == 2
    assert rem["recombined_count"] == 2  # no overlap → not merged


def test_rem_phase_empty_clusters_is_noop():
    assert sp.run_rem_phase([])["recombined_count"] == 0
    assert sp.run_rem_phase(None)["formed_count"] == 0


def test_rem_phase_cluster_without_schema_forms_nothing():
    # A tiny cluster (< min_memories) forms no schema.
    clusters = [_cluster(1, [_mem(1, "lonely", entities=["x"])])]
    rem = sp.run_rem_phase(clusters)
    assert rem["formed_count"] == 0
    assert rem["clusters_seen"] == 1


# ── Orchestrator: NREM then REM, in order ─────────────────────────────────────
def test_orchestrator_runs_both_phases_in_order():
    mems = _hot_memories()
    clusters = [_schema_cluster(1, "gamma")]
    plan = sp.run_two_phase_consolidation([mems], clusters=clusters)
    assert plan["sleep_phases"]["phase_order"] == [sp.NREM, sp.REM]
    # NREM keys preserved (single-pass compatibility).
    for k in ("replay_updates", "stale_embeddings", "cluster_summaries", "narration"):
        assert k in plan
    # REM abstraction happened.
    assert plan["sleep_phases"]["rem"]["schemas_formed"] == 1


def test_orchestrator_preserves_single_pass_keys_and_values():
    mems = _hot_memories()
    clusters = [_cluster(1, mems)]
    plan = sp.run_two_phase_consolidation([mems], clusters=clusters, directory="d")
    single = run_sleep_compute(mems, clusters=clusters, directory="d")
    for k in ("replay_updates", "stale_embeddings", "cluster_summaries", "narration"):
        assert plan[k] == single[k]  # NREM outcomes unchanged by the split


def test_orchestrator_phase_boundary_counts():
    mems = _hot_memories()
    clusters = [_schema_cluster(1, "delta")]
    plan = sp.run_two_phase_consolidation([mems], clusters=clusters)
    phases = plan["sleep_phases"]
    assert phases["nrem"]["replayed"] == len(plan["replay_updates"])
    assert phases["rem"]["clusters_seen"] == 1


# ── Edge cases ────────────────────────────────────────────────────────────────
def test_empty_memory_set():
    plan = sp.run_two_phase_consolidation([[]], clusters=[])
    assert plan["replay_updates"] == []
    assert plan["sleep_phases"]["rem"]["schemas_formed"] == 0
    assert plan["sleep_phases"]["phase_order"] == [sp.NREM, sp.REM]


def test_no_clusters_still_runs_nrem():
    mems = _hot_memories()
    plan = sp.run_two_phase_consolidation([mems], clusters=None)
    assert plan["replay_updates"]  # NREM replay still happened
    assert plan["sleep_phases"]["rem"]["schemas_formed"] == 0
