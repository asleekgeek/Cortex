"""Deterministic float32 fixtures; never construct a neural model or a DB."""

from __future__ import annotations

from unittest.mock import Mock

import numpy as np

from mcp_server.infrastructure.embedding_engine import EmbeddingEngine
from tests_py.handlers._preflight_fakes import Store


class FixedModel:
    def __init__(self, vectors):
        self.vectors = vectors

    def encode(self, texts):
        if isinstance(texts, str):
            return np.asarray(self.vectors[texts], dtype=np.float64)
        return np.asarray([self.vectors[text] for text in texts], dtype=np.float64)


def make_engine(vectors):
    # Three dimensions are fixture geometry, not a production model setting.
    engine = EmbeddingEngine(dim=3)
    engine._model = FixedModel(vectors)
    engine._ensure_model = Mock()
    engine.encode = Mock(wraps=engine.encode)
    engine.encode_batch = Mock(wraps=engine.encode_batch)
    return engine


def blob(vector):
    return np.asarray(vector, dtype=np.float32).tobytes()


class BatchStore(Store):
    def __init__(self, content, rows):
        super().__init__(content, known=False)
        self.rows = rows
        self.searches = []
        self.update_memory_compression = Mock()
        self.update_memory_heat = Mock()

    def get_memory(self, memory_id):
        return self.rows.get(memory_id)

    def get_memories_by_ids(self, memory_ids):
        return {mid: self.rows[mid] for mid in memory_ids if mid in self.rows}

    def search_vectors(self, embedding, **kwargs):
        self.searches.append((embedding, kwargs))
        return [(mid, 0.0) for mid in self.rows][: kwargs["top_k"]]
