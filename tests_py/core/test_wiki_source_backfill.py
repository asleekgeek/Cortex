"""Tests for core.wiki_source_backfill — primary source derivation
(ADR-0051 STEP 3)."""

from __future__ import annotations

from mcp_server.core.wiki_source_backfill import (
    SOURCE_BODY,
    SOURCE_CLAIM_EVIDENCE,
    SOURCE_CODEBASE_GROUNDING,
    derive_primary_source,
)


def _exists_only(*paths: str):
    allowed = set(paths)
    return lambda p: p in allowed


class TestClaimEvidence:
    def test_single_claim_file_wins(self):
        page = {"rel_path": "reference/cortex/foo.md", "domain": "cortex"}
        result = derive_primary_source(page, ["mcp_server/core/foo.py"], _exists_only())
        assert result == ("mcp_server/core/foo.py", SOURCE_CLAIM_EVIDENCE)

    def test_multiple_distinct_claim_files_refuse_to_guess(self):
        page = {"rel_path": "reference/cortex/foo.md", "domain": "cortex"}
        result = derive_primary_source(
            page,
            ["mcp_server/core/foo.py", "mcp_server/core/bar.py"],
            _exists_only("mcp_server/core/foo.py", "mcp_server/core/bar.py"),
        )
        assert result is None

    def test_duplicate_claim_files_after_normalization_collapse_to_one(self):
        page = {"rel_path": "reference/cortex/foo.md", "domain": "cortex"}
        result = derive_primary_source(
            page,
            ["./mcp_server/core/foo.py", "mcp_server/core/foo.py"],
            _exists_only(),
        )
        assert result == ("mcp_server/core/foo.py", SOURCE_CLAIM_EVIDENCE)


class TestCodebaseGrounding:
    def test_slug_reversed_and_grounded(self):
        page = {"rel_path": "reference/cortex/mcp_server-core-foo.py.md", "domain": "cortex"}
        result = derive_primary_source(
            page, [], _exists_only("mcp_server/core/foo.py")
        )
        assert result == ("mcp_server/core/foo.py", SOURCE_CODEBASE_GROUNDING)

    def test_refuses_to_fabricate_when_guess_does_not_exist(self):
        """Anti-fabrication: a plausible-looking guess that doesn't
        resolve to a real file must never be accepted."""
        page = {"rel_path": "reference/cortex/mcp_server-core-foo.py.md", "domain": "cortex"}
        result = derive_primary_source(page, [], _exists_only())
        assert result is None


class TestBodyCitation:
    def test_single_groundable_citation_in_lead(self):
        page = {
            "rel_path": "reference/cortex/some-note.md",
            "domain": "cortex",
            "lead": "Implemented in `mcp_server/core/foo.py`.",
            "sections": {},
        }
        result = derive_primary_source(page, [], _exists_only("mcp_server/core/foo.py"))
        assert result == ("mcp_server/core/foo.py", SOURCE_BODY)

    def test_single_groundable_citation_in_sections(self):
        page = {
            "rel_path": "reference/cortex/some-note.md",
            "domain": "cortex",
            "lead": "",
            "sections": {"Notes": "See `mcp_server/core/foo.py` for details."},
        }
        result = derive_primary_source(page, [], _exists_only("mcp_server/core/foo.py"))
        assert result == ("mcp_server/core/foo.py", SOURCE_BODY)

    def test_multiple_groundable_citations_refuse_to_guess(self):
        page = {
            "rel_path": "reference/cortex/some-note.md",
            "domain": "cortex",
            "lead": "See `mcp_server/core/foo.py` and `mcp_server/core/bar.py`.",
            "sections": {},
        }
        result = derive_primary_source(
            page,
            [],
            _exists_only("mcp_server/core/foo.py", "mcp_server/core/bar.py"),
        )
        assert result is None

    def test_ungroundable_citation_is_ignored(self):
        page = {
            "rel_path": "reference/cortex/some-note.md",
            "domain": "cortex",
            "lead": "See `mcp_server/core/ghost.py`.",
            "sections": {},
        }
        result = derive_primary_source(page, [], _exists_only())
        assert result is None


class TestPriorityOrder:
    def test_claim_evidence_wins_over_body_citation(self):
        page = {
            "rel_path": "reference/cortex/some-note.md",
            "domain": "cortex",
            "lead": "See `mcp_server/core/bar.py`.",
            "sections": {},
        }
        result = derive_primary_source(
            page,
            ["mcp_server/core/foo.py"],
            _exists_only("mcp_server/core/bar.py"),
        )
        assert result == ("mcp_server/core/foo.py", SOURCE_CLAIM_EVIDENCE)

    def test_no_candidate_anywhere_returns_none(self):
        page = {"rel_path": "reference/cortex/some-note.md", "domain": "cortex"}
        result = derive_primary_source(page, [], _exists_only())
        assert result is None
