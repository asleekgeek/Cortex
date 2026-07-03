"""C1 read-side / enforcement wiring tests (source / reality monitoring).

Covers the HELD C1 read-side steps now wired:

  1. Recall-side surfacing — ``source_attribution`` flows through the
     recall_memories() projection into each recall hit, and each hit is
     annotated with a per-hit ``confabulation_risk`` flag
     (recall_helpers.annotate_source_attribution). ADDITIVE: order and
     membership of the result list are unchanged.
  2. Confabulation-gate call site — the gate fires at the episodic->semantic
     PROMOTION point (consolidation_engine), flagging a cluster that would be
     crystallized as a semantic FACT while its combined evidence is INFERRED
     with zero perceptual grounding. Non-fatal: the promotion is still emitted,
     tagged 'confabulation-risk'.
  3. Ablation guard — CORTEX_ABLATE_CONFABULATION_GATE=1 disables both the
     promotion flag and the recall confabulation_risk annotation, with no change
     to recall ordering/membership either way.

Pure business-logic + sqlite-store paths only (no Postgres, no fastmcp).
"""

from __future__ import annotations

import os


from mcp_server.core import consolidation_engine as ce
from mcp_server.core import source_monitoring as sm
from mcp_server.handlers.recall_helpers import annotate_source_attribution


# ── Unit: the two gate helpers ──────────────────────────────────────────────
class TestPromotionGate:
    def test_inferred_ungrounded_cluster_is_risk(self):
        cluster = [
            {"content": "I think the retry logic is probably flaky"},
            {"content": "It seems like the cache maybe expires too early"},
            {"content": "This suggests the timeout is likely wrong"},
        ]
        assert sm.promotion_confabulation_risk(cluster) is True

    def test_grounded_cluster_is_not_risk(self):
        cluster = [
            {"content": "The retry logic is in retry.py line 40"},
            {"content": "See https://example.com/docs for the cache TTL"},
        ]
        assert sm.promotion_confabulation_risk(cluster) is False

    def test_told_cluster_is_not_risk(self):
        cluster = [{"content": "You asked me to keep the reranker alpha at 0.70"}]
        assert sm.promotion_confabulation_risk(cluster) is False

    def test_empty_cluster_is_not_risk(self):
        assert sm.promotion_confabulation_risk([]) is False


class TestRecallRiskHelper:
    def test_perceived_claim_inferred_content_is_risk(self):
        assert (
            sm.recall_confabulation_risk("I think it probably seems wrong", "perceived")
            is True
        )

    def test_inferred_claim_never_flagged(self):
        # A memory stored as inferred makes no external-grounding promise.
        assert (
            sm.recall_confabulation_risk("I think it probably seems wrong", "inferred")
            is False
        )

    def test_perceived_claim_with_grounding_not_flagged(self):
        assert (
            sm.recall_confabulation_risk("defined in foo.py line 10", "perceived")
            is False
        )

    def test_unknown_claim_never_flagged(self):
        assert sm.recall_confabulation_risk("anything at all", "unknown") is False


# ── Wiring: recall-side surfacing on result dicts ───────────────────────────
def _results():
    # Mimic the recall projection output (pg_store dict(r)) with source_attribution.
    return [
        {
            "memory_id": 1,
            "content": "I think this probably seems wrong somehow",
            "score": 0.9,
            "source_attribution": "perceived",  # claims observed, but inferred content
        },
        {
            "memory_id": 2,
            "content": "The parser lives in parser.py line 12",
            "score": 0.8,
            "source_attribution": "perceived",  # legitimately grounded
        },
        {
            "memory_id": 3,
            "content": "I guess maybe it could be slow",
            "score": 0.7,
            "source_attribution": "inferred",  # makes no observed claim
        },
    ]


