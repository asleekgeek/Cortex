"""Download-free algorithmic embedding provider (issue #169).

The SECOND ``EmbeddingProvider`` implementation (the first is the neural
``EmbeddingEngine``). It produces deterministic vectors with no model download,
no network, and no learned parameters — only arithmetic seeded by the token
strings — in the SAME dimension contract as the neural encoder. Used whenever
the neural model is not loadable (``ModelState`` PACKAGE_ABSENT /
MODEL_FILES_ABSENT / LOAD_RAISED); the factory maps those states here.

The vectors live in a DIFFERENT geometry from the neural space, so the store
tags each stored vector with the producing provider and never cross-ranks the
two (see ``sqlite_store``). Pure delegation to
``shared.algorithmic_embedding`` — see that module for the signal selection
(TF + Random Indexing + co-occurrence bridging) and its sources.
"""

from __future__ import annotations

import numpy as np

from mcp_server.infrastructure.embedding_provider import _EmbeddingMathMixin
from mcp_server.shared.algorithmic_embedding import embed_text


class AlgorithmicEmbeddingProvider(_EmbeddingMathMixin):
    """Deterministic, download-free ``EmbeddingProvider`` implementation.

    Stateless apart from its fixed dimension; safe to share across threads
    (``embed_text`` allocates its own arrays). Inherits the shared vector math
    (``similarity`` / ``to_list`` / ``from_list`` / ``_normalize`` / ``_cache_key``)
    so it satisfies the provider surface identically to the neural engine.
    """

    def __init__(self, dim: int) -> None:
        self._dim = dim

    @property
    def dimensions(self) -> int:
        return self._dim

    @property
    def available(self) -> bool:
        """Always False: this provider is the fallback, backed by no neural model."""
        return False

    def encode(self, text: str) -> bytes | None:
        """Encode one text to a deterministic, L2-normalized float32 blob.

        precondition: none (``text`` may be empty).
        postcondition: ``None`` for empty text; otherwise a ``self._dim``-length
        float32 blob, deterministic in ``(text, dim)``.
        """
        if not text:
            return None
        vec = embed_text(text, self._dim)
        return vec.astype(np.float32).tobytes()

    def encode_batch(self, texts: list[str]) -> list[bytes | None]:
        """Encode a batch, preserving order and ``None`` for empty items."""
        return [self.encode(t) for t in texts]
