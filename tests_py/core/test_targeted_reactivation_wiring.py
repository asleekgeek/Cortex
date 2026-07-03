"""Wiring tests for F2 targeted reactivation into the NREM replay selection.

Verifies:
  - A cue biases which memories enter the bounded NREM replay set / ordering.
  - No cue == identity vs the pre-F2 heat-only selection.
  - CORTEX_ABLATE_TARGETED_REACTIVATION=1 forces cue-off (identity).
  - F1's sleep_phases behavior (NREM/REM, SLEEP_PHASES ablation) still holds.
  - The sleep_phases block carries the tmr telemetry cortex-viz reads.

These call the real orchestrator (run_two_phase_consolidation) and the streamed
sleep-compute pass. Enrichment requires content >= 30 chars and no doc2query
marker to produce a replay_update, so test memories use long, distinct bodies.
"""

import os

import pytest

from mcp_server.core.ablation import Mechanism
from mcp_server.core.sleep_compute import run_sleep_compute_streamed
from mcp_server.core.sleep_phases import run_two_phase_consolidation


def _mem(mid, heat, content, tags=None, domain=""):
    return {
        "id": mid,
        "heat": heat,
        "content": content,
        "tags": tags or [],
        "domain": domain,
        "embedding": [0.1],  # non-stale, so it isn't pulled for re-embedding
        "importance": heat,
    }


# Long, distinct bodies (>=30 chars, no doc2query marker) so each produces a
# replay_update when selected.
_POSTGRES = (
    "the postgres keyset pagination bug over heat_base and id needs a composite "
    "index to avoid a full table scan on the shared store"
)
_UNRELATED = (
    "the frontend react component rendering loop redraws the whole cortex-viz "
    "sidebar on every websocket tick which is wasteful and janky"
)


@pytest.fixture(autouse=True)
def _clear_ablation_env():
    """Ensure a clean ablation env around each test."""
    saved = {
        k: os.environ.pop(k, None)
        for k in (
            "CORTEX_ABLATE_TARGETED_REACTIVATION",
            "CORTEX_ABLATE_SLEEP_PHASES",
        )
    }
    yield
    for k, v in saved.items():
        if v is not None:
            os.environ[k] = v
        else:
            os.environ.pop(k, None)


def _replay_ids(plan):
    return [u["memory_id"] for u in plan["replay_updates"]]


class TestStreamedCueBias:
    def test_no_cue_is_heat_only_identity(self):
        mems = [
            _mem(1, 0.2, _POSTGRES),
            _mem(2, 0.9, _UNRELATED),
        ]
        # max_replay=1: heat-only keeps the hotter (uncued) memory 2.
        plan = run_sleep_compute_streamed([mems], max_replay=1)
        assert _replay_ids(plan) == [2]

    def test_cue_promotes_cued_into_bounded_set(self):
        mems = [
            _mem(1, 0.2, _POSTGRES),   # cued but cooler
            _mem(2, 0.9, _UNRELATED),  # hotter, uncued
        ]
        # max_replay=1 + cue: cued memory 1 (0.2 + 1.0 = 1.2) beats memory 2.
        plan = run_sleep_compute_streamed([mems], max_replay=1, cue="postgres")
        assert _replay_ids(plan) == [1]

    def test_cue_reorders_replay(self):
        mems = [
            _mem(1, 0.2, _POSTGRES),
            _mem(2, 0.5, _UNRELATED),
        ]
        # Both fit (max_replay=2); hottest-first ordering. No cue → 2 then 1.
        no_cue = run_sleep_compute_streamed([mems], max_replay=2)
        assert _replay_ids(no_cue) == [2, 1]
        # Cue lifts memory 1's priority above memory 2 → 1 then 2.
        cued = run_sleep_compute_streamed([mems], max_replay=2, cue="postgres")
        assert _replay_ids(cued) == [1, 2]


