"""Tabular (columns-once, rows-as-arrays) encoding for homogeneous MCP lists.

source: ADR-0280"""

from __future__ import annotations

from typing import Any

from mcp_server.core.response_budget import MAX_RESPONSE_CHARS, serialized_length

# The two self-describing encodings a response can declare under ``format``.
FORMAT_JSON = "json"
FORMAT_TABULAR = "tabular"

# source: ADR-0280


SELF_DESCRIBE_RESERVE_CHARS = len(',"format":"tabular"')


def reserved_budget(budget_chars: int) -> int:
    """The budget to hand ``bound_payload``.

    source: ADR-0280

    precondition: ``budget_chars`` is the host cap the final payload must not
    exceed. postcondition: returns ``budget_chars`` minus the worst-case
    ``format``-field cost (never below zero), so a payload bounded to the
    result still fits the cap once ``encode_within_budget`` appends its
    self-describing field.
    """
    return max(0, budget_chars - SELF_DESCRIBE_RESERVE_CHARS)


def parse_format(value: Any) -> str:
    """Normalize a caller-supplied ``format`` argument.

    precondition: none. postcondition: returns ``FORMAT_TABULAR`` iff
    ``value`` is exactly the string ``"tabular"``; every other value
    (including ``None`` and unknown strings) returns ``FORMAT_JSON`` — the
    unchanged default. An unknown format is not an error: it degrades to the
    richest encoding rather than rejecting the call.
    """
    return FORMAT_TABULAR if value == FORMAT_TABULAR else FORMAT_JSON


def derive_columns(items: list[dict]) -> list[str]:
    """The column header: the union of every item's keys, first-seen order.

    precondition: every element of ``items`` is a dict. postcondition: the
    result contains each key that appears in at least one item exactly once,
    ordered by first appearance while scanning items in order. First-seen
    (not sorted) order keeps the common case — a uniform list — presenting
    columns in the natural key order the producer emitted.
    """
    columns: list[str] = []
    seen: set[str] = set()
    for item in items:
        for key in item:
            if key not in seen:
                seen.add(key)
                columns.append(key)
    return columns


def encode_rows(items: list[dict], columns: list[str]) -> list[list[Any]]:
    """Project each item onto ``columns`` as a cell array.

    precondition: every element of ``items`` is a dict; ``columns`` is the
    output of ``derive_columns(items)`` (a superset of every item's keys).
    postcondition: returns one list per item, length ``len(columns)``, where
    cell ``j`` is ``item[columns[j]]`` if present else ``None``. Item order
    and cell order are preserved, so an upstream ranking or paging contract
    is untouched.
    """
    return [[item.get(col) for col in columns] for item in items]


def decode_tabular(columns: list[str], rows: list[list[Any]]) -> list[dict]:
    """Inverse of ``encode_rows`` — reconstruct the objects from the table.

    precondition: every row has length ``len(columns)``. postcondition:
    returns one dict per row mapping ``columns[j] -> row[j]``, so every field
    of every original item is recovered by column position (the
    no-information-loss guarantee; absent-in-original fields come back as the
    explicit ``None`` the encoder wrote). Used by round-trip tests and any
    client that prefers objects.
    """
    # strict=True: the documented precondition above already requires every
    # row to have length len(columns).
    return [dict(zip(columns, row, strict=True)) for row in rows]


def encode_within_budget(
    payload: dict,
    list_key: str,
    fmt: str,
    budget_chars: int = MAX_RESPONSE_CHARS,
) -> dict:
    """Self-describe ``payload`` and, when asked, tabularize its list.

    precondition: payload is a bounded dictionary in object form; fmt is
    a parse_format result.
    postcondition: always sets payload[format]. Nonempty dictionary lists
    use cell arrays and a columns header only when fmt is FORMAT_TABULAR
    and the encoded result fits budget_chars. Otherwise returns the object
    form with format=json.
    source: ADR-0280"""
    payload["format"] = FORMAT_JSON
    if fmt != FORMAT_TABULAR:
        return payload
    items = payload.get(list_key)
    if not isinstance(items, list) or not items:
        return payload
    if not all(isinstance(item, dict) for item in items):
        return payload
    columns = derive_columns(items)
    candidate = {
        **payload,
        list_key: encode_rows(items, columns),
        "columns": columns,
        "format": FORMAT_TABULAR,
    }
    if serialized_length(candidate) > budget_chars:
        return payload
    return candidate