class TestRecallSurfacing:
    def test_attribution_and_risk_annotated(self):
        results = _results()
        annotate_source_attribution(results)
        # attribution passthrough
        assert [r["source_attribution"] for r in results] == [
            "perceived",
            "perceived",
            "inferred",
        ]
        # only the perceived-but-inferred hit is flagged
        assert [r["confabulation_risk"] for r in results] == [True, False, False]

    def test_additive_no_reorder_no_drop(self):
        results = _results()
        before_ids = [r["memory_id"] for r in results]
        before_scores = [r["score"] for r in results]
        annotate_source_attribution(results)
        after_ids = [r["memory_id"] for r in results]
        after_scores = [r["score"] for r in results]
        assert after_ids == before_ids  # membership + order unchanged
        assert after_scores == before_scores  # scores untouched
        assert len(results) == 3

    def test_missing_attribution_defaults_unknown(self):
        results = [{"memory_id": 9, "content": "plain", "score": 0.5}]
        annotate_source_attribution(results)
        assert results[0]["source_attribution"] == "unknown"
        assert results[0]["confabulation_risk"] is False

    def test_ablation_disables_risk_but_keeps_attribution(self):
        os.environ["CORTEX_ABLATE_CONFABULATION_GATE"] = "1"
        try:
            results = _results()
            annotate_source_attribution(results)
            # attribution still surfaced (pure provenance passthrough)
            assert [r["source_attribution"] for r in results] == [
                "perceived",
                "perceived",
                "inferred",
            ]
            # but the gate contributes nothing
            assert all(r["confabulation_risk"] is False for r in results)
        finally:
            del os.environ["CORTEX_ABLATE_CONFABULATION_GATE"]


# ── Wiring: consolidation-promotion gate fires at the crystallization point ──
def _cluster(contents):
    return {
        "memories": [{"content": c, "tags": []} for c in contents],
        "memory_ids": list(range(len(contents))),
        "count": len(contents),
        "session_count": 2,
    }


class TestConsolidationGate:
    def test_inferred_promotion_flagged_not_dropped(self):
        pattern = _cluster(
            [
                "I think the module is probably broken",
                "It seems the flow maybe loops forever",
                "This suggests the guard is likely missing",
            ]
        )
        result = ce._try_abstract_pattern(
            pattern,
            existing_semantics=[],
            similarity_fn=lambda a, b: 0.0,
            dedup_threshold=0.85,
        )
        # STILL abstracted (non-fatal) AND flagged.
        assert result is not None
        assert result["confabulation_risk"] is True

    def test_grounded_promotion_not_flagged(self):
        pattern = _cluster(
            [
                "The handler is defined in handler.py line 22",
                "The config is read from config.yaml",
            ]
        )
        result = ce._try_abstract_pattern(
            pattern,
            existing_semantics=[],
            similarity_fn=lambda a, b: 0.0,
            dedup_threshold=0.85,
        )
        assert result is not None
        assert result["confabulation_risk"] is False

    def test_process_patterns_counts_risky_promotions(self):
        patterns = [
            _cluster(
                [
                    "I think A is probably B",
                    "It seems A maybe equals B",
                    "This suggests A is likely B",
                ]
            ),
            _cluster(
                [
                    "X is in x.py line 1",
                    "Y is in y.py line 2",
                ]
            ),
        ]
        plan = ce._process_patterns(
            patterns,
            existing_semantics=[],
            similarity_fn=lambda a, b: 0.0,
            dedup_threshold=0.85,
        )
        # both abstractions emitted (nothing dropped by the gate)
        assert len(plan["new_semantics"]) == 2
        # exactly one flagged
        assert plan["confabulation_risk_promotions"] == 1

    def test_ablation_disables_promotion_flag(self):
        os.environ["CORTEX_ABLATE_CONFABULATION_GATE"] = "1"
        try:
            pattern = _cluster(
                [
                    "I think the module is probably broken",
                    "It seems the flow maybe loops forever",
                    "This suggests the guard is likely missing",
                ]
            )
            result = ce._try_abstract_pattern(
                pattern,
                existing_semantics=[],
                similarity_fn=lambda a, b: 0.0,
                dedup_threshold=0.85,
            )
            # same abstraction is still produced, but never flagged when ablated
            assert result is not None
            assert result["confabulation_risk"] is False
        finally:
            del os.environ["CORTEX_ABLATE_CONFABULATION_GATE"]

    def test_ablation_zeroes_process_patterns_count(self):
        os.environ["CORTEX_ABLATE_CONFABULATION_GATE"] = "1"
        try:
            patterns = [
                _cluster(
                    [
                        "I think A is probably B",
                        "It seems A maybe equals B",
                        "This suggests A is likely B",
                    ]
                )
            ]
            plan = ce._process_patterns(
                patterns,
                existing_semantics=[],
                similarity_fn=lambda a, b: 0.0,
                dedup_threshold=0.85,
            )
            assert len(plan["new_semantics"]) == 1  # membership unchanged
            assert plan["confabulation_risk_promotions"] == 0
        finally:
            del os.environ["CORTEX_ABLATE_CONFABULATION_GATE"]
