"""Consumer-side supersession skip in the sleep compute pass.

The decay cursor feeding run_sleep_compute_streamed must keep yielding
superseded physical rows (decay/forgetting/homeostatic cool them), so the
filter lives at the consumer boundary: a superseded row must reach neither
the replay heap nor the narration accumulators (decision 2026-07-07,
docs/program/pr2-read-path-supersession-audit.json).
"""

from __future__ import annotations

from mcp_server.core.sleep_compute import run_sleep_compute_streamed


def _mem(mid: int, content: str, heat: float, superseded_by=None) -> dict:
    return {
        "id": mid,
        "content": content,
        "heat": heat,
        "importance": heat,
        "superseded_by_id": superseded_by,
    }


def test_superseded_rows_skipped_from_replay_and_narration():
    # Contents ≥ 30 chars: _replay_updates_for skips shorter rows.
    chunks = [
        [
            _mem(
                1,
                "wrong retractedzorblax deployment target fact, old version",
                heat=0.9,
                superseded_by=2,
            ),
            _mem(
                2,
                "corrected zorblax deployment target fact, current version",
                heat=0.5,
            ),
            _mem(3, "unrelated background housekeeping fact here", heat=0.1),
        ]
    ]
    plan = run_sleep_compute_streamed(chunks, max_replay=10, max_reembed=10)

    replay_ids = [u["memory_id"] for u in plan["replay_updates"]]
    assert 1 not in replay_ids, "superseded row must not be replayed"
    assert 2 in replay_ids, "chain head must still be replayed"

    narrative = plan["narration"].get("narrative_text", "")
    assert "retractedzorblax" not in narrative, (
        "superseded content must not fold into the auto-narration"
    )
    assert plan["narration"].get("memory_count") == 2, (
        "superseded row must not be counted in the narration"
    )


def test_no_edges_is_identity():
    """Benchmark-neutrality: with no superseded rows the pass is unchanged."""
    chunks = [
        [
            _mem(i, f"fact number {i} with enough content to be replayable", i / 10)
            for i in range(1, 6)
        ]
    ]
    plan = run_sleep_compute_streamed(chunks, max_replay=3)
    assert len(plan["replay_updates"]) == 3
    assert plan["narration"].get("memory_count") == 5
