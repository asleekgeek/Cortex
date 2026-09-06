"""LRU coordination shared by scalar and batch encoding, without model imports.

Capacity belongs to EmbeddingEngine and remains unchanged pending measurement.
This mixin preserves input order, float32 byte blobs and provider-specific empty
batch values; it performs no normalization or model/device selection itself.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import OrderedDict


class _EmbeddingCacheMixin(ABC):
    _cache: OrderedDict[str, bytes]
    _cache_max: int
    _cache_hits: int
    _cache_misses: int
    _batch_reuses: int

    @staticmethod
    @abstractmethod
    def _cache_key(text: str) -> str:
        """Provided by the existing embedding math mixin (ADR-0045 R5)."""

    @abstractmethod
    def _encode_batch_uncached(self, texts: list[str]) -> list[bytes | None]:
        """Provided by the engine's unchanged neural/fallback implementation."""

    def encode_batch(self, texts: list[str]) -> list[bytes | None]:
        """Encode uncached texts together, preserving positions and byte format.

        Cache accesses are replayed in input order, including duplicates and
        batches larger than capacity. Empty text keeps the existing batch
        provider's behavior (neural bytes versus fallback None), never entering
        the scalar cache where encode("") must remain None.
        """
        if not texts:
            return []
        keys, available, pending = self._batch_cache_plan(texts)
        if pending:
            vectors = self._encode_batch_uncached(list(pending.values()))
            available.update(zip(pending, vectors, strict=True))
        result = []
        for text, key in zip(texts, keys, strict=True):
            vector = available[key]
            result.append(vector)
            if text and vector is not None:
                self._cache_store(key, vector)
        return result

    def _batch_cache_plan(self, texts: list[str]) -> tuple[list, dict, dict]:
        keys = [self._cache_key(text) for text in texts]
        available = {
            key: self._cache[key]
            for text, key in zip(texts, keys, strict=True)
            if text and key in self._cache
        }
        pending: dict[str, str] = {}
        for text, key in zip(texts, keys, strict=True):
            if text:
                self._cache_hits += key in available
                self._cache_misses += key not in available
                self._batch_reuses += key not in available and key in pending
            if key not in available:
                pending.setdefault(key, text)
        return keys, available, pending

    def _cache_store(self, key: str, vector: bytes) -> None:
        # source: Python's OrderedDict LRU recipe:
        # https://docs.python.org/3.13/library/collections.html#ordereddict-examples-and-recipes
        # Zero capacity is the no-cache control for the W3-4 measurement.
        if self._cache_max <= 0:
            return
        self._cache[key] = vector
        self._cache.move_to_end(key)
        if len(self._cache) > self._cache_max:
            self._cache.popitem(last=False)

    def cache_info(self) -> dict[str, int]:
        """Content-free cumulative observations; no capacity decision implied.

        Hits/misses count nonempty input positions, against the cache at entry
        to each call. batch_reuses counts duplicate misses coalesced within a
        batch; these are not persistent-cache hits. Failed lookups still count.
        """
        return {
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "batch_reuses": self._batch_reuses,
            "size": len(self._cache),
            "capacity": self._cache_max,
        }
