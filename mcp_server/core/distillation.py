"""Distillation dossier assembly — server-side candidate gathering for the
``curate_distill`` job; lesson AUTHORING stays with the in-session LLM
(M-D8).

source: ADR-0159"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from mcp_server.shared.hash import simple_hash
from mcp_server.core.auto_curator import extract_entities_from_content

if TYPE_CHECKING:
    from mcp_server.core.auto_curator import CurationCluster

# source: ADR-0159


_MAX_DOSSIERS_PER_KIND = 10
_MAX_MEMORY_IDS_PER_DOSSIER = 12

# Error->success pairing: memories must share at least this many lexical
# entities (extract_entities_from_content) to count as "about the same
# thing". 1 is the minimum that means "related at all".
_MIN_SHARED_ENTITIES = 1

# source: ADR-0159


_DEFAULT_ERROR_SUCCESS_WINDOW_HOURS = 168.0

# source: ADR-0159


_MIN_RECURRING_ACCESS = 5
_MIN_CO_ACCESS_CLUSTER_SIZE = 3


def _parse_iso(ts: str | None) -> float:
    """ISO 8601 string -> Unix seconds; 0.0 on any parse failure.

    Precondition: accepts None or malformed input.
    Postcondition: never raises.
    source: ADR-0159"""
    if not ts:
        return 0.0
    try:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except (ValueError, TypeError):
        return 0.0


def dossier_marker_tag(memory_ids: list[int]) -> str:
    """Deterministic idempotence marker for a dossier's member set.

    Precondition: ``memory_ids`` is non-empty.
    Postcondition: identical sets of IDs yield identical tag strings,
    independently of input order and duplicate IDs.
    source: ADR-0159"""
    canonical = ",".join(str(i) for i in sorted(set(memory_ids)))
    return f"distill-of:{simple_hash(canonical)}"


@dataclass
class DistillDossier:
    """One candidate — evidence a lesson-shaped synthesis is possible.

    ``marker`` is this dossier's idempotence key (``dossier_marker_tag``
    of its canonical ``memory_ids``); the handler skips re-offering a
    dossier whose marker already exists as a tag on a stored memory (same
    skip-before-gate pattern as ``memify_derive._existing_derived_markers``).
    """

    kind: str  # "error_success" | "co_access_family" | "entity_family"
    topic: str
    domain: str
    memory_ids: list[int] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    avg_heat: float = 0.0
    marker: str = ""

    def __post_init__(self) -> None:
        self.memory_ids = sorted(set(int(i) for i in self.memory_ids))
        if not self.marker and self.memory_ids:
            self.marker = dossier_marker_tag(self.memory_ids)


def build_error_success_dossiers(
    error_memories: list[dict[str, Any]],
    success_memories: list[dict[str, Any]],
    window_hours: float = _DEFAULT_ERROR_SUCCESS_WINDOW_HOURS,
    max_dossiers: int = _MAX_DOSSIERS_PER_KIND,
) -> list[DistillDossier]:
    """Pair each error-tagged memory with the nearest LATER success-tagged
    memory sharing >= ``_MIN_SHARED_ENTITIES`` lexical entities within
    ``window_hours``.

    Precondition: both lists are fetched; each row carries id, content,
    created_at, and domain. Input order is arbitrary.
    Postcondition: returns at most max_dossiers, most-recent-error first;
    every dossier has two memory IDs (error, success). Each success row
    is consumed by at most one pairing.
    source: ADR-0159"""

    def _entities(mem: dict[str, Any]) -> set[str]:
        return set(extract_entities_from_content(mem.get("content") or ""))

    errors = sorted(
        error_memories, key=lambda m: _parse_iso(m.get("created_at")), reverse=True
    )
    successes = sorted(success_memories, key=lambda m: _parse_iso(m.get("created_at")))
    success_entities = {
        s["id"]: _entities(s) for s in successes if s.get("id") is not None
    }
    window_secs = window_hours * 3600.0

    dossiers: list[DistillDossier] = []
    used_success_ids: set[int] = set()
    for err in errors:
        if len(dossiers) >= max_dossiers:
            break
        err_id = err.get("id")
        err_t = _parse_iso(err.get("created_at"))
        if err_id is None or err_t == 0.0:
            continue
        err_ents = _entities(err)
        if not err_ents:
            continue
        best: tuple[int, float, set[str]] | None = None  # (succ_id, delta, shared)
        for succ in successes:
            succ_id = succ.get("id")
            # source: ADR-0159

            if succ_id is None or succ_id in used_success_ids or succ_id == err_id:
                continue
            delta = _parse_iso(succ.get("created_at")) - err_t
            if delta < 0 or delta > window_secs:
                continue
            shared = err_ents & success_entities.get(succ_id, set())
            if len(shared) < _MIN_SHARED_ENTITIES:
                continue
            if best is None or delta < best[1]:
                best = (succ_id, delta, shared)
        if best is None:
            continue
        succ_id, _delta, shared = best
        used_success_ids.add(succ_id)
        dossiers.append(
            DistillDossier(
                kind="error_success",
                topic=next(iter(sorted(shared)), "untitled"),
                domain=err.get("domain", ""),
                memory_ids=[int(err_id), int(succ_id)],
                entities=sorted(shared),
            )
        )
    return dossiers


class _UnionFind:
    """Minimal union-find for connected-components over co-access pairs.

    Precondition: none — ``find``/``union`` lazily create singleton
    components for unseen ids.
    Postcondition: path-compressed ``find`` keeps amortized near-O(1)
    lookups across the bounded (<= a few hundred edges) pair lists this
    module operates on.
    """

    def __init__(self) -> None:
        self._parent: dict[int, int] = {}

    def find(self, x: int) -> int:
        self._parent.setdefault(x, x)
        while self._parent[x] != x:
            self._parent[x] = self._parent[self._parent[x]]
            x = self._parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self._parent[ra] = rb


def build_co_access_dossiers(
    pairs: list[tuple[int, int, float]],
    heat_by_id: dict[int, float] | None = None,
    min_cluster_size: int = _MIN_CO_ACCESS_CLUSTER_SIZE,
    max_dossiers: int = _MAX_DOSSIERS_PER_KIND,
) -> list[DistillDossier]:
    """Connected components over recurring co-access edges.

    Precondition: pairs contains (mem_a, mem_b, proximity) rows with both
    endpoints already filtered to access_count >= min_access. Each row
    describes one last_accessed snapshot, not multiple observed pairings.
    Postcondition: returns components with >= min_cluster_size members,
    sorted by descending (size, average proximity). Each component is capped
    at _MAX_MEMORY_IDS_PER_DOSSIER, retaining highest-proximity endpoints;
    at most max_dossiers components are returned.
    source: ADR-0159"""
    if not pairs:
        return []
    uf = _UnionFind()
    weight_sum: dict[int, float] = {}
    weight_count: dict[int, float] = {}
    for a, b, _w in pairs:
        uf.union(a, b)
    # source: ADR-0159

    ordered_edges = sorted(pairs, key=lambda p: p[2], reverse=True)
    members: dict[int, list[int]] = {}
    for a, b, w in ordered_edges:
        root = uf.find(a)
        bucket = members.setdefault(root, [])
        for node in (a, b):
            if node not in bucket:
                bucket.append(node)
        weight_sum[root] = weight_sum.get(root, 0.0) + w
        weight_count[root] = weight_count.get(root, 0.0) + 1

    heat_by_id = heat_by_id or {}
    components = [ids for ids in members.values() if len(ids) >= min_cluster_size]
    components.sort(
        key=lambda ids: (len(ids), weight_sum.get(uf.find(ids[0]), 0.0)), reverse=True
    )

    dossiers: list[DistillDossier] = []
    for ids in components[:max_dossiers]:
        capped = ids[:_MAX_MEMORY_IDS_PER_DOSSIER]
        avg_heat = (
            sum(heat_by_id.get(i, 0.0) for i in capped) / len(capped) if capped else 0.0
        )
        dossiers.append(
            DistillDossier(
                kind="co_access_family",
                topic="",  # filled by the handler from fetched content
                domain="",
                memory_ids=capped,
                avg_heat=avg_heat,
            )
        )
    return dossiers


def dossier_from_cluster(cluster: "CurationCluster") -> DistillDossier:
    """Adapt an ``auto_curator.CurationCluster`` into a ``DistillDossier``.

    Precondition: cluster comes from core.auto_curator.build_clusters.
    Postcondition: memory_ids is capped at _MAX_MEMORY_IDS_PER_DOSSIER.
    source: ADR-0159"""
    capped_ids = list(cluster.memory_ids)[:_MAX_MEMORY_IDS_PER_DOSSIER]
    return DistillDossier(
        kind="entity_family",
        topic=cluster.topic,
        domain=cluster.domain,
        memory_ids=capped_ids,
        entities=list(cluster.entities),
        avg_heat=cluster.avg_heat,
    )


# source: ADR-0159
