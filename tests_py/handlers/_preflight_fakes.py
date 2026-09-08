"""Fixed observations for preflight equivalence tests; no DB or model."""

from __future__ import annotations

from collections import Counter


class Store:
    def __init__(self, content="steady observation", repeats=0, known=True):
        self.content, self.repeats, self.known = content, repeats, known
        self.calls = Counter()
        self.triggers = []

    def search_vectors(self, embedding, **kwargs):
        self.calls["search_vectors"] += 1
        return [(1, 0.0)]

    def get_memory(self, memory_id):
        self.calls["get_memory"] += 1
        return {
            "content": self.content,
            "embedding": b"neighbor",
            "created_at": "2026-09-06T00:00:00+00:00",
        }

    def get_entity_by_name(self, name):
        self.calls["get_entity_by_name"] += 1
        return {"name": name} if self.known else None

    def get_hot_memories(self, **kwargs):
        self.calls["get_hot_memories"] += 1
        return [{"content": self.content}]

    def signature_repeat_stats(self, signature):
        self.calls["signature_repeat_stats"] += 1
        return self.repeats, 0.0

    def get_active_prospective_memories(self):
        self.calls["get_active_prospective_memories"] += 1
        return self.triggers


class Engine:
    def __init__(self, similarity=1.0):
        self.similarity_score = similarity
        self.encoded = []

    def encode(self, content):
        self.encoded.append(content)
        return b"raw:" + content.encode()

    def similarity(self, first, second):
        return self.similarity_score
