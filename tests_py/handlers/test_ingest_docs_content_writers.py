"""Unit tests for ingest_docs_content_writers (INC5.3/D6) — fake store,
no live Postgres required (mirrors test_ingest_findings_writers.py's
pattern)."""

from __future__ import annotations

from pathlib import Path

from mcp_server.handlers.ingest_docs_content_writers import (
    MAX_DOC_BYTES,
    doc_tag,
    find_existing_doc_memory,
    read_doc_content,
    write_doc_memory,
    write_doc_reference_edge,
)


class _FakeStore:
    def __init__(
        self,
        existing_by_tag: dict[str, list[dict]] | None = None,
        entities_by_name: dict[str, dict] | None = None,
    ):
        self.memories: list[dict] = []
        self.relationships: list[dict] = []
        self._next = 9000
        self._existing_by_tag = existing_by_tag or {}
        self._entities_by_name = entities_by_name or {}

    def insert_memory(self, data: dict) -> int:
        mid = self._next
        self._next += 1
        self.memories.append({**data, "id": mid})
        return mid

    def get_memories_by_tag(self, tag: str, limit: int = 20) -> list[dict]:
        return self._existing_by_tag.get(tag, [])

    def get_entity_by_name(self, name: str) -> dict | None:
        return self._entities_by_name.get(name)

    def insert_relationship(self, data: dict) -> int:
        self.relationships.append(data)
        return len(self.relationships)


class TestDocTag:
    def test_deterministic_and_scoped_to_domain_and_path(self):
        assert doc_tag("code:proj", "docs/a.md") == "ap-doc:code:proj:docs/a.md"
        assert doc_tag("code:proj", "docs/a.md") != doc_tag("code:other", "docs/a.md")


class TestFindExistingDocMemory:
    def test_returns_none_when_no_prior_memory(self):
        store = _FakeStore()
        assert find_existing_doc_memory(store, "code:proj", "README.md") is None

    def test_returns_id_when_tag_present(self):
        tag = doc_tag("code:proj", "README.md")
        store = _FakeStore(existing_by_tag={tag: [{"id": 42, "tags": ["doc", tag]}]})
        assert find_existing_doc_memory(store, "code:proj", "README.md") == 42

    def test_degrades_to_none_when_store_lacks_tag_query(self):
        class _NoTagStore:
            pass

        assert find_existing_doc_memory(_NoTagStore(), "code:proj", "README.md") is None


class TestReadDocContent:
    def test_reads_utf8_content(self, tmp_path: Path):
        (tmp_path / "README.md").write_text("# Hello\n", encoding="utf-8")
        content = read_doc_content(tmp_path, "README.md")
        assert content == "# Hello\n"

    def test_missing_file_returns_none(self, tmp_path: Path):
        assert read_doc_content(tmp_path, "nope.md") is None

    def test_oversized_file_is_skipped_not_read(self, tmp_path: Path):
        big = tmp_path / "big.md"
        big.write_bytes(b"x" * (MAX_DOC_BYTES + 1))
        assert read_doc_content(tmp_path, "big.md") is None

    def test_file_exactly_at_cap_is_read(self, tmp_path: Path):
        exact = tmp_path / "exact.md"
        exact.write_bytes(b"x" * MAX_DOC_BYTES)
        assert read_doc_content(tmp_path, "exact.md") is not None

    def test_undecodable_bytes_return_none_not_raise(self, tmp_path: Path):
        bad = tmp_path / "bad.md"
        bad.write_bytes(b"\xff\xfe\x00\x01\x02")
        assert read_doc_content(tmp_path, "bad.md") is None


class TestWriteDocMemory:
    def test_writes_content_tagged_doc_and_src_ap(self):
        store = _FakeStore()
        mem_id, created = write_doc_memory(
            store, "code:proj", "/repo", "docs/a.md", "distinctive phrase here"
        )
        assert created is True
        record = store.memories[0]
        assert "doc" in record["tags"]
        assert "src:ap" in record["tags"]
        assert doc_tag("code:proj", "docs/a.md") in record["tags"]
        assert "distinctive phrase here" in record["content"]
        assert record["domain"] == "code:proj"
        assert record["directory_context"] == "/repo"
        assert record["is_protected"] is False

    def test_reingesting_same_doc_does_not_duplicate(self):
        tag = doc_tag("code:proj", "docs/a.md")
        store = _FakeStore(existing_by_tag={tag: [{"id": 555, "tags": ["doc", tag]}]})
        mem_id, created = write_doc_memory(
            store, "code:proj", "/repo", "docs/a.md", "content"
        )
        assert created is False
        assert mem_id == 555
        assert store.memories == []


class TestWriteDocReferenceEdge:
    def test_writes_edge_when_both_endpoints_exist(self):
        store = _FakeStore(
            entities_by_name={
                "docs/a.md": {"id": 1},
                "docs/b.md": {"id": 2},
            }
        )
        written = write_doc_reference_edge(store, "docs/a.md", "docs/b.md")
        assert written is True
        assert store.relationships[0]["source_entity_id"] == 1
        assert store.relationships[0]["target_entity_id"] == 2
        assert store.relationships[0]["relationship_type"] == "references"

    def test_missing_endpoint_drops_edge_silently(self):
        store = _FakeStore(entities_by_name={"docs/a.md": {"id": 1}})
        written = write_doc_reference_edge(store, "docs/a.md", "docs/missing.md")
        assert written is False
        assert store.relationships == []
