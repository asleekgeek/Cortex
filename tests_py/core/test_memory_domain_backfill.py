"""Tests for core.memory_domain_backfill — evidence-only domain
re-derivation for memories stuck with an empty domain (I6-D3)."""

from __future__ import annotations

from mcp_server.core.memory_domain_backfill import (
    DomainDerivation,
    derive_memory_domain,
)


def _directory_resolver(mapping: dict[str, str]):
    """Stub resolve_directory: raw cwd -> domain, '' if unknown."""
    return lambda directory: mapping.get(directory, "")


def _tag_resolver(mapping: dict[str, str]):
    """Stub resolve_project_tag: slug -> domain, '' if unknown."""
    return lambda slug: mapping.get(slug, "")


class TestDirectoryContextEvidence:
    """Source (a): directory_context resolves via injected resolve_directory."""

    def test_directory_context_resolves_to_domain(self):
        resolve_dir = _directory_resolver({"/Users/x/Developments/cortex": "cortex"})
        result = derive_memory_domain(
            "/Users/x/Developments/cortex",
            [],
            resolve_dir,
            _tag_resolver({}),
        )
        assert result == DomainDerivation("cortex", "directory_context")

    def test_directory_context_unresolved_falls_through_to_tag(self):
        resolve_dir = _directory_resolver({})  # nothing resolves
        resolve_tag = _tag_resolver({"my-slug": "cortex"})
        result = derive_memory_domain(
            "/tmp/not-a-known-repo",
            ["project:my-slug"],
            resolve_dir,
            resolve_tag,
        )
        assert result == DomainDerivation("cortex", "project_tag")

    def test_empty_directory_context_skips_directory_source(self):
        # An empty string must never be handed to resolve_directory —
        # the tag source should be tried directly.
        calls: list[str] = []

        def tracking_resolver(directory: str) -> str:
            calls.append(directory)
            return "should-not-be-used"

        result = derive_memory_domain(
            "",
            ["project:my-slug"],
            tracking_resolver,
            _tag_resolver({"my-slug": "cortex"}),
        )
        assert calls == []
        assert result == DomainDerivation("cortex", "project_tag")


class TestPriorityOrder:
    """directory_context evidence outranks project_tag evidence when both resolve."""

    def test_directory_context_wins_over_project_tag(self):
        resolve_dir = _directory_resolver({"/a/b": "cortex"})
        resolve_tag = _tag_resolver({"slug": "agentic-ai"})
        result = derive_memory_domain(
            "/a/b", ["project:slug"], resolve_dir, resolve_tag
        )
        assert result == DomainDerivation("cortex", "directory_context")


class TestProjectTagExtraction:
    def test_first_project_tag_wins(self):
        resolve_tag = _tag_resolver({"first-slug": "cortex", "second-slug": "other"})
        result = derive_memory_domain(
            "",
            ["auto-captured", "project:first-slug", "project:second-slug"],
            _directory_resolver({}),
            resolve_tag,
        )
        assert result == DomainDerivation("cortex", "project_tag")

    def test_non_project_tags_ignored(self):
        result = derive_memory_domain(
            "",
            ["auto-captured", "tool:bash", "error"],
            _directory_resolver({}),
            _tag_resolver({}),
        )
        assert result == DomainDerivation("", "")

    def test_project_tag_with_empty_slug_ignored(self):
        result = derive_memory_domain(
            "",
            ["project:"],
            _directory_resolver({}),
            _tag_resolver({"": "should-not-resolve"}),
        )
        assert result == DomainDerivation("", "")

    def test_non_string_tags_do_not_crash(self):
        result = derive_memory_domain(
            "",
            [123, None, "project:ok"],  # type: ignore[list-item]
            _directory_resolver({}),
            _tag_resolver({"ok": "cortex"}),
        )
        assert result == DomainDerivation("cortex", "project_tag")


class TestOrphan:
    """Neither source resolves -> orphan, never a fabricated guess."""

    def test_no_evidence_at_all_is_orphan(self):
        result = derive_memory_domain(
            "", [], _directory_resolver({}), _tag_resolver({})
        )
        assert result == DomainDerivation("", "")

    def test_directory_and_tag_both_unresolved_is_orphan(self):
        result = derive_memory_domain(
            "/unknown/path",
            ["project:unknown-slug"],
            _directory_resolver({}),
            _tag_resolver({}),
        )
        assert result == DomainDerivation("", "")
