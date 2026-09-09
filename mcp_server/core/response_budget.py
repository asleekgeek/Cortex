"""Bounded MCP responses — total payload budget with per-item truncation.

source: ADR-0246"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any

# source: ADR-0246
# source: ADR-0246
HOST_CAP_CHARS = 100_000

# source: ADR-0246
# source: ADR-0246
SAFETY_FACTOR = 0.75

MAX_RESPONSE_CHARS = int(HOST_CAP_CHARS * SAFETY_FACTOR)


@dataclass(frozen=True)
class ListTarget:
    """A list of dict items under ``payload[key]``, each carrying a text
    field at ``content_key`` that may be truncated.

    ``weight_key`` names a positive-number field used as the item's
    truncation priority (higher = keeps more content). ``None`` means
    equal shares."""

    key: str
    content_key: str = "content"
    weight_key: str | None = None


@dataclass(frozen=True)
class TextTarget:
    """A single string field at ``payload[key]`` that may be truncated."""

    key: str


@dataclass
class _Cell:
    """One truncatable text plus the bookkeeping keys written on cut."""

    container: dict
    content_key: str
    flag_key: str
    length_key: str
    weight: float = 1.0


def serialized_length(payload: Any) -> int:
    """Compact JSON code-point count used by this legacy allocation policy.

    source: ADR-0246
    """
    return len(
        json.dumps(payload, separators=(",", ":"), ensure_ascii=False, default=str)
    )


def bound_payload(
    payload: dict,
    targets: list[ListTarget | TextTarget],
    budget_chars: int = MAX_RESPONSE_CHARS,
) -> dict:
    """Mutate ``payload`` in place until it serializes within budget.

    source: ADR-0246"""
    while True:
        total = serialized_length(payload)
        if total <= budget_chars:
            return payload
        cells = _collect_cells(payload, targets)
        cuttable = [c for c in cells if len(c.container.get(c.content_key) or "") > 0]
        if cuttable:
            _truncate_cells(cuttable, total - budget_chars)
            continue
        if not _drop_tail_item(payload, targets):
            return payload


def _collect_cells(
    payload: dict, targets: list[ListTarget | TextTarget]
) -> list[_Cell]:
    cells: list[_Cell] = []
    for target in targets:
        if isinstance(target, TextTarget):
            if isinstance(payload.get(target.key), str):
                cells.append(
                    _Cell(
                        container=payload,
                        content_key=target.key,
                        flag_key=f"{target.key}_truncated",
                        length_key=f"{target.key}_length",
                    )
                )
            continue
        items = payload.get(target.key)
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict) and isinstance(item.get(target.content_key), str):
                cells.append(
                    _Cell(
                        container=item,
                        content_key=target.content_key,
                        flag_key="truncated",
                        length_key=f"{target.content_key}_length",
                        weight=_priority_weight(item, target.weight_key),
                    )
                )
    return cells


def _priority_weight(item: dict, weight_key: str | None) -> float:
    """Item's truncation priority; degenerate values fall back to 1.0
    (equal share — the unweighted behavior, not an invented constant)."""
    if weight_key is None:
        return 1.0
    value = item.get(weight_key)
    if isinstance(value, (int, float)) and math.isfinite(value) and value > 0:
        return float(value)
    return 1.0


def _flag_cost(cell: _Cell) -> int:
    """Exact serialized chars added when a cell is first marked truncated."""
    cost = 0
    if not cell.container.get(cell.flag_key):
        cost += len(f',"{cell.flag_key}":true')
    if cell.length_key not in cell.container:
        content = cell.container.get(cell.content_key) or ""
        cost += len(f',"{cell.length_key}":') + len(str(len(content)))
    return cost


def _truncate_cells(cells: list[_Cell], overflow: int) -> None:
    """Weighted water-fill: cut contents down to a common per-weight level L — each
    cell keeps up to ``floor(L × weight)`` chars.

    source: ADR-0246
    """
    needed = overflow + sum(_flag_cost(c) for c in cells)
    pairs = [(len(c.container[c.content_key]), c.weight) for c in cells]
    level = _water_level(pairs, needed)
    for cell in cells:
        content = cell.container[cell.content_key]
        allowed = int(level * cell.weight)
        if len(content) <= allowed:
            continue
        cell.container[cell.flag_key] = True
        # source: ADR-0246

        cell.container.setdefault(cell.length_key, len(content))
        cell.container[cell.content_key] = content[:allowed]


def _water_level(pairs: list[tuple[int, float]], needed: int) -> float:
    """Largest common level L ≥ 0 with
    ``sum(max(0, length - L*weight)) >= needed``.

    Weighted max-min fairness: cells whose length exceeds L×weight are
    cut to it, the rest are untouched. Equal weights make this plain
    water-filling. Returns 0 when even emptying everything cannot free
    ``needed`` chars.
    """
    if not pairs or needed <= 0:
        return max((length / weight for length, weight in pairs), default=0.0)
    desc = sorted(pairs, key=lambda p: p[0] / p[1], reverse=True)
    freed = 0.0
    active_weight = 0.0
    for i, (length, weight) in enumerate(desc):
        ratio = length / weight
        active_weight += weight
        nxt = desc[i + 1] if i + 1 < len(desc) else None
        next_ratio = nxt[0] / nxt[1] if nxt else 0.0
        capacity = active_weight * (ratio - next_ratio)
        if freed + capacity >= needed:
            return ratio - (needed - freed) / active_weight
        freed += capacity
    return 0.0


def _drop_tail_item(payload: dict, targets: list[ListTarget | TextTarget]) -> bool:
    """Drop one item from the tail of the longest target list.

    source: ADR-0246"""
    longest: list | None = None
    for target in targets:
        if isinstance(target, ListTarget):
            items = payload.get(target.key)
            if isinstance(items, list) and items:
                if longest is None or len(items) > len(longest):
                    longest = items
    if longest is None:
        return False
    longest.pop()
    payload["truncation_dropped"] = payload.get("truncation_dropped", 0) + 1
    return True
