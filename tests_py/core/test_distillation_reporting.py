"""Tests for core.distillation_reporting (INC7.8/M-D8) — prompt text and
the memify_derive usage snapshot. Pure functions, no I/O.
"""

from __future__ import annotations

from mcp_server.core.distillation import DistillDossier
from mcp_server.core.distillation_reporting import (
    build_distill_prompt,
    summarize_derived_usage,
)


class TestBuildDistillPrompt:
    def _dossier(self) -> DistillDossier:
        return DistillDossier(
            kind="error_success",
            topic="write_gate",
            domain="cortex",
            memory_ids=[1, 2],
        )

    def test_names_required_call_shape(self):
        prompt = build_distill_prompt(
            self._dossier(),
            [
                {"id": 1, "content": "error content", "tags": ["error"]},
                {"id": 2, "content": "success content", "tags": ["success"]},
            ],
        )
        assert "write_class='deliberate'" in prompt
        assert "'lesson'" in prompt
        assert "'derived-src:1'" in prompt
        assert "'derived-src:2'" in prompt
        assert self._dossier().marker in prompt

    def test_includes_source_previews(self):
        prompt = build_distill_prompt(
            self._dossier(),
            [{"id": 1, "content": "the actual error text", "tags": []}],
        )
        assert "the actual error text" in prompt

    def test_never_mentions_derived_write_class(self):
        # M-D8 point 2: distilled lessons are write_class='deliberate',
        # never 'derived' — that stays reserved for memify_derive.
        prompt = build_distill_prompt(self._dossier(), [])
        assert "write_class='derived'" not in prompt


class TestSummarizeDerivedUsage:
    def test_empty_list(self):
        result = summarize_derived_usage([])
        assert result == {
            "count": 0,
            "total_access_count": 0,
            "total_useful_count": 0,
            "mean_useful_ratio": None,
        }

    def test_aggregates_counts(self):
        mems = [
            {"access_count": 4, "useful_count": 2},
            {"access_count": 6, "useful_count": 1},
        ]
        result = summarize_derived_usage(mems)
        assert result["count"] == 2
        assert result["total_access_count"] == 10
        assert result["total_useful_count"] == 3
        assert abs(result["mean_useful_ratio"] - 0.3) < 1e-9

    def test_zero_access_zero_ratio_not_divide_by_zero(self):
        mems = [{"access_count": 0, "useful_count": 0}]
        result = summarize_derived_usage(mems)
        assert result["mean_useful_ratio"] == 0.0

    def test_missing_fields_default_to_zero(self):
        result = summarize_derived_usage([{}])
        assert result["total_access_count"] == 0
        assert result["total_useful_count"] == 0
