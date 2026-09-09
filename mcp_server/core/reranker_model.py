"""FlashRank model identity, cache location, and the offline-fetch gate.

source: ADR-0244"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path

from mcp_server.shared.platform import cache_dir as _base_cache_dir

# source: ADR-0244


_MODEL_NAME = "ms-marco-MiniLM-L-12-v2"
_MODEL_FILE = "flashrank-MiniLM-L-12-v2_Q.onnx"

# source: ADR-0244


_OFFLINE_ENV = "CORTEX_RERANKER_OFFLINE"


def _offline_requested() -> bool:
    """True when the caller has forbidden a network fetch of the model.

    Precondition: none.
    Postcondition: True iff CORTEX_RERANKER_OFFLINE is set to a value other
    than empty, 0, false, or no, ignoring whitespace and case. Unset is False.
    source: ADR-0244"""
    return os.environ.get(_OFFLINE_ENV, "").strip().lower() not in (
        "",
        "0",
        "false",
        "no",
    )


@dataclass(frozen=True)
class RerankerStatus:
    """Snapshot of the FlashRank reranker singleton's load state.

    source: ADR-0244"""

    state: str
    model_path: str
    error: str | None = None


def reranker_cache_dir() -> Path:
    """Durable on-disk cache directory for the FlashRank ONNX model.

    source: ADR-0244"""
    return _base_cache_dir() / "flashrank"


def _model_path() -> Path:
    return reranker_cache_dir() / _MODEL_NAME / _MODEL_FILE


def model_sha256() -> str | None:
    """Sha256 of the on-disk ONNX weights file, or None if it is absent.

    source: ADR-0244"""
    path = _model_path()
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()
