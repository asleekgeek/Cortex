"""Embeddings observed once for consecutive stages of one recall request."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class EmbeddingReader(Protocol):
    def get_embeddings_for_memories(self, ids: list[int]) -> dict[int, bytes]: ...


@dataclass(frozen=True)
class MemoryEmbeddings:
    """A read-only snapshot; stage consumers retain their candidate order."""

    by_id: dict[int, bytes]

    @classmethod
    def read(cls, reader: EmbeddingReader, ids: list[int]) -> MemoryEmbeddings:
        return cls(reader.get_embeddings_for_memories(ids))

    def get_embeddings_for_memories(self, ids: list[int]) -> dict[int, bytes]:
        return {mid: self.by_id[mid] for mid in ids if mid in self.by_id}
