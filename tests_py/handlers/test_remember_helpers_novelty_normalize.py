"""Tests for remember_helpers.compute_template_normalized_similarities
(i7d3 pivot, 2026-07-11) — the template-normalized re-scoring used ONLY
for the write gate's embedding-novelty signal. Never touches storage;
these tests use lightweight fakes (no DB, no real embedding model) to
keep the unit boundary pure and fast.
"""

from __future__ import annotations

from mcp_server.handlers.remember_helpers import (
    compute_template_normalized_similarities,
)


class FakeStore:
    """Minimal store double: get_memory(id) -> {"content": ...} | None."""

    def __init__(self, contents: dict[int, str]):
        self._contents = contents

    def get_memory(self, memory_id: int):
        if memory_id not in self._contents:
            return None
        return {"content": self._contents[memory_id]}


class FakeEmbEngine:
    """Deterministic fake: encode() returns a 1-hot-ish vector derived
    from the text so similarity() can be computed with plain equality
    semantics without loading a real model."""

    def encode(self, text: str):
        if not text:
            return None
        return text  # identity "vector" — good enough for similarity()

    def similarity(self, a, b) -> float:
        return 1.0 if a == b else 0.3


class TestSkipsNonTemplateContent:
    def test_returns_none_for_deliberate_content(self):
        store = FakeStore({})
        emb = FakeEmbEngine()
        result = compute_template_normalized_similarities(
            "Decided to use pgvector HNSW for ANN.", [], store, emb
        )
        assert result is None

    def test_returns_none_for_empty_vec_hits_but_template_content(self):
        store = FakeStore({})
        emb = FakeEmbEngine()
        result = compute_template_normalized_similarities(
            "# Tool: Read\n**Read:** `/a/b.py`", [], store, emb
        )
        assert result == []


class TestRescoresAutoCaptureContent:
    def test_normalizes_new_content_and_neighbor_before_similarity(self):
        store = FakeStore(
            {
                1: "# Tool: Read\n**Read:** `/a/b.py`",
                2: "# Tool: Read\n**Read:** `/c/d.py`",
            }
        )
        emb = FakeEmbEngine()
        new_content = "# Tool: Read\n**Read:** `/a/b.py`"
        result = compute_template_normalized_similarities(
            new_content, [(1, 0.1), (2, 0.2)], store, emb
        )
        assert result is not None
        assert len(result) == 2
        # Neighbor 1 has the SAME normalized payload as new_content ->
        # identity match under the fake similarity(); neighbor 2 differs.
        assert result[0] == 1.0
        assert result[1] == 0.3

    def test_derived_fact_content_is_also_rescored(self):
        store = FakeStore(
            {1: "Foo and Bar are strongly linked (depends_on, weight=10.0)"}
        )
        emb = FakeEmbEngine()
        new_content = "Foo and Bar are strongly linked (depends_on, weight=10.0)"
        result = compute_template_normalized_similarities(
            new_content, [(1, 0.1)], store, emb
        )
        assert result == [1.0]


class TestGracefulDegradation:
    def test_missing_neighbor_content_is_skipped_not_raised(self):
        store = FakeStore({1: "# Tool: Read\n**Read:** `/a/b.py`"})
        emb = FakeEmbEngine()
        new_content = "# Tool: Read\n**Read:** `/a/b.py`"
        # neighbor id 99 does not exist in the store
        result = compute_template_normalized_similarities(
            new_content, [(1, 0.1), (99, 0.5)], store, emb
        )
        assert result == [1.0]

    def test_encode_failure_on_new_content_returns_none(self):
        class DeadEmbEngine(FakeEmbEngine):
            def encode(self, text: str):
                return None

        store = FakeStore({1: "# Tool: Read\n**Read:** `/a/b.py`"})
        result = compute_template_normalized_similarities(
            "# Tool: Read\n**Read:** `/a/b.py`", [(1, 0.1)], store, DeadEmbEngine()
        )
        assert result is None


class TestNeverTouchesStorage:
    def test_store_has_no_write_methods_called(self):
        """FakeStore only implements get_memory — if the function under
        test tried to write anything, it would raise AttributeError."""
        store = FakeStore({1: "# Tool: Bash\n**Command:** `ls`"})
        emb = FakeEmbEngine()
        result = compute_template_normalized_similarities(
            "# Tool: Bash\n**Command:** `pwd`", [(1, 0.1)], store, emb
        )
        assert result is not None
