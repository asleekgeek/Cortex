"""Tests for mcp_server.core.lesson_promotion — pure classification and
job-building logic for the M-D6 (7.6) lesson-promotion pipeline.

Contract under test (from lesson_promotion.py):
  POST-1  classify_promotion_kind returns one of VALID_KINDS, never raises,
          for any string input including empty/None-like.
  POST-2  Recall/ranking keywords -> "rule".
  POST-3  Future-conditional keywords -> "trigger" (when no rule keyword
          also present — rule keywords take precedence).
  POST-4  No matching keyword -> "wiki" (documentary catch-all).
  POST-5  already_promoted is True iff at least one tag starts with
          "promoted:".
  POST-6  build_promotion_job never raises given the documented minimal
          shape (only "id" required) and includes suggested_kind.
  POST-7  build_promotion_jobs excludes already-promoted candidates and
          preserves order/count invariant len(result) <= len(candidates).
  POST-8  promotion_instructions returns a non-empty string mentioning
          the no-auto-promotion guarantee.
"""

from __future__ import annotations

from mcp_server.core.lesson_promotion import (
    VALID_KINDS,
    already_promoted,
    build_promotion_job,
    build_promotion_jobs,
    classify_promotion_kind,
    promotion_instructions,
)


class TestClassifyPromotionKind:
    def test_empty_string_returns_wiki(self):
        assert classify_promotion_kind("") == "wiki"

    def test_none_like_does_not_raise(self):
        assert classify_promotion_kind(None) in VALID_KINDS  # type: ignore[arg-type]

    def test_rule_keyword_recall(self):
        assert classify_promotion_kind("boost lessons in the recall pipeline") == "rule"

    def test_rule_keyword_deprecated(self):
        assert classify_promotion_kind("never surface deprecated memories") == "rule"

    def test_trigger_keyword_next_time(self):
        assert (
            classify_promotion_kind(
                "next time we touch the schema module, re-read the ADR"
            )
            == "trigger"
        )

    def test_trigger_keyword_reminder(self):
        assert classify_promotion_kind("reminder: push the release notes") == "trigger"

    def test_no_keyword_returns_wiki(self):
        assert (
            classify_promotion_kind("the checkout flow uses a transactional service")
            == "wiki"
        )

    def test_rule_keyword_takes_precedence_over_trigger_keyword(self):
        text = "next time, boost lessons tagged review in recall"
        assert classify_promotion_kind(text) == "rule"

    def test_result_always_in_valid_kinds(self):
        for text in ("", "recall boost", "next time reminder", "plain text", "🎉"):
            assert classify_promotion_kind(text) in VALID_KINDS


class TestAlreadyPromoted:
    def test_no_tags_returns_false(self):
        assert already_promoted([]) is False
        assert already_promoted(None) is False

    def test_unrelated_tags_returns_false(self):
        assert already_promoted(["lesson", "self-critique"]) is False

    def test_promoted_prefix_returns_true(self):
        assert already_promoted(["lesson", "promoted:rule"]) is True

    def test_promoted_wiki_returns_true(self):
        assert already_promoted(["promoted:wiki"]) is True

    def test_tag_containing_but_not_starting_with_promoted_is_false(self):
        assert already_promoted(["not-promoted:rule"]) is False


class TestBuildPromotionJob:
    def test_minimal_shape_does_not_raise(self):
        job = build_promotion_job({"id": 42})
        assert job["memory_id"] == 42
        assert job["suggested_kind"] in VALID_KINDS
        assert job["content"] == ""

    def test_uses_content_preview_when_present(self):
        job = build_promotion_job(
            {"id": 1, "content_preview": "boost lessons in recall"}
        )
        assert job["content"] == "boost lessons in recall"
        assert job["suggested_kind"] == "rule"

    def test_falls_back_to_content_when_no_preview(self):
        job = build_promotion_job({"id": 2, "content": "documentary note"})
        assert job["content"] == "documentary note"

    def test_carries_usage_evidence_fields(self):
        job = build_promotion_job(
            {
                "id": 3,
                "content_preview": "x",
                "useful_count": 4,
                "access_count": 9,
                "domain": "cortex",
                "tags": ["lesson"],
            }
        )
        assert job["useful_count"] == 4
        assert job["access_count"] == 9
        assert job["domain"] == "cortex"
        assert job["tags"] == ["lesson"]

    def test_defaults_evidence_to_zero_when_absent(self):
        job = build_promotion_job({"id": 4})
        assert job["useful_count"] == 0
        assert job["access_count"] == 0


class TestBuildPromotionJobs:
    def test_empty_candidates_returns_empty(self):
        assert build_promotion_jobs([]) == []

    def test_excludes_already_promoted_candidates(self):
        candidates = [
            {"id": 1, "content_preview": "a", "tags": ["lesson"]},
            {"id": 2, "content_preview": "b", "tags": ["lesson", "promoted:rule"]},
        ]
        jobs = build_promotion_jobs(candidates)
        assert [j["memory_id"] for j in jobs] == [1]

    def test_length_never_exceeds_candidate_count(self):
        candidates = [
            {"id": i, "tags": ["promoted:wiki"] if i % 2 == 0 else ["lesson"]}
            for i in range(10)
        ]
        jobs = build_promotion_jobs(candidates)
        assert len(jobs) <= len(candidates)
        assert len(jobs) == 5


class TestPromotionInstructions:
    def test_non_empty_string(self):
        text = promotion_instructions()
        assert isinstance(text, str)
        assert len(text) > 0

    def test_mentions_no_automatic_promotion(self):
        text = promotion_instructions().lower()
        assert "no promotion happens automatically" in text

    def test_mentions_source_memory_id_traceability(self):
        text = promotion_instructions()
        assert "source_memory_id" in text
