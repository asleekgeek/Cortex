"""Tests for ADR-0051 STEP 2 — the wiki page->source-file writer.

Covers:
  1. ``mcp_server.shared.wiki_source_paths.extract_document_paths`` reads
     each legacy frontmatter form (documents:/source_file_path:/file:/
     file:<path> tag) and canonicalizes them.
  2. ``wiki_migrate._page_row_from_md`` wires that extraction into the
     upsert_page payload (documents/documents_primary).
  3. ``pg_store_wiki_sources.upsert_page_sources`` is idempotent —
     calling it twice with the same documents yields the same rows.

The DB-touching idempotency test uses a mocked cursor (no live Postgres
required for the unit tier); the live integration proof against a real
throwaway database is run separately and reported in the task output.
"""

from __future__ import annotations

from unittest.mock import MagicMock, call

from mcp_server.handlers.wiki_migrate import _page_row_from_md
from mcp_server.infrastructure.pg_store_wiki_sources import upsert_page_sources
from mcp_server.shared.wiki_source_paths import (
    extract_document_paths,
    normalize_source_path,
)


# ── normalize_source_path ───────────────────────────────────────────────


def test_normalize_strips_leading_dot_slash() -> None:
    assert normalize_source_path("./src/foo.py") == "src/foo.py"


def test_normalize_converts_backslashes() -> None:
    assert normalize_source_path("src\\foo\\bar.py") == "src/foo/bar.py"


def test_normalize_strips_leading_slash() -> None:
    assert normalize_source_path("/src/foo.py") == "src/foo.py"


def test_normalize_blank_returns_none() -> None:
    assert normalize_source_path("") is None
    assert normalize_source_path("   ") is None


# ── extract_document_paths — legacy forms ───────────────────────────────


def test_extract_from_source_file_path_frontmatter() -> None:
    fm = {"source_file_path": "mcp_server/core/foo.py"}
    assert extract_document_paths(fm, []) == ["mcp_server/core/foo.py"]


def test_extract_from_file_field_frontmatter() -> None:
    fm = {"file": "mcp_server/core/bar.py"}
    assert extract_document_paths(fm, []) == ["mcp_server/core/bar.py"]


def test_extract_from_file_tag() -> None:
    fm: dict[str, object] = {}
    tags = ["reference", "file:mcp_server/core/baz.py", "lang:python"]
    assert extract_document_paths(fm, tags) == ["mcp_server/core/baz.py"]


def test_extract_from_documents_list() -> None:
    fm = {"documents": ["a/b.py", "a/c.py"]}
    assert extract_document_paths(fm, []) == ["a/b.py", "a/c.py"]


def test_extract_from_documents_scalar() -> None:
    fm = {"documents": "a/b.py"}
    assert extract_document_paths(fm, []) == ["a/b.py"]


def test_extract_dedupes_across_forms_preserving_order() -> None:
    fm = {"source_file_path": "a/b.py", "file": "a/b.py"}
    tags = ["file:a/b.py", "file:a/c.py"]
    assert extract_document_paths(fm, tags) == ["a/b.py", "a/c.py"]


def test_extract_canonicalizes_each_path() -> None:
    fm = {"source_file_path": "./a/b.py"}
    assert extract_document_paths(fm, []) == ["a/b.py"]


def test_extract_no_documented_files_returns_empty() -> None:
    assert extract_document_paths({}, ["unrelated"]) == []


# ── _page_row_from_md wiring ─────────────────────────────────────────────


def test_page_row_from_md_carries_documents_primary() -> None:
    content = (
        "---\n"
        "title: File: mcp_server/core/foo.py\n"
        "kind: reference\n"
        "domain: cortex\n"
        "source_file_path: mcp_server/core/foo.py\n"
        "tags:\n"
        "  - file\n"
        "---\n\n"
        "# foo.py\n"
    )
    row = _page_row_from_md("reference/cortex/1-foo-py.md", content)
    assert row["documents"] == ["mcp_server/core/foo.py"]
    assert row["documents_primary"] == "mcp_server/core/foo.py"


def test_page_row_from_md_no_documents_is_none() -> None:
    content = "---\ntitle: Some ADR\nkind: adr\ndomain: cortex\n---\n\nBody.\n"
    row = _page_row_from_md("adr/cortex/1-some-adr.md", content)
    assert row["documents"] == []
    assert row["documents_primary"] is None


def test_page_row_from_md_file_tag_form() -> None:
    content = (
        "---\n"
        "title: File: mcp_server/core/bar.py\n"
        "kind: file\n"
        "domain: cortex\n"
        "tags:\n"
        "  - file:mcp_server/core/bar.py\n"
        "---\n\n"
        "# bar.py\n"
    )
    row = _page_row_from_md("reference/cortex/2-bar-py.md", content)
    assert row["documents"] == ["mcp_server/core/bar.py"]
    assert row["documents_primary"] == "mcp_server/core/bar.py"


# ── upsert_page_sources idempotency (mocked cursor) ─────────────────────


def _mock_conn() -> MagicMock:
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    return conn


def test_upsert_page_sources_deletes_before_insert() -> None:
    conn = _mock_conn()
    cur = conn.cursor.return_value.__enter__.return_value

    upsert_page_sources(conn, page_id=1, documents=["a/b.py", "a/c.py"])

    delete_call = cur.execute.call_args_list[0]
    assert "DELETE FROM wiki.page_sources" in delete_call.args[0]
    assert delete_call.args[1] == (1, "documents")
    cur.executemany.assert_called_once()


def test_upsert_page_sources_empty_documents_only_deletes() -> None:
    conn = _mock_conn()
    cur = conn.cursor.return_value.__enter__.return_value

    result = upsert_page_sources(conn, page_id=1, documents=[])

    assert result == 0
    cur.execute.assert_called_once()
    cur.executemany.assert_not_called()


def test_upsert_page_sources_calling_twice_reissues_same_delete_and_insert() -> None:
    """Idempotency: two identical calls each delete-then-insert the same set."""
    conn = _mock_conn()
    cur = conn.cursor.return_value.__enter__.return_value

    upsert_page_sources(conn, page_id=1, documents=["a/b.py"])
    first_executemany_args = cur.executemany.call_args

    upsert_page_sources(conn, page_id=1, documents=["a/b.py"])
    second_executemany_args = cur.executemany.call_args

    assert first_executemany_args == second_executemany_args
    expected_delete = call(
        "DELETE FROM wiki.page_sources WHERE page_id = %s AND link_kind = %s",
        (1, "documents"),
    )
    assert cur.execute.call_args_list[0] == expected_delete
    assert cur.execute.call_args_list[1] == expected_delete
