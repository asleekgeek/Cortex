"""Process-local experiment hooks; no production import depends on this module."""

from __future__ import annotations

from contextlib import ExitStack, contextmanager
from importlib import import_module
from importlib.metadata import version
from pathlib import Path
import time
from unittest.mock import patch

from mcp_server.shared.telemetry_context import operation_metrics

from benchmarks.reranker_matrix.cache import digest_file, durable_root, verify
from benchmarks.reranker_matrix.corpus import loaded_corpus
from benchmarks.reranker_matrix.pins import FLASHRANK_VERSION, Cell


def fetched(original, multiplier: int, observations: list):
    """Preserve SQL pools, weights and final fusion; vary the returned prefix only."""

    def wrapped(ctx, weights):
        rows = original(ctx, weights)
        kept = rows[: ctx.top_k * multiplier]
        observations.append(
            {"top_k": ctx.top_k, "sql_returned": len(rows), "admitted": len(kept)}
        )
        return kept

    return wrapped


def reranked(original, observations: list):
    """Record actual CE work; refuse scores after swallowed inference failures."""

    def wrapped(query, candidates, content_lookup, **kwargs):
        wall = time.perf_counter_ns()
        cpu = time.process_time_ns()
        with operation_metrics() as metrics:
            rows = original(query, candidates, content_lookup, **kwargs)
        observations.append(
            {
                "candidates": len(candidates),
                "reranked_count": metrics.reranked_count,
                "wall_ns": time.perf_counter_ns() - wall,
                "cpu_ns": time.process_time_ns() - cpu,
            }
        )
        if metrics.reranked_count != len(candidates):
            raise RuntimeError(
                "reranker skipped/failed inference; refusing matrix score"
            )
        return rows

    return wrapped


def replacements(config: Cell, root: Path, evidence: dict) -> list[tuple]:
    model = import_module("mcp_server.core.reranker_model")
    ranker = import_module("mcp_server.core.reranker")
    context = import_module("mcp_server.core.pg_recall_context")
    stages = import_module("mcp_server.core.pg_recall_stages")
    if ranker.reranker_status().state != "not_attempted":
        raise RuntimeError("cell must be configured before any reranker load")
    return [
        (model, "_MODEL_NAME", config.model.name),
        (model, "_MODEL_FILE", config.model.filename),
        (model, "reranker_cache_dir", lambda: root),
        (ranker, "_MODEL_NAME", config.model.name),
        (ranker, "_MODEL_FILE", config.model.filename),
        (ranker, "reranker_cache_dir", lambda: root),
        (ranker, "_flashrank_instance", None),
        (ranker, "_flashrank_failed", False),
        (ranker, "_flashrank_load_error", None),
        (ranker.silent_failure, "note", reject_failure(ranker.silent_failure.note)),
        (
            context,
            "_wrrf_fetch",
            fetched(context._wrrf_fetch, config.multiplier, evidence["fetches"]),
        ),
        (
            stages,
            "rerank_results",
            reranked(stages.rerank_results, evidence["reranks"]),
        ),
    ]


def dataset_replacements(evidence: dict) -> list[tuple]:
    beam = import_module("benchmarks.beam.data")
    locomo = import_module("benchmarks.locomo.data")
    return [
        (
            beam,
            "load_beam_dataset",
            loaded_corpus(beam.load_beam_dataset, "beam", evidence["datasets"]),
        ),
        (
            locomo,
            "load_locomo",
            loaded_corpus(locomo.load_locomo, "locomo", evidence["datasets"]),
        ),
    ]


def reject_failure(original):
    """Preserve diagnostics, but a reranker fallback cannot become a matrix result."""

    def note(operation, error):
        original(operation, error)
        if operation.startswith("reranker."):
            raise RuntimeError(f"reranker experiment failure at {operation}") from error

    return note


@contextmanager
def selected_cell(config: Cell):
    root = durable_root()
    evidence = verify(root, config.model)
    if version("flashrank") != FLASHRANK_VERSION:
        raise RuntimeError(
            "FlashRank version differs from the inspected model contract"
        )
    evidence["packages"] = {
        name: version(name) for name in ("flashrank", "onnxruntime")
    }
    evidence.update(
        {
            "cell": config.name,
            "multiplier": config.multiplier,
            "boundary": "SQL fused prefix before familiarity triage",
            "fetches": [],
            "reranks": [],
            "datasets": {},
        }
    )
    evidence["code_sha256"] = code_identity()
    with ExitStack() as stack:
        stack.enter_context(patch.dict("os.environ", {"CORTEX_RERANKER_OFFLINE": "1"}))
        for module, attribute, value in replacements(
            config, root, evidence
        ) + dataset_replacements(evidence):
            stack.enter_context(patch.object(module, attribute, value))
        yield evidence


def code_identity() -> dict[str, str]:
    root = Path(__file__).resolve().parents[2]
    paths = (
        "uv.lock",
        "mcp_server/infrastructure/pg_schema.py",
        "mcp_server/core/reranker_scoring.py",
        "mcp_server/handlers/recall.py",
        "mcp_server/core/pg_recall_context.py",
        "mcp_server/core/pg_recall_stages.py",
    )
    return {name: digest_file(root / name) for name in paths}
