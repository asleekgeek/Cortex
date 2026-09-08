"""Stdlib-only SQL spies and source extraction; never import store/ML modules."""

from __future__ import annotations

import ast
import copy
import json
import struct
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from mcp_server.core.capture_template_normalize import (
    capture_template_normalize,
    is_auto_capture_template,
    is_derived_fact_template,
)
from mcp_server.shared.memory_rows import MemoryRows


ROOT = Path(__file__).resolve().parents[1]


def source_functions(relative, names, namespace=None):
    """Execute real function bodies with explicit dependency doubles only."""
    tree = ast.parse((ROOT / relative).read_text())
    selected = [
        n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name in names
    ]
    body = [
        ast.ImportFrom(
            module="__future__", names=[ast.alias(name="annotations")], level=0
        )
    ]
    for node in selected:
        node = copy.deepcopy(node)
        node.decorator_list = []
        # _retrieve_fn's facade import is a seam supplied explicitly below.
        node.body = [
            n for n in node.body if not isinstance(n, (ast.Import, ast.ImportFrom))
        ]
        body.append(node)
    scope = dict(namespace or {})
    exec(
        compile(
            ast.fix_missing_locations(ast.Module(body=body, type_ignores=[])),
            relative,
            "exec",
        ),
        scope,
    )  # noqa: S102 — execute selected checked-in source, no external input
    return SimpleNamespace(**{name: scope[name] for name in names})


def vector_bytes(vector):
    if isinstance(vector, bytes):
        return vector
    return struct.pack(f"{len(vector)}f", *vector)


SERIALIZE = source_functions(
    "mcp_server/infrastructure/pg_store_serialize.py",
    ["_normalize_memory_row", "_isoformat_datetime_fields"],
    {
        "json": json,
        "datetime": datetime,
        "_DATETIME_FIELDS": ("created_at", "ingested_at"),
    },
)
PG = source_functions(
    "mcp_server/infrastructure/pg_store_heat.py", ["get_memory", "get_memories_by_ids"]
)
SQLITE = source_functions(
    "mcp_server/infrastructure/sqlite_store_queries.py", ["get_memories_by_ids"]
)
SEARCH = source_functions(
    "mcp_server/infrastructure/pg_store_search.py", ["search_vectors"]
)


class SqlSpy:
    get_memory = PG.get_memory
    get_memories_by_ids = PG.get_memories_by_ids
    search_vectors = SEARCH.search_vectors
    _normalize_memory_row = SERIALIZE._normalize_memory_row
    _isoformat_datetime_fields = staticmethod(SERIALIZE._isoformat_datetime_fields)
    _vector_to_bytes = staticmethod(vector_bytes)
    _bytes_to_vector = staticmethod(lambda value: value)

    def __init__(self, rows, hits=None):
        self.rows = copy.deepcopy(rows)
        self.hits = list(hits if hits is not None else [(mid, 0.0) for mid in rows])
        self._execute = Mock(side_effect=self._query)
        self._conn = SimpleNamespace(execute=self._execute)

    def _query(self, sql, params):
        if "AS distance" in sql:
            rows = [{"id": mid, "distance": distance} for mid, distance in self.hits]
        else:
            ids = params[0] if "ANY" in sql else params
            rows = [
                copy.deepcopy(row)
                for mid, row in reversed(list(self.rows.items()))
                if mid in ids
            ]
        return SimpleNamespace(
            fetchall=lambda: rows, fetchone=lambda: rows[0] if rows else None
        )


class Engine:
    """Deterministic bytes distinguish normalized text from stored vectors."""

    def __init__(self):
        self.encode = Mock(side_effect=self._scalar)
        self.encode_batch = Mock(side_effect=self._batch)
        self.similarity = Mock(side_effect=self._similarity)

    def _scalar(self, text):
        return b"normalized:" + text.encode() if text else None

    def _batch(self, texts):
        return [self._scalar(text) for text in texts]

    def _similarity(self, first, second):
        return float(len(first) + len(second))


