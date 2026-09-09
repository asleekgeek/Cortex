"""Shared benchmark library — retrieval, fusion, and PG database helpers.

source: ADR-0059"""

from benchmarks.lib.fusion import (
    wrrf_fuse,
    QualityZone,
    assess_quality_zone,
    enforce_chunk_limit,
)
from benchmarks.lib.retriever import BenchmarkRetriever

__all__ = [
    "BenchmarkDB",
    "BenchmarkRetriever",
    "wrrf_fuse",
    "QualityZone",
    "assess_quality_zone",
    "enforce_chunk_limit",
]


def __getattr__(name: str):
    """Lazily resolve ``BenchmarkDB`` on first access (PEP 562).

    Precondition: ``name`` is an attribute looked up on this module that
    was not found among its eagerly-bound names above.
    Postcondition: returns ``bench_db.BenchmarkDB`` for
    ``name == "BenchmarkDB"`` — raising whatever ``ImportError`` psycopg's
    own absence produces, deferred until actually needed — else raises
    ``AttributeError`` (the standard module-attribute-not-found contract).
    """
    if name == "BenchmarkDB":
        from benchmarks.lib.bench_db import (  # noqa: PLC0415 — deferred: module hard-imports pgvector/psycopg/psycopg_pool at top level; hoisting would break installs without it
            BenchmarkDB,
        )

        return BenchmarkDB
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
