"""Tests for ADR-0051 STEP 4 typed harvest additions to core.wiki_staleness.

Covers:
  1. ``harvest_page_refs_typed`` — per-path provenance, claim wins over body.
  2. ``harvest_page_refs`` still returns the same sorted-union list it did
     before the typed refactor (behavior-preserving).
  3. ``normalize_typed_refs`` — canonicalization + merge-on-collision with
     claim_evidence winning regardless of iteration order.
"""

from __future__ import annotations

from mcp_server.core.wiki_staleness import (
    REF_SOURCE_BODY,
    REF_SOURCE_CLAIM_EVIDENCE,
    harvest_page_refs,
    harvest_page_refs_typed,
    normalize_typed_refs,
)


# ── harvest_page_refs_typed ──────────────────────────────────────────────


def test_typed_harvest_tags_claim_evidence() -> None:
    page = {"lead": "", "sections": {}}
    typed = harvest_page_refs_typed(page, ["mcp_server/core/foo.py"])
    assert typed == {"mcp_server/core/foo.py": REF_SOURCE_CLAIM_EVIDENCE}


def test_typed_harvest_tags_body_refs() -> None:
    page = {"lead": "See mcp_server/core/bar.py for details.", "sections": {}}
    typed = harvest_page_refs_typed(page, [])
    assert typed == {"mcp_server/core/bar.py": REF_SOURCE_BODY}


def test_typed_harvest_claim_wins_over_body_on_same_path() -> None:
    page = {"lead": "See mcp_server/core/baz.py.", "sections": {}}
    typed = harvest_page_refs_typed(page, ["mcp_server/core/baz.py"])
    assert typed == {"mcp_server/core/baz.py": REF_SOURCE_CLAIM_EVIDENCE}


def test_typed_harvest_scans_sections_dict() -> None:
    page = {"lead": "", "sections": {"details": "mcp_server/core/qux.py cited here"}}
    typed = harvest_page_refs_typed(page, [])
    assert typed == {"mcp_server/core/qux.py": REF_SOURCE_BODY}


def test_typed_harvest_scans_sections_list() -> None:
    page = {
        "lead": "",
        "sections": [{"body": "mcp_server/core/list_form.py referenced"}],
    }
    typed = harvest_page_refs_typed(page, [])
    assert typed == {"mcp_server/core/list_form.py": REF_SOURCE_BODY}


def test_typed_harvest_empty_page_no_claims_is_empty() -> None:
    assert harvest_page_refs_typed({"lead": "", "sections": {}}, []) == {}


# ── harvest_page_refs (behavior-preserving adapter) ──────────────────────


def test_harvest_page_refs_returns_sorted_union() -> None:
    page = {"lead": "mcp_server/core/a.py and mcp_server/core/c.py", "sections": {}}
    refs = harvest_page_refs(page, ["mcp_server/core/b.py"])
    assert refs == [
        "mcp_server/core/a.py",
        "mcp_server/core/b.py",
        "mcp_server/core/c.py",
    ]


def test_harvest_page_refs_dedupes_claim_and_body_overlap() -> None:
    page = {"lead": "mcp_server/core/dup.py", "sections": {}}
    refs = harvest_page_refs(page, ["mcp_server/core/dup.py"])
    assert refs == ["mcp_server/core/dup.py"]


# ── normalize_typed_refs ──────────────────────────────────────────────────


def test_normalize_typed_refs_canonicalizes_paths() -> None:
    typed = {"./mcp_server/core/a.py": REF_SOURCE_BODY}
    assert normalize_typed_refs(typed) == {"mcp_server/core/a.py": REF_SOURCE_BODY}


def test_normalize_typed_refs_merges_colliding_paths_claim_wins_body_first() -> None:
    # Iteration order: body entry inserted before the claim entry that
    # normalizes to the same canonical path.
    typed = {
        "./mcp_server/core/a.py": REF_SOURCE_BODY,
        "mcp_server/core/a.py": REF_SOURCE_CLAIM_EVIDENCE,
    }
    assert normalize_typed_refs(typed) == {
        "mcp_server/core/a.py": REF_SOURCE_CLAIM_EVIDENCE
    }


def test_normalize_typed_refs_merges_colliding_paths_claim_wins_claim_first() -> None:
    # Iteration order: claim entry inserted before the body entry that
    # normalizes to the same canonical path — claim must not be demoted.
    typed = {
        "mcp_server/core/a.py": REF_SOURCE_CLAIM_EVIDENCE,
        "./mcp_server/core/a.py": REF_SOURCE_BODY,
    }
    assert normalize_typed_refs(typed) == {
        "mcp_server/core/a.py": REF_SOURCE_CLAIM_EVIDENCE
    }


def test_normalize_typed_refs_drops_blank_paths() -> None:
    typed = {"": REF_SOURCE_BODY, "   ": REF_SOURCE_CLAIM_EVIDENCE}
    assert normalize_typed_refs(typed) == {}


def test_normalize_typed_refs_empty_input_is_empty() -> None:
    assert normalize_typed_refs({}) == {}
