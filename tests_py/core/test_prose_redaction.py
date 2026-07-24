"""Tests for core/prose_redaction.py — the native AI-writing-tell inventory (issue #166)."""

from __future__ import annotations

from mcp_server.core.prose_redaction import (
    CATEGORY_BANNED_WORD,
    CATEGORY_EM_DASH,
    CATEGORY_ING_TACKON,
    CATEGORY_WEASEL,
    REDACTION_CONVENTIONS,
    scan_prose,
    summarize_findings,
)


class TestScanProse:
    def test_clean_technical_prose_yields_no_findings(self):
        text = (
            "The recall path fuses vector, FTS, and trigram signals.\n"
            "p50 latency is 125ms, measured in benchmarks/longmemeval "
            "(2026-04 run).\n"
        )
        assert scan_prose(text) == []

    def test_em_dash_flagged_with_line_number(self):
        findings = scan_prose("First line is fine.\nThe store is fast — very fast.")
        assert len(findings) == 1
        f = findings[0]
        assert f.category == CATEGORY_EM_DASH
        assert f.line == 2

    def test_banned_vocabulary_flagged(self):
        findings = scan_prose("We leverage a transformative pipeline.")
        cats = [f.category for f in findings]
        assert cats.count(CATEGORY_BANNED_WORD) >= 1

    def test_weasel_attribution_flagged(self):
        findings = scan_prose("Studies show this approach wins.")
        assert [f.category for f in findings] == [CATEGORY_WEASEL]

    def test_ing_tackon_flagged(self):
        text = "The launch adds file search, highlighting the team's commitment."
        findings = scan_prose(text)
        assert [f.category for f in findings] == [CATEGORY_ING_TACKON]

    def test_plain_participle_clause_not_flagged(self):
        # An -ing verb outside the tack-on set must not fire (false-positive guard).
        assert scan_prose("The worker keeps polling, retrying on timeouts.") == []

    def test_fenced_code_blocks_skipped(self):
        text = (
            "Real prose line.\n```\nx = 'studies show — leverage'\n```\nMore prose.\n"
        )
        assert scan_prose(text) == []

    def test_frontmatter_is_scanned(self):
        # Titles/descriptions are reader-facing; the fence regex must not
        # treat YAML '---' as a code fence.
        text = "---\ntitle: A transformative journey\n---\nBody.\n"
        findings = scan_prose(text)
        assert [f.category for f in findings] == [CATEGORY_BANNED_WORD]

    def test_excerpt_bounded(self):
        long_line = "delve " + "x" * 300
        (finding,) = scan_prose(long_line)
        assert len(finding.excerpt) <= 80


class TestSummarizeFindings:
    def test_summary_shape_and_cap(self):
        text = "\n".join("We delve deeper — again." for _ in range(15))
        summary = summarize_findings(scan_prose(text), cap=10)
        assert summary["count"] == 30  # em dash + banned word per line
        assert summary["by_category"][CATEGORY_EM_DASH] == 15
        assert summary["by_category"][CATEGORY_BANNED_WORD] == 15
        assert len(summary["first"]) == 10
        first = summary["first"][0]
        assert set(first) == {"line", "category", "match", "excerpt"}

    def test_empty_findings_summary(self):
        summary = summarize_findings([])
        assert summary == {"count": 0, "by_category": {}, "first": []}


class TestPromptIntegration:
    def test_conventions_block_is_nonempty_and_em_dash_free(self):
        assert "No em dashes" in REDACTION_CONVENTIONS
        assert "—" not in REDACTION_CONVENTIONS

    def test_authoring_prompts_carry_the_conventions(self):
        from mcp_server.core import auto_curator

        for name in (
            "WIKI_AUTHORING_PROMPT",
            "WIKI_COVERAGE_PROMPT",
            "WIKI_REAUTHOR_PROMPT",
        ):
            template = getattr(auto_curator, name)
            assert "{redaction_conventions}" in template, name
