"""Fuzzy entity-graph deduplication — 3-pass exact / MinHash-LSH / Jaro-Winkler.

source: ADR-0176"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from mcp_server.core.entity_dedup_filters import (
    ENTROPY_THRESHOLD,
    LSH_THRESHOLD,
    MERGE_THRESHOLD,
    NUM_PERM,
    entropy,
    affixes_sandwich_difference,
    is_affix_extension,
    is_structural_identifier,
    is_variant_pair,
    make_minhash,
    normalize_label,
    shared_prefix_masks_difference,
    short_label_blocked,
)
from mcp_server.shared.minhash import MinHash, MinHashLSH
from mcp_server.shared.string_distance import jaro_winkler_similarity

# source: ADR-0176


FUZZY_ELIGIBLE_TYPES = frozenset({"technology", "decision", "error", "dependency"})

# source: ADR-0176
_MIN_CANDIDATES_FOR_PAIRING = 2


@dataclass(frozen=True)
class EntityMerge:
    """One matched pair and why it matched (audit trail).

    source: ADR-0176
    """

    key_a: str
    key_b: str
    score: float
    reason: str


@dataclass
class DedupResult:
    """Outcome of a dedup pass.

    source: ADR-0176"""

    remap: dict[str, str] = field(default_factory=dict)
    merges: list[EntityMerge] = field(default_factory=list)
    survivors: list[dict] = field(default_factory=list)


class _UnionFind:
    """Disjoint-set with path halving — groups entities into merge components."""

    def __init__(self) -> None:
        self._parent: dict[str, str] = {}

    def find(self, x: str) -> str:
        self._parent.setdefault(x, x)
        while self._parent[x] != x:
            self._parent[x] = self._parent[self._parent[x]]
            x = self._parent[x]
        return x

    def union(self, x: str, y: str) -> None:
        self._parent.setdefault(x, x)
        self._parent.setdefault(y, y)
        rx, ry = self.find(x), self.find(y)
        if rx != ry:
            self._parent[ry] = rx

    def components(self) -> dict[str, list[str]]:
        groups: dict[str, list[str]] = defaultdict(list)
        for x in self._parent:
            groups[self.find(x)].append(x)
        return dict(groups)


def _merge_key(entity: dict) -> str:
    """Stable merge identity: the entity id if present, else its name."""
    if entity.get("id") is not None:
        return str(entity["id"])
    return str(entity.get("name", ""))


def _pick_winner(group: list[dict]) -> dict:
    """Canonical survivor: most-mentioned, then hottest, then shortest name.

    source: ADR-0176"""

    def rank(e: dict) -> tuple:
        name = str(e.get("name", ""))
        return (
            -int(e.get("mention_count") or 0),
            -float(e.get("heat") or 0.0),
            len(name),
            name,
        )

    return min(group, key=rank)


def deduplicate_entities(
    entities: list[dict],
    *,
    eligible_types: frozenset[str] = FUZZY_ELIGIBLE_TYPES,
    merge_threshold: float = MERGE_THRESHOLD,
) -> DedupResult:
    """Find near-duplicate concept entities and plan their collapse.

    Args:
        entities: dicts with at least ``name`` and ``type`` (``id``, ``heat``,
            ``mention_count`` used when present).
        eligible_types: entity types eligible for label-fuzzy merging.
        merge_threshold: Jaro-Winkler similarity in [0, 1] required to merge.

    Returns:
        DedupResult with the alias→canonical remap, the matched pairs, and the
        surviving entities. No mutation of the input.
    """
    if len(entities) <= 1:
        return DedupResult(survivors=list(entities))

    by_type: dict[str, list[dict]] = defaultdict(list)
    for e in entities:
        # source: ADR-0176

        if e.get("origin", "text_concept") == "ast_symbol":
            continue
        if e.get("type") in eligible_types and normalize_label(e.get("name", "")):
            by_type[e["type"]].append(e)

    uf = _UnionFind()
    merges: list[EntityMerge] = []
    for group in by_type.values():
        _exact_norm_pass(group, uf, merges)
        _fuzzy_pass(group, uf, merges, merge_threshold)

    remap, survivors = _build_remap(entities, uf)
    return DedupResult(remap=remap, merges=merges, survivors=survivors)


def _exact_norm_pass(
    group: list[dict], uf: _UnionFind, merges: list[EntityMerge]
) -> None:
    """Pass 1 — union entities whose normalized labels are identical."""
    buckets: dict[str, list[dict]] = defaultdict(list)
    for e in group:
        buckets[normalize_label(e["name"])].append(e)
    for norm, members in buckets.items():
        if len(members) <= 1:
            continue
        base_key = _merge_key(members[0])
        for other in members[1:]:
            other_key = _merge_key(other)
            uf.union(base_key, other_key)
            merges.append(EntityMerge(base_key, other_key, 1.0, f"exact-norm:{norm}"))


def _gather_candidates(group: list[dict]) -> tuple[list[dict], dict[str, str]]:
    """Pick one high-entropy entity per distinct normalized label for Pass 2."""
    candidates: list[dict] = []
    norm_cache: dict[str, str] = {}
    seen_norm: set[str] = set()
    for e in group:
        # source: ADR-0176

        if is_structural_identifier(str(e.get("name", ""))):
            continue
        norm = normalize_label(e["name"])
        if not norm or norm in seen_norm:
            continue
        seen_norm.add(norm)
        if entropy(e["name"]) >= ENTROPY_THRESHOLD:
            candidates.append(e)
            norm_cache[_merge_key(e)] = norm
    return candidates, norm_cache


def _build_lsh(
    candidates: list[dict], norm_cache: dict[str, str]
) -> tuple[MinHashLSH, dict[str, MinHash]]:
    """Index candidate sketches for sub-quadratic neighbor blocking."""
    lsh = MinHashLSH(threshold=LSH_THRESHOLD, num_perm=NUM_PERM)
    minhashes: dict[str, MinHash] = {}
    for e in candidates:
        key = _merge_key(e)
        m = make_minhash(norm_cache[key])
        minhashes[key] = m
        try:
            lsh.insert(key, m)
        except ValueError:
            pass  # duplicate key already inserted
    return lsh, minhashes


def _verify_pair(a_norm: str, b_norm: str, threshold: float) -> tuple[bool, float, str]:
    """Apply Jaro-Winkler + the three blockers to a candidate pair."""
    score = jaro_winkler_similarity(a_norm, b_norm)
    if is_variant_pair(a_norm, b_norm):
        return False, score, "blocked:variant"
    if short_label_blocked(a_norm, b_norm, score):
        return False, score, "blocked:short-label"
    if is_affix_extension(a_norm, b_norm):
        return False, score, "blocked:affix-extension"
    if shared_prefix_masks_difference(a_norm, b_norm):
        return False, score, "blocked:shared-prefix"
    if affixes_sandwich_difference(a_norm, b_norm):
        return False, score, "blocked:affix-sandwich"
    if score >= threshold:
        return True, score, "jaro-winkler"
    return False, score, "below-threshold"


def _fuzzy_pass(
    group: list[dict],
    uf: _UnionFind,
    merges: list[EntityMerge],
    threshold: float,
) -> None:
    """Pass 2 — MinHash/LSH blocking then Jaro-Winkler verification."""
    candidates, norm_cache = _gather_candidates(group)
    if len(candidates) < _MIN_CANDIDATES_FOR_PAIRING:
        return
    lsh, minhashes = _build_lsh(candidates, norm_cache)
    for e in candidates:
        key = _merge_key(e)
        a_norm = norm_cache[key]
        for nbr_key in lsh.query(minhashes[key]):
            if nbr_key == key or uf.find(key) == uf.find(nbr_key):
                continue
            b_norm = norm_cache.get(nbr_key)
            if b_norm is None:
                continue
            ok, score, reason = _verify_pair(a_norm, b_norm, threshold)
            if ok:
                uf.union(key, nbr_key)
                merges.append(EntityMerge(key, nbr_key, score, reason))


def _build_remap(
    entities: list[dict], uf: _UnionFind
) -> tuple[dict[str, str], list[dict]]:
    """Turn union-find components into an alias→canonical remap + survivor list."""
    by_key: dict[str, dict] = {_merge_key(e): e for e in entities}
    remap: dict[str, str] = {}
    for members in uf.components().values():
        if len(members) <= 1:
            continue
        group_entities = [by_key[m] for m in members if m in by_key]
        if not group_entities:
            continue
        winner_key = _merge_key(_pick_winner(group_entities))
        for m in members:
            if m != winner_key:
                remap[m] = winner_key
    survivors = [e for e in entities if _merge_key(e) not in remap]
    return remap, survivors
