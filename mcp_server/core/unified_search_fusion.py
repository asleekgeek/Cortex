"""Reciprocal Rank Fusion for unified search.

source: ADR-0289
"""

from __future__ import annotations

from typing import Iterable

# source: ADR-0289


DEFAULT_K = 60


def _id_of(item: dict, id_key: str) -> str | None:
    v = item.get(id_key)
    return str(v) if v is not None else None


def fuse(
    ranked_lists: Iterable[tuple[str, list[dict]]],
    *,
    k: int = DEFAULT_K,
    id_key: str = "id",
    top_n: int | None = None,
) -> list[dict]:
    """RRF-merge two or more ranked lists into one.

    source: ADR-0289

    ``top_n`` clips the returned list to the strongest N. ``None`` keeps
    all items.
    """
    scores: dict[str, float] = {}
    bodies: dict[str, dict] = {}
    source_ranks: dict[str, dict[str, int]] = {}
    source_order: list[str] = []

    for source_name, results in ranked_lists:
        source_order.append(source_name)
        for rank, item in enumerate(results, start=1):
            ident = _id_of(item, id_key)
            if ident is None:
                continue
            delta = 1.0 / (k + rank)
            scores[ident] = scores.get(ident, 0.0) + delta
            if ident not in bodies:
                # First retriever to mention this id owns the body.
                bodies[ident] = {**item}
            source_ranks.setdefault(ident, {})[source_name] = rank

    merged = []
    for ident, score in scores.items():
        body = bodies[ident]
        merged.append(
            {
                **body,
                id_key: ident,
                "rrf_score": round(score, 6),
                "source_ranks": source_ranks[ident],
            }
        )
    merged.sort(key=lambda r: r["rrf_score"], reverse=True)
    # Determinism: ties broken by presence in more retrievers, then by id.
    merged.sort(
        key=lambda r: (-r["rrf_score"], -len(r["source_ranks"]), r[id_key]),
    )
    if top_n is not None and top_n >= 0:
        merged = merged[:top_n]
    _ = source_order  # reserved for future per-source weighting
    return merged


__all__ = ["DEFAULT_K", "fuse"]