def gate_functions():
    scope = {
        "ObservedNeighbors": lambda sims, hits, rows: SimpleNamespace(
            similarities=sims, hits=hits, rows=rows
        ),
        "MemoryRows": MemoryRows,
        "capture_template_normalize": capture_template_normalize,
        "is_auto_capture_template": is_auto_capture_template,
        "is_derived_fact_template": is_derived_fact_template,
        "compute_embedding_novelty": lambda sims: tuple(sims),
        "observe_gate": Mock(side_effect=AssertionError("must reuse observation")),
        "_finish_observed_gate": lambda request, observed, signals: signals,
        "write_gate": SimpleNamespace(compute_temporal_novelty=temporal_signal),
    }
    return source_functions(
        "mcp_server/handlers/remember_helpers.py",
        [
            "compute_similarities",
            "_similarities_with_rows",
            "compute_template_normalized_similarities",
            "evaluate_observed_gate",
        ],
        scope,
    )


# Exact temporal selector body; only timestamp scoring is replaced by its input
# so tests expose the selected row without depending on the wall clock.
temporal_signal = source_functions(
    "mcp_server/core/write_gate.py",
    ["compute_temporal_novelty"],
    {
        "_compute_temporal_novelty": lambda value: value,
        "_parse_hours_since": lambda value: value,
    },
).compute_temporal_novelty


def rows_fixture(count=5):
    return {
        mid: {
            "id": mid,
            "content": f"# Tool: Read\n**Read:** `/file_{mid}.py`",
            "embedding": [float(mid), 1.0],
            "created_at": "2026-09-06T00:00:00+00:00",
            "heat_base": 0.5,
            "tags": '["capture"]',
            "plan_id": "current",
        }
        for mid in range(1, count + 1)
    }


def old_gate_signals(request, engine):
    """Pre-W4-3 read sequence with current scalar scoring: 1 + 5 + 5 + 1 SQL."""
    store, content = request.store, request.content
    hits = store.search_vectors(b"raw", top_k=5, min_heat=0.0, heads_only=True)
    sims = []
    for mid, _distance in hits:
        memory = store.get_memory(mid)
        if memory and memory.get("embedding"):
            sims.append(engine.similarity(b"raw", memory["embedding"]))
    normalized = gate_functions().compute_template_normalized_similarities(
        content, hits, store, engine
    )
    return {
        "sims": sims,
        "vec_hits": hits,
        "emb_nov": tuple(normalized if normalized is not None else sims),
        "temp_nov": temporal_signal(sims, hits, store.get_memory),
    }


def old_titans_embeddings(candidates, store):
    """Frozen pre-W4-3 loop, including duplicate IDs and missing vectors."""
    result = []
    for candidate in candidates[:10]:
        memory = store.get_memory(candidate["memory_id"])
        if memory and memory.get("embedding"):
            result.append(memory["embedding"])
    return result


def old_stage_rows(candidates, store, detector, limit):
    """Frozen pre-W4-3 assembly loop with a known entity fixture."""
    result = []
    for candidate in candidates:
        memory = store.get_memory(candidate["memory_id"])
        if not memory or detector.stage_of(memory) != "current":
            continue
        output = dict(candidate)
        output["embedding"] = memory.get("embedding")
        output["entity_ids"] = (
            ["7"] if "needle" in (memory.get("content") or "").lower() else []
        )
        result.append(output)
        if len(result) >= limit:
            break
    return result


def stage_retriever(store, candidates, detector):
    return source_functions(
        "mcp_server/core/pg_recall_assembly.py",
        ["_retrieve_fn"],
        {
            "MemoryRows": MemoryRows,
            "store": store,
            "embeddings": None,
            "domain": "fixture",
            "detector": detector,
            "_MIN_ENTITY_NAME_LEN": 3,
            "recall": Mock(return_value=candidates),
            "_ensure_graph": lambda: {"entities": [{"id": 7, "name": "Needle"}]},
        },
    )._retrieve_fn


def final_stage(store):
    titans = SimpleNamespace(update=Mock(return_value=0.25))
    ctx = SimpleNamespace(
        store=store, intent="general", momentum_state={}, q_emb=b"query", sa_mode="rrf"
    )
    apply = source_functions(
        "mcp_server/core/pg_recall_stages.py",
        ["apply_final_stages"],
        {
            "MemoryRows": MemoryRows,
            "QueryIntent": SimpleNamespace(EVENT_ORDER="event"),
            "_get_titans": lambda: titans,
        },
    ).apply_final_stages
    return apply, ctx, titans