class TestTwoPhaseCueWiring:
    def test_no_cue_identity_vs_pre_f2(self):
        mems = [_mem(1, 0.2, _POSTGRES), _mem(2, 0.9, _UNRELATED)]
        # Pre-F2 baseline == run_two_phase with no cue.
        baseline = run_sleep_compute_streamed([mems], max_replay=1)
        plan = run_two_phase_consolidation([mems], clusters=[], max_replay=1)
        assert _replay_ids(plan) == _replay_ids(baseline) == [2]
        assert plan["sleep_phases"]["tmr"]["cue"] is None
        assert plan["sleep_phases"]["tmr"]["cued_replayed"] == 0

    def test_cue_biases_and_reports(self):
        mems = [_mem(1, 0.2, _POSTGRES), _mem(2, 0.9, _UNRELATED)]
        plan = run_two_phase_consolidation(
            [mems], clusters=[], max_replay=1, cue="postgres"
        )
        assert _replay_ids(plan) == [1]
        tmr = plan["sleep_phases"]["tmr"]
        assert tmr["cue"] == "postgres"
        assert tmr["ablated"] is False
        assert tmr["cued_replayed"] == 1

    def test_ablation_forces_cue_off(self):
        os.environ["CORTEX_ABLATE_TARGETED_REACTIVATION"] = "1"
        mems = [_mem(1, 0.2, _POSTGRES), _mem(2, 0.9, _UNRELATED)]
        # Even with a cue passed, ablation forces heat-only selection (memory 2).
        plan = run_two_phase_consolidation(
            [mems], clusters=[], max_replay=1, cue="postgres"
        )
        assert _replay_ids(plan) == [2]
        tmr = plan["sleep_phases"]["tmr"]
        assert tmr["ablated"] is True
        assert tmr["cue"] is None
        assert tmr["cued_replayed"] == 0

    def test_ablation_matches_no_cue_baseline(self):
        mems = [_mem(1, 0.2, _POSTGRES), _mem(2, 0.9, _UNRELATED)]
        baseline = run_two_phase_consolidation([mems], clusters=[], max_replay=1)
        os.environ["CORTEX_ABLATE_TARGETED_REACTIVATION"] = "1"
        ablated = run_two_phase_consolidation(
            [mems], clusters=[], max_replay=1, cue="postgres"
        )
        assert _replay_ids(ablated) == _replay_ids(baseline)


class TestF1StillGreen:
    def test_phase_order_default_nrem_then_rem(self):
        mems = [_mem(1, 0.5, _POSTGRES)]
        plan = run_two_phase_consolidation([mems], clusters=[])
        assert plan["sleep_phases"]["phase_order"] == ["nrem", "rem"]

    def test_sleep_phases_ablation_skips_rem(self):
        os.environ["CORTEX_ABLATE_SLEEP_PHASES"] = "1"
        mems = [_mem(1, 0.5, _POSTGRES)]
        plan = run_two_phase_consolidation([mems], clusters=[])
        assert plan["sleep_phases"]["phase_order"] == ["nrem"]

    def test_nrem_keys_preserved(self):
        mems = [_mem(1, 0.5, _POSTGRES)]
        plan = run_two_phase_consolidation([mems], clusters=[])
        for key in (
            "replay_updates",
            "stale_embeddings",
            "cluster_summaries",
            "narration",
        ):
            assert key in plan

    def test_tmr_and_sleep_phases_independent(self):
        # SLEEP_PHASES ablated but TMR active: cue still biases NREM replay.
        os.environ["CORTEX_ABLATE_SLEEP_PHASES"] = "1"
        mems = [_mem(1, 0.2, _POSTGRES), _mem(2, 0.9, _UNRELATED)]
        plan = run_two_phase_consolidation(
            [mems], clusters=[], max_replay=1, cue="postgres"
        )
        assert _replay_ids(plan) == [1]
        assert plan["sleep_phases"]["phase_order"] == ["nrem"]
        assert plan["sleep_phases"]["tmr"]["cue"] == "postgres"


class TestMechanismRegistered:
    def test_targeted_reactivation_in_enum(self):
        assert Mechanism.TARGETED_REACTIVATION.value == "targeted_reactivation"
