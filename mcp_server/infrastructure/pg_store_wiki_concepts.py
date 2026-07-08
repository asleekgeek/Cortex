"""wiki.concepts DB operations.

Split out of ``pg_store_wiki.py`` (originally 890 lines, over the
300-line file limit — CLAUDE.md "Code Quality Rules") purely for size
compliance; no logic changed.

Pure infrastructure — no core imports, no handler imports.
"""

from __future__ import annotations

import json
from typing import Any

from psycopg import Connection
from psycopg.rows import dict_row

from mcp_server.infrastructure.pg_store_wiki_common import _returning_id


def list_concepts(
    conn: Connection,
    *,
    status: str | None = None,
    limit: int = 200,
) -> list[dict]:
    """Return concept rows, optionally filtered by status."""
    if status:
        sql = "SELECT * FROM wiki.concepts WHERE status = %s ORDER BY id LIMIT %s"
        params: tuple = (status, limit)
    else:
        sql = "SELECT * FROM wiki.concepts ORDER BY id LIMIT %s"
        params = (limit,)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, params)
        return list(cur.fetchall())


def get_concepts_by_entity_overlap(
    conn: Connection, entity_ids: list[int]
) -> list[dict]:
    """Return concepts whose entity_ids intersect the given list."""
    if not entity_ids:
        return []
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT * FROM wiki.concepts WHERE entity_ids && %s::int[]",
            (list(entity_ids),),
        )
        return list(cur.fetchall())


def insert_concept(conn: Connection, concept: dict[str, Any]) -> int:
    """Insert a new concept. Returns wiki.concepts.id."""
    sql = """
    INSERT INTO wiki.concepts (
        label, status, entity_ids, grounding_memory_ids,
        grounding_claim_ids, properties, axial_slots,
        saturation_rate, saturation_streak
    ) VALUES (
        %(label)s, %(status)s, %(entity_ids)s::int[],
        %(grounding_memory_ids)s::int[], %(grounding_claim_ids)s::bigint[],
        %(properties)s::jsonb, %(axial_slots)s::jsonb,
        %(saturation_rate)s, %(saturation_streak)s
    ) RETURNING id;
    """
    params = {
        "label": concept["label"],
        "status": concept.get("status", "candidate"),
        "entity_ids": concept.get("entity_ids", []),
        "grounding_memory_ids": concept.get("grounding_memory_ids", []),
        "grounding_claim_ids": concept.get("grounding_claim_ids", []),
        "properties": json.dumps(concept.get("properties", {})),
        "axial_slots": json.dumps(concept.get("axial_slots", {})),
        "saturation_rate": float(concept.get("saturation_rate", 1.0)),
        "saturation_streak": int(concept.get("saturation_streak", 0)),
    }
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return _returning_id(cur.fetchone())


def update_concept(conn: Connection, concept_id: int, fields: dict[str, Any]) -> bool:
    """Patch a concept row. Returns True if updated."""
    if not fields:
        return False
    sets: list[str] = []
    params: list = []
    for k, v in fields.items():
        if k in ("entity_ids", "grounding_memory_ids"):
            sets.append(f"{k} = %s::int[]")
            params.append(v)
        elif k == "grounding_claim_ids":
            sets.append(f"{k} = %s::bigint[]")
            params.append(v)
        elif k in ("properties", "axial_slots"):
            sets.append(f"{k} = %s::jsonb")
            params.append(json.dumps(v))
        elif k == "last_property_at":
            sets.append(f"{k} = NOW()")
        else:
            sets.append(f"{k} = %s")
            params.append(v)
    params.append(concept_id)
    sql = f"UPDATE wiki.concepts SET {', '.join(sets)} WHERE id = %s"
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.rowcount > 0
