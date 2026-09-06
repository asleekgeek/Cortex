"""A request-local view of complete memory rows, without further store reads."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class MemoryReader(Protocol):
    def get_memory(self, memory_id: int) -> dict[str, Any] | None: ...


class MemoryBatchReader(Protocol):
    def get_memories_by_ids(
        self, memory_ids: list[int]
    ) -> dict[int, dict[str, Any]]: ...


@dataclass(frozen=True)
class MemoryRows:
    """Rows observed once; consumers retain their own candidate order."""

    by_id: dict[int, dict[str, Any]]

    @classmethod
    def read(cls, store: MemoryBatchReader, memory_ids: list[int]) -> MemoryRows:
        return cls(store.get_memories_by_ids(memory_ids))

    def get_memory(self, memory_id: int) -> dict[str, Any] | None:
        return self.by_id.get(memory_id)
