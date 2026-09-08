"""Personalized PageRank traversal over Cortex's entity graph (Phase 2).

source: ADR-0148"""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def personalized_pagerank(
    adjacency: dict[str, list[tuple[str, float]]],
    seeds: dict[str, float],
    *,
    alpha: float = 0.15,
    max_iters: int = 30,
    tolerance: float = 1e-4,
) -> dict[str, float]:
    """Compute PPR scores for every node reachable from the seeds.

    Power-iteration variant of Personalized PageRank.

    Args:
        adjacency: node_id to (neighbor_id, edge_weight) lists; weights are
            normalized to probabilities during iteration.
        seeds: node_id to seed mass, normalized and injected on every restart.
        alpha: Restart probability (default 0.15); higher values localize.
        max_iters: Power iteration cap.
        tolerance: L1 convergence threshold.
    source: ADR-0148

    Returns:
        Dict node_id → PPR score. Only nodes with non-zero mass are
        included.
    """
    if not seeds:
        return {}

    # Normalize seed mass
    seed_total = sum(seeds.values())
    if seed_total <= 0:
        return {}
    seed_dist = {k: v / seed_total for k, v in seeds.items()}

    # Initialize rank = seed distribution
    rank: dict[str, float] = dict(seed_dist)

    # Pre-normalize outgoing edge weights to probabilities
    out_probs: dict[str, list[tuple[str, float]]] = {}
    for node, edges in adjacency.items():
        total = sum(w for _, w in edges)
        if total > 0:
            out_probs[node] = [(n, w / total) for n, w in edges]
        else:
            out_probs[node] = []

    for _ in range(max_iters):
        new_rank: dict[str, float] = defaultdict(float)
        # Random restart mass
        for node, mass in seed_dist.items():
            new_rank[node] += alpha * mass
        # Walk step: distribute (1 - α) of each node's mass along edges
        for node, mass in rank.items():
            if mass <= 0:
                continue
            edges = out_probs.get(node, [])
            if not edges:
                # Dangling node: re-inject via seeds
                for s, sm in seed_dist.items():
                    new_rank[s] += (1 - alpha) * mass * sm
                continue
            for nbr, prob in edges:
                new_rank[nbr] += (1 - alpha) * mass * prob

        # Convergence check
        delta = sum(
            abs(new_rank.get(k, 0.0) - rank.get(k, 0.0))
            for k in set(new_rank) | set(rank)
        )
        rank = dict(new_rank)
        if delta < tolerance:
            break

    return {k: v for k, v in rank.items() if v > 0}


# ── Adapter: build PPR input from Cortex's entity/relationship tables ──


def build_entity_adjacency(
    entities: list[dict[str, Any]],
    relationships: list[dict[str, Any]],
) -> dict[str, list[tuple[str, float]]]:
    """Build a PPR adjacency dict from Cortex's entity/relationship records.

    Args:
        entities: list of entity dicts with at least "id" or "name".
        relationships: list of relationship dicts with "source_entity_id",
            "target_entity_id", and optionally "strength" (defaults to 1.0).
            Undirected — each relationship adds both directions.

    Returns:
        Dict node_id → list of (neighbor_id, weight). Suitable for
        `personalized_pagerank`.
    """
    adj: dict[str, list[tuple[str, float]]] = defaultdict(list)
    # source: ADR-0148
    for e in entities:
        node_id = str(e.get("id") or e.get("name") or "")
        if node_id:
            _ = adj[node_id]  # touch to create key
    for r in relationships:
        src = str(r.get("source_entity_id") or r.get("source") or "")
        tgt = str(r.get("target_entity_id") or r.get("target") or "")
        weight = float(r.get("strength", 1.0))
        if src and tgt and weight > 0:
            adj[src].append((tgt, weight))
            adj[tgt].append((src, weight))
    return dict(adj)


# ── Score memories by aggregating PPR mass over contained entities ─────


def score_memories_by_ppr(
    memories: list[dict[str, Any]],
    ppr_scores: dict[str, float],
    *,
    entity_ids_key: str = "entity_ids",
) -> list[tuple[dict[str, Any], float]]:
    """Aggregate PPR mass onto memories via their contained entities.

    Following HippoRAG §3.3: a memory's relevance under PPR is the sum
    of PPR mass of its entities. Memories without any entity get score
    0 and are filtered out.

    Args:
        memories: list of memory dicts. Each must expose the list of
            entity IDs it contains under `entity_ids_key`.
        ppr_scores: output of `personalized_pagerank`.
        entity_ids_key: field name holding the list of entity IDs.

    Returns:
        List of (memory, score) tuples sorted by descending score.
    """
    scored: list[tuple[dict[str, Any], float]] = []
    for m in memories:
        entity_ids = m.get(entity_ids_key, []) or []
        mass = sum(ppr_scores.get(str(eid), 0.0) for eid in entity_ids)
        if mass > 0:
            scored.append((m, mass))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored
