"""Unit tests for ingest_docs_content_cypher (INC5.3/D6) — fake upstream
MCP client, mirrors ingest_codebase_cypher's own test patterns."""

from __future__ import annotations

import re

import pytest

from mcp_server.errors import McpConnectionError
from mcp_server.handlers import ingest_docs_content_cypher as cyp


@pytest.mark.asyncio
class TestFetchDocFiles:
    async def test_filters_to_markdown_family_extensions(self, monkeypatch):
        seen_queries: list[str] = []

        async def _call(server, tool, args):
            seen_queries.append(args["query"])
            return {
                "columns": ["path", "name", "extension", "size_bytes"],
                "rows": [
                    ["docs/a.md", "a.md", "md", 100],
                    ["docs/b.markdown", "b.markdown", "markdown", 50],
                ],
                "truncated": False,
            }

        monkeypatch.setattr(cyp, "call_upstream", _call)
        files, diag = await cyp.fetch_doc_files("/g")
        assert diag == []
        assert {f["path"] for f in files} == {"docs/a.md", "docs/b.markdown"}
        assert "extension IN ['md', 'markdown', 'mdx']" in seen_queries[0]

    async def test_pages_past_injected_limit(self, monkeypatch):
        total = 733

        async def _call(server, tool, args):
            q = args["query"]
            skip = int(re.search(r"SKIP (\d+)", q).group(1))
            limit = int(re.search(r"LIMIT (\d+)", q).group(1))
            n = max(0, min(limit, total - skip))
            rows = [[f"docs/f{skip + i}.md", "n", "md", 1] for i in range(n)]
            return {
                "rows": rows,
                "columns": ["path", "name", "extension", "size_bytes"],
                "truncated": False,
            }

        monkeypatch.setattr(cyp, "call_upstream", _call)
        files, diag = await cyp.fetch_doc_files("/g")
        assert diag == []
        assert len(files) == total
        assert files[0]["path"] == "docs/f0.md"
        assert files[-1]["path"] == "docs/f732.md"

    async def test_transport_error_yields_diagnostic_not_exception(self, monkeypatch):
        async def _boom(server, tool, args):
            raise McpConnectionError("upstream down")

        monkeypatch.setattr(cyp, "call_upstream", _boom)
        files, diag = await cyp.fetch_doc_files("/g")
        assert files == []
        assert diag and "doc-files" in diag[0]


@pytest.mark.asyncio
class TestFetchDocReferences:
    async def test_returns_empty_without_calling_upstream_when_no_known_docs(
        self, monkeypatch
    ):
        called = False

        async def _call(server, tool, args):
            nonlocal called
            called = True
            return {}

        monkeypatch.setattr(cyp, "call_upstream", _call)
        refs, diag = await cyp.fetch_doc_references("/g", set())
        assert refs == []
        assert diag == []
        assert called is False

    async def test_keeps_edges_whose_source_is_a_known_doc(self, monkeypatch):
        async def _call(server, tool, args):
            return {
                "columns": ["src", "dst"],
                "rows": [
                    ["docs/guide.md", "src/mod.py"],  # doc -> code, kept
                    ["docs/guide.md", "docs/arch.md"],  # doc -> doc, kept
                    ["src/other.py", "docs/guide.md"],  # code -> doc, dropped
                ],
                "truncated": False,
            }

        monkeypatch.setattr(cyp, "call_upstream", _call)
        refs, diag = await cyp.fetch_doc_references("/g", {"docs/guide.md"})
        assert diag == []
        assert set(refs) == {
            ("docs/guide.md", "src/mod.py"),
            ("docs/guide.md", "docs/arch.md"),
        }

    async def test_dedups_repeated_pairs(self, monkeypatch):
        async def _call(server, tool, args):
            return {
                "columns": ["src", "dst"],
                "rows": [
                    ["docs/a.md", "docs/b.md"],
                    ["docs/a.md", "docs/b.md"],
                ],
                "truncated": False,
            }

        monkeypatch.setattr(cyp, "call_upstream", _call)
        refs, diag = await cyp.fetch_doc_references("/g", {"docs/a.md"})
        assert refs == [("docs/a.md", "docs/b.md")]

    async def test_drops_self_edges(self, monkeypatch):
        async def _call(server, tool, args):
            return {
                "columns": ["src", "dst"],
                "rows": [["docs/a.md", "docs/a.md"]],
                "truncated": False,
            }

        monkeypatch.setattr(cyp, "call_upstream", _call)
        refs, diag = await cyp.fetch_doc_references("/g", {"docs/a.md"})
        assert refs == []
