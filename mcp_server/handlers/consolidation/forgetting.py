"""Consolidation cycle: dopaminergic active forgetting (two independent circuits).

Composition root wiring ``core.active_forgetting`` (pure decisions) to the PG
store (newer-neighbor search + reversible effects). It runs AFTER the deep-sleep
replay pass so memories replayed this cycle count as sleep-protected
(``recently_active``) and are exempt from the ongoing forgetting signal — sleep
inhibits the Rac1 forgetting circuit (Davis & Zhong 2017, Neuron 95:490-503).

Per active memory that is neither pinned nor replayed this cycle:

  - ``chronic_interference`` = the noisy-OR over the similarities of NEWER
    overlapping neighbors (``1 - ∏(1 - sim_i)``; Pearl 1988): param-free,
    bounded to [0, 1], monotone increasing in both neighbor count and strength
    — the faithful aggregate of Davis & Zhong's "ongoing" retroactive
    interference signal. Aggregation lives here (the store returns raw
    per-neighbor similarities) so the SQL stays a plain KNN and the maths is
    unit-testable without a database (SRP).

  - the acute interferer = the strongest newer neighbor (``acute_overlap``) and
    its age (``acute_age_hours``), feeding the stage-independent transient DAMB
    block (Sabandal, Berry & Davis 2021, Nature 591:426-430).

Effects, both reversible (the two circuits read disjoint signals and never
chain — Sabandal 2021 tested and rejected transient→permanent conversion):

  - permanent (Rac1) → ``mark_memory_stale(True)``: the row persists as a
    residual engram, reinstated when the trace is reactivated.
  - transient (DAMB) → ``heat × (1 - acute_overlap)``: retrieval suppression
    whose magnitude rides the *measured* interferer salience. No biological
    rate law exists for this magnitude at the hours/days timescale and the
    salience effect is ordinal only (Berry, Phan & Davis 2018, PMC6239218), so
    the suppression is scaled by the interferer overlap itself rather than an
    invented constant; heat recovers on re-access.

Ablation-gated by ``Mechanism.ACTIVE_FORGETTING``.
"""

from __future__ import annotations

import logging
from typing import Iterable

from mcp_server.core.ablation import Mechanism, is_mechanism_disabled
from mcp_server.core.active_forgetting import (
    is_permanent_forgetting,
    is_transient_forgetting,
)
from mcp_server.infrastructure.memory_store import MemoryStore

logger = logging.getLogger(__name__)

# Newer-neighbor fan-out for the chronic noisy-OR aggregate. Bounds I/O only:
# the noisy-OR is monotone in count, so this caps how much of a long similar-
# neighbor tail can contribute — it is NOT a biological rate constant. Matches
# the store's default KNN width.
# source: I/O bound; mirrors search_vectors default top_k (pg_store.py)
NEIGHBOR_K = 10


def _noisy_or(similarities: Iterable[float]) -> float:
    """Noisy-OR aggregate ``1 - ∏(1 - s_i)`` over neighbor similarities (Pearl 1988).

    Param-free, range [0, 1], monotone increasing in both the count and the
    strength of overlapping neighbors — the faithful accumulation of Davis &
    Zhong (2017)'s "ongoing" retroactive interference. Each similarity is
    clamped to [0, 1]: cosine can dip slightly negative for near-orthogonal
    embeddings, and a negative term must not inflate the product. An empty
    neighbor set yields 0.0 (no interference).
    """
    product = 1.0
    for s in similarities:
        product *= 1.0 - max(0.0, min(1.0, float(s)))
    return 1.0 - product


def run_forgetting_cycle(
    store: MemoryStore,
    recently_active_ids: set[int],
) -> dict:
    """Run the two-circuit active-forgetting pass over all active memories.

    Streams the corpus in bounded chunks (constant memory) and evaluates each
    memory against its newer overlapping neighbors. ``recently_active_ids`` are
    the memories replayed by the deep-sleep pass this cycle (sleep-protected).
    """
    if is_mechanism_disabled(Mechanism.ACTIVE_FORGETTING):
        return {"scanned": 0, "permanent": 0, "transient": 0, "ablated": True}
    if not hasattr(store, "search_newer_neighbors"):
        # Cowork/SQLite fallback does not implement the newer-neighbor query;
        # active forgetting is a production (PostgreSQL) deep-cycle mechanism.
        return {"scanned": 0, "permanent": 0, "transient": 0, "skipped": "unsupported_store"}

    counts = {"scanned": 0, "permanent": 0, "transient": 0}
    if hasattr(store, "iter_memories_for_decay"):
        chunks: Iterable[list[dict]] = store.iter_memories_for_decay()
    else:
        chunks = [store.get_all_memories_for_decay()]

    for chunk in chunks:
        for mem in chunk:
            counts["scanned"] += 1
            try:
                effect = _evaluate_memory(store, mem, recently_active_ids)
            except Exception:
                logger.debug("Forgetting eval failed for memory %s", mem.get("id"))
                continue
            if effect in ("permanent", "transient"):
                counts[effect] += 1
    return counts


def _evaluate_memory(
    store: MemoryStore,
    mem: dict,
    recently_active_ids: set[int],
) -> str:
    """Decide and apply the forgetting effect for one memory.

    Returns ``"permanent"``, ``"transient"``, or ``"retain"``. The permanent
    (stale) effect subsumes the transient (heat) effect, so once a memory is
    marked stale the redundant heat write is skipped — the independence of the
    two circuits is preserved at the DECISION level (disjoint signals), not by
    forcing two writes on the same row.
    """
    embedding = mem.get("embedding")
    if not embedding:
        return "retain"

    memory_id = int(mem["id"])
    neighbors = store.search_newer_neighbors(
        embedding, mem.get("created_at"), memory_id, top_k=NEIGHBOR_K
    )
    chronic = _noisy_or(sim for sim, _ in neighbors)
    acute_overlap, acute_age_hours = neighbors[0] if neighbors else (0.0, float("inf"))

    stage = mem.get("consolidation_stage") or "labile"
    heat = float(mem.get("heat", 0.0))
    is_pinned = bool(mem.get("is_protected")) or heat >= 1.0
    recently_active = memory_id in recently_active_ids

    if is_permanent_forgetting(stage, chronic, is_pinned, recently_active):
        store.mark_memory_stale(memory_id, True)
        return "permanent"
    if is_transient_forgetting(acute_overlap, acute_age_hours, is_pinned, recently_active):
        store.update_memory_heat(memory_id, heat * (1.0 - acute_overlap))
        return "transient"
    return "retain"
