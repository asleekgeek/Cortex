"""Composition root for the embedding subsystem (Cortex#173, seam 3).

This is the "engine selection / wiring" seam: the single place that reads the
runtime settings (``EMBEDDING_DIM`` / ``EMBEDDING_DEVICE``) and assembles the
process-wide encoder. Consumers call ``get_embedding_engine()`` rather than
constructing an ``EmbeddingEngine`` themselves, which guarantees one model, one
device, no mixed-device embeddings, ~5x memory savings.

Keeping selection here — separate from the concrete provider
(``embedding_engine.EmbeddingEngine``) and its interface
(``embedding_provider.EmbeddingProvider``) — is what lets a second provider be
wired in later by editing exactly this one function, with no consumer change.

Import-cycle note: the concrete ``EmbeddingEngine`` (and ``get_memory_settings``)
are imported lazily *inside* ``get_embedding_engine`` so this module has no
module-load dependency on ``embedding_engine`` — ``embedding_engine`` re-exports
these functions, so the two modules must not import each other at top level.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp_server.infrastructure.embedding_engine import EmbeddingEngine

# Process-wide singleton. Handlers/hooks read it via get_embedding_engine().
_singleton: EmbeddingEngine | None = None


def get_embedding_engine() -> "EmbeddingEngine":
    """Return the process-wide EmbeddingEngine singleton, building it once.

    precondition: none.
    postcondition: the same instance is returned for every call until
    ``reset_embedding_engine`` clears it; the instance is constructed from the
    current ``MemorySettings`` (dimension + device).
    """
    global _singleton
    if _singleton is None:
        from mcp_server.infrastructure.embedding_engine import EmbeddingEngine
        from mcp_server.infrastructure.memory_config import get_memory_settings

        s = get_memory_settings()
        _singleton = EmbeddingEngine(dim=s.EMBEDDING_DIM, device=s.EMBEDDING_DEVICE)
    return _singleton


def reset_embedding_engine() -> None:
    """Clear the singleton (for testing only)."""
    global _singleton
    _singleton = None
