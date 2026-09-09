"""Structured 3-phase context assembly.

source: ADR-0217
"""

from __future__ import annotations
from typing import Any
from mcp_server.shared.memory_rows import MemoryRows

from mcp_server.core.context_assembly.condensers import condense_assembled_context
from mcp_server.core.context_assembly.stage_assembler import (
    BudgetSplit,
    StageAwareContextAssembler,
)
from mcp_server.core.context_assembly.stage_detector import ExplicitStageDetector

# source: ADR-0217

# source: ADR-0217
_MIN_ENTITY_NAME_LEN = 3


# ── Structured 3-phase context assembly (new path) ─────────────────────


def assemble_context(
    query: str,
    store: Any,
    embeddings: Any,
    *,
    current_stage: str,
    token_budget: int | None = None,
    domain: str | None = None,
    stage_field: str = "plan_id",
    budget_split: tuple[float, float, float] = (0.6, 0.3, 0.1),
    max_chunks_per_phase: int = 5,
    diversity_lambda: float = 0.0,
    stage_detector: Any | None = None,
) -> dict[str, Any]:
    """Structured 3-phase context assembly for a single query.

    source: ADR-0217

    Args:
        query: Raw query text.
        store: PgMemoryStore supplying the entity graph and memories.
        embeddings: Engine encoding the query.
        current_stage: Stage identifier, such as conversation or agent topic.
        token_budget: Assembled context token cap (default 6000).
        domain: Optional retrieval domain.
        stage_field: Memory stage field (default plan_id).
        budget_split: Own/adjacent/summary proportions (default 0.6/0.3/0.1).
        max_chunks_per_phase: Per-phase chunk cap.
        diversity_lambda: MMR diversity weight (default 0.5).
    source: ADR-0217"""

    split = BudgetSplit(
        own_stage=budget_split[0],
        adjacent=budget_split[1],
        summaries=budget_split[2],
    )
    # Use the caller-provided detector if given, else default to Explicit
    if stage_detector is not None:
        detector = stage_detector
    else:
        detector = ExplicitStageDetector(field=stage_field)

    # source: ADR-0217

    _graph_cache: dict[str, Any] = {}

    def _ensure_graph() -> dict[str, Any]:
        if _graph_cache:
            return _graph_cache
        entities = (
            store.get_all_entities() if hasattr(store, "get_all_entities") else []
        )
        relationships = (
            store.get_all_relationships()
            if hasattr(store, "get_all_relationships")
            else []
        )
        _graph_cache["entities"] = entities
        _graph_cache["relationships"] = relationships
        _graph_cache["id_to_name"] = {
            str(e.get("id")): e.get("name", "") for e in entities
        }
        _graph_cache["name_to_id"] = {
            (e.get("name") or "").lower(): str(e.get("id")) for e in entities
        }
        return _graph_cache

    # source: ADR-0217

    def _retrieve_fn(q: str, stage_id: str, max_results: int) -> list[dict[str, Any]]:
        # source: ADR-0217

        from mcp_server.core.pg_recall import recall  # noqa: PLC0415 — source: ADR-0217

        candidates = recall(
            query=q,
            store=store,
            embeddings=embeddings,
            top_k=max_results * 3,
            domain=domain,
            include_globals=False,
            rerank=True,
        )
        graph = _ensure_graph()
        # Pre-compute (name_lower, eid) pairs once per Phase 1 call
        entity_pairs: list[tuple[str, str]] = []
        for e in graph.get("entities", []):
            name = (e.get("name") or "").strip().lower()
            eid = str(e.get("id", ""))
            if len(name) >= _MIN_ENTITY_NAME_LEN and eid:
                entity_pairs.append((name, eid))

        memories = MemoryRows.read(store, [c["memory_id"] for c in candidates])
        filtered: list[dict[str, Any]] = []
        for c in candidates:
            mem = memories.get_memory(c["memory_id"])
            if not mem:
                continue
            if detector.stage_of(mem) != stage_id:
                continue
            content_lower = (mem.get("content") or "").lower()
            entity_ids_for_mem: list[str] = [
                eid for name, eid in entity_pairs if name in content_lower
            ]
            c_out = dict(c)
            c_out["embedding"] = mem.get("embedding")
            c_out["entity_ids"] = entity_ids_for_mem
            filtered.append(c_out)
            if len(filtered) >= max_results:
                break
        return filtered

    # ── Entity graph callback for Phase 2 ─────────────────────────────
    def _entity_graph_fn() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        graph = _ensure_graph()
        return graph["entities"], graph["relationships"]

    # source: ADR-0217

    def _memories_by_entity_fn(
        entity_ids: list[str],
    ) -> list[dict[str, Any]]:
        if not hasattr(store, "get_memories_mentioning_entity"):
            return []
        graph = _ensure_graph()
        id_to_name: dict[str, str] = graph["id_to_name"]
        # Build (name_lower, eid) pairs once for entity_ids enrichment
        entity_pairs: list[tuple[str, str]] = []
        for e in graph.get("entities", []):
            nm = (e.get("name") or "").strip().lower()
            eid = str(e.get("id", ""))
            if len(nm) >= _MIN_ENTITY_NAME_LEN and eid:
                entity_pairs.append((nm, eid))

        out: list[dict[str, Any]] = []
        seen_ids: set[int] = set()
        for eid in entity_ids:
            name = id_to_name.get(str(eid))
            if not name:
                continue
            # heads_only: Phase 2 serves memory content into the assembled
            # context — supersession chain heads only.
            mems = (
                store.get_memories_mentioning_entity(name, limit=10, heads_only=True)
                or []
            )
            for m in mems:
                mid = m.get("id") or m.get("memory_id")
                if mid is None or mid in seen_ids:
                    continue
                if domain and m.get("domain") != domain:
                    continue
                seen_ids.add(mid)
                content_lower = (m.get("content") or "").lower()
                m_entity_ids = [
                    pid for pname, pid in entity_pairs if pname in content_lower
                ]
                m_out = dict(m)
                m_out["memory_id"] = mid
                m_out["entity_ids"] = m_entity_ids
                out.append(m_out)
        return out

    # ── Stage summary callback for Phase 3 ────────────────────────────
    # For BEAM we don't have pre-computed summaries yet. Return the
    # first ~300 chars of the first memory in the stage as a proxy.
    # Production Cortex will wire this to dual_store_cls.py / schema_engine.
    def _stage_summary_fn(stage_id: str) -> str:
        # source: ADR-0217

        return ""

    assembler = StageAwareContextAssembler(
        stage_detector=detector,
        retrieve_fn=_retrieve_fn,
        entity_graph_fn=_entity_graph_fn,
        memories_by_entity_fn=_memories_by_entity_fn,
        stage_summary_fn=_stage_summary_fn,
    )

    result = assembler.assemble(
        query=query,
        current_stage=current_stage,
        token_budget=token_budget,
        budget_split=split,
        max_chunks_per_phase=max_chunks_per_phase,
        diversity_lambda=diversity_lambda,
    )

    # source: ADR-0217

    assembled_context = result.assembled_context
    if token_budget is not None:
        assembled_context = condense_assembled_context(
            result.own_stage_context,
            result.adjacent_stage_context,
            result.stage_summaries,
            current_stage,
            token_budget,
        )

    return {
        "assembled_context": assembled_context,
        "own_stage_context": result.own_stage_context,
        "adjacent_stage_context": result.adjacent_stage_context,
        "stage_summaries": result.stage_summaries,
        "metadata": result.metadata,
        # Contains both Phase 1 and Phase 2 selected memories, each
        # tagged with a `phase` field (1 or 2). Downstream evaluators
        # read this to score retrieval hits across all phases.
        "selected_memories": result.selected_memories,
    }
