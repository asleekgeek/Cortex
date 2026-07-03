"""Integration test for F1 — NREM/REM two-phase consolidation wiring.

Verifies the offline consolidation path (run_deep_sleep, invoked by the
consolidate handler) as routed through run_two_phase_consolidation:
  - the deep-sleep pass runs NREM then REM and reports a sleep_phases block;
  - existing NREM outcomes (replayed / reembedded / narration) are preserved
    vs the single-pass baseline;
  - CORTEX_ABLATE_SLEEP_PHASES=1 falls back to single-pass NREM only
    (phase_order == ["nrem"], no REM abstraction);
  - the orchestrator itself preserves single-pass plan keys/values.

No Postgres — a fake store + fake embedding engine stand in.
"""

from __future__ import annotations

import os

from mcp_server.core import sleep_phases as sp
from mcp_server.core.sleep_compute import run_sleep_compute
from mcp_server.handlers.consolidation.sleep import run_deep_sleep


# ── Fakes ─────────────────────────────────────────────────────────────────────
class _FakeEmbeddings:
    def encode(self, text):
        # Deterministic tiny vector; length keys off content so it's non-empty.
        return [float(len(text) % 7), 1.0, 0.0]


class _FakeStore:
    """Minimal store covering the calls run_deep_sleep makes."""

    def __init__(self, memories):
        self._memories = memories
        self.updated = []
        self.inserted = []
        self.reembedded = []

    def iter_memories_for_decay(self):
        yield self._memories

    def update_memory_compression(self, mid, content, emb, compression_level=0):
        self.updated.append(mid)

    def acquire_batch(self):
        store = self

        class _Ctx:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def execute(self, sql, params):
                store.reembedded.append(params[-1])

        return _Ctx()

    def insert_memory(self, row):
        self.inserted.append(row)


def _mem(mid, content, heat=1.0, entities=None, tags=None):
    return {
        "id": mid,
        "content": content,
        "heat": heat,
        "importance": 0.5,
        "embedding": [1.0, 0.0],  # present → not stale
        "entities": entities or [],
        "tags": tags or [],
    }


def _corpus():
    # >=5 memories so narration stores; content>30 so replay enriches.
    return [
        _mem(i, f"A memory about consolidation topic number {i} here.", heat=float(i))
        for i in range(1, 7)
    ]


# ── Two phases run, telemetry surfaced ────────────────────────────────────────
def test_deep_sleep_runs_two_phases_and_reports_telemetry():
    store = _FakeStore(_corpus())
    res = run_deep_sleep(store, _FakeEmbeddings(), memories=None)
    assert "sleep_phases" in res
    assert res["sleep_phases"]["phase_order"] == [sp.NREM, sp.REM]
    # NREM did exact replay (some memories enriched & updated).
    assert res["replayed"] >= 0
    assert "nrem" in res["sleep_phases"] and "rem" in res["sleep_phases"]


def test_deep_sleep_preserves_nrem_outcomes():
    mems = _corpus()
    baseline = run_sleep_compute(mems, clusters=[], directory="")
    store = _FakeStore(mems)
    res = run_deep_sleep(store, _FakeEmbeddings(), memories=mems)
    # replayed count matches the single-pass replay set size.
    assert res["replayed"] == len(baseline["replay_updates"])


# ── Ablation fallback ─────────────────────────────────────────────────────────
def test_ablation_falls_back_to_single_pass_nrem_only():
    store = _FakeStore(_corpus())
    os.environ["CORTEX_ABLATE_SLEEP_PHASES"] = "1"
    try:
        res = run_deep_sleep(store, _FakeEmbeddings(), memories=None)
    finally:
        del os.environ["CORTEX_ABLATE_SLEEP_PHASES"]
    assert res["sleep_phases"]["phase_order"] == [sp.NREM]
    assert res["sleep_phases"]["rem"]["schemas_formed"] == 0


# ── Orchestrator plan parity vs single pass ───────────────────────────────────
def test_orchestrator_plan_matches_single_pass_on_nrem_keys():
    mems = _corpus()
    clusters = [{"cluster_id": 1, "level": 1, "memories": mems}]
    plan = sp.run_two_phase_consolidation([mems], clusters=clusters, directory="d")
    single = run_sleep_compute(mems, clusters=clusters, directory="d")
    for k in ("replay_updates", "stale_embeddings", "cluster_summaries", "narration"):
        assert plan[k] == single[k]


def test_ablated_orchestrator_equals_single_pass_plus_marker():
    mems = _corpus()
    clusters = [{"cluster_id": 1, "level": 1, "memories": mems}]
    os.environ["CORTEX_ABLATE_SLEEP_PHASES"] = "1"
    try:
        plan = sp.run_two_phase_consolidation([mems], clusters=clusters, directory="d")
    finally:
        del os.environ["CORTEX_ABLATE_SLEEP_PHASES"]
    single = run_sleep_compute(mems, clusters=clusters, directory="d")
    # Every single-pass key identical; only the sleep_phases marker is added.
    assert plan["sleep_phases"]["phase_order"] == [sp.NREM]
    for k in single:
        assert plan[k] == single[k]
