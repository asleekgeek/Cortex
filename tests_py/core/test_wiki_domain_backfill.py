"""Tests for core.wiki_domain_backfill — catch-all domain re-derivation
by majority vote over source paths."""

from __future__ import annotations

from mcp_server.core.wiki_domain_backfill import derive_page_domain


def _containing(mapping: dict[str, set[str]]):
    """Stub domains_containing: rel_path -> set of domains that own it."""
    return lambda rel_path: mapping.get(rel_path, set())


class TestSingleVote:
    def test_single_source_path_wins(self):
        mapping = {"mcp_server/core/foo.py": {"cortex"}}
        result = derive_page_domain(["mcp_server/core/foo.py"], _containing(mapping))
        assert result == "cortex"


class TestMajorityVote:
    def test_majority_domain_wins(self):
        mapping = {
            "mcp_server/core/foo.py": {"cortex"},
            "mcp_server/core/bar.py": {"cortex"},
            "src/other.py": {"automatised-pipeline"},
        }
        result = derive_page_domain(
            [
                "mcp_server/core/foo.py",
                "mcp_server/core/bar.py",
                "src/other.py",
            ],
            _containing(mapping),
        )
        assert result == "cortex"


class TestTieRefusal:
    def test_tied_vote_refuses_to_guess(self):
        mapping = {
            "mcp_server/core/foo.py": {"cortex"},
            "src/other.py": {"automatised-pipeline"},
        }
        result = derive_page_domain(
            ["mcp_server/core/foo.py", "src/other.py"],
            _containing(mapping),
        )
        assert result is None


class TestBasenameIgnored:
    def test_bare_basenames_are_ignored(self):
        mapping = {"foo.py": {"cortex"}}
        result = derive_page_domain(["foo.py"], _containing(mapping))
        assert result is None

    def test_mix_of_bare_and_slashed_uses_only_slashed(self):
        mapping = {"mcp_server/core/foo.py": {"cortex"}}
        result = derive_page_domain(
            ["foo.py", "mcp_server/core/foo.py"], _containing(mapping)
        )
        assert result == "cortex"


class TestNoVotes:
    def test_no_matching_domain_returns_none(self):
        result = derive_page_domain(
            ["mcp_server/core/foo.py"], _containing({})
        )
        assert result is None

    def test_empty_source_paths_returns_none(self):
        result = derive_page_domain([], _containing({}))
        assert result is None
