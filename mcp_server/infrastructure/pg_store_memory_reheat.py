"""``memories`` deliberate-heat recalibration — DB operations (I6-D5,
INC6.6).

Finds active deliberate memories (source NOT IN the auto-capture/
mechanical set — the exact I6 audit definition, ``inc6-audit-outils-
memoire.md`` §"État des lieux corpus": "Délibérées actives
(feature/lesson/bug-fix/decision/...)") whose ``effective_heat`` sits
below the measured retrieval cliff, and probes each row's own
``effective_heat`` at ``heat_base=1.0`` so ``core.memory_reheat`` can
compute the exact minimal raise (see that module's docstring for the
derivation). Split into its own module for the same reason as
``pg_store_memory_dedup.py``/``pg_store_memory_domain.py`` (I6-D1/D3
precedent): one focused infrastructure file per campaign pass, under the
size cap.

Pure infrastructure — no core imports, no handler imports.
"""

from __future__ import annotations

from psycopg import Connection
from psycopg.rows import dict_row

# Deliberate = everything that is NOT an auto-capture or mechanical write
# path. Exact list from the I6-D5 acceptance-criterion SQL (design doc
# §I6-D5) and the I6 audit's corpus table ("Auto-capturées actives
# (post_tool_capture)" / "Backfill / mécaniques (codebase_analyze, seed,
# ingest, cls)" rows) — the audit's own boundary between "délibérées" and
# everything else.
_AUTO_AND_MECHANICAL_SOURCES = (
    "post_tool_capture",
    "codebase_analyze",
    "seed",
    "ingest",
    "cls",
)

# Per-run scan cap on candidate rows. The I6 audit measured 542 deliberate
# active rows on 2026-07-10; re-measured 750 at run time post-6.3 dedup
# (corpus grows). Comfortably above either count in one pass.
DEFAULT_REHEAT_SCAN_LIMIT = 5000


def list_deliberate_below_target(
    conn: Connection, target: float, limit: int
) -> list[dict]:
    """Every active deliberate memory whose ``effective_heat`` < ``target``.

    Pre-condition:  ``target`` is the campaign's cliff target (0.25,
                    ``core.memory_reheat.DEFAULT_REHEAT_TARGET``);
                    ``limit`` bounds the number of rows scanned.
    Post-condition: returns one dict per matching row: ``id``,
                    ``heat_base`` (current, REAL), ``effective_heat``
                    (computed with the row's own domain's homeostatic
                    factor, COALESCE'd to 1.0 for domains with no
                    ``homeostatic_state`` row — matching
                    ``list_exact_duplicate_groups``'s convention),
                    ``effective_heat_at_max`` (the SAME function
                    re-evaluated on a clone of the row with ``heat_base``
                    overridden to 1.0 via
                    ``jsonb_populate_record(NULL::memories, to_jsonb(c) ||
                    jsonb_build_object('heat_base', 1.0))`` — the
                    standard Postgres "clone a composite row with one
                    field changed" pattern, robust to schema changes
                    since it never lists the ``memories`` column set
                    explicitly). Scope: ``current_memories`` (chain heads
                    only) ``WHERE NOT is_stale AND source NOT IN``
                    the auto/mechanical set — the exact I6-D5
                    acceptance-criterion population. The ``candidates``
                    CTE re-projects ``m.*`` before calling
                    ``effective_heat()`` for the same reason
                    ``pg_store_memory_dedup.py`` documents: ``current_
                    memories`` is a VIEW with its own composite type that
                    Postgres will not implicitly cast to ``memories``.
    """
    sql = """
        WITH candidates AS (
            SELECT m.*
              FROM current_memories m
             WHERE NOT m.is_stale
               AND NOT (m.source = ANY(%(sources)s))
        ),
        probed AS (
            SELECT c.id,
                   c.heat_base::REAL AS heat_base,
                   effective_heat(c, NOW(), COALESCE(hs.factor, 1.0)::REAL)
                       AS effective_heat,
                   effective_heat(
                       jsonb_populate_record(
                           NULL::memories,
                           to_jsonb(c) || jsonb_build_object('heat_base', 1.0)
                       )::memories,
                       NOW(), COALESCE(hs.factor, 1.0)::REAL
                   ) AS effective_heat_at_max
              FROM candidates c
         LEFT JOIN homeostatic_state hs ON hs.domain = c.domain
        )
        SELECT id, heat_base, effective_heat, effective_heat_at_max
          FROM probed
         WHERE effective_heat < %(target)s
         ORDER BY id
         LIMIT %(limit)s
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            sql,
            {
                "sources": list(_AUTO_AND_MECHANICAL_SOURCES),
                "target": target,
                "limit": limit,
            },
        )
        return list(cur.fetchall())


def apply_reheat(
    conn: Connection, memory_id: int, old_heat_base: float, new_heat_base: float
) -> bool:
    """Raise ``memory_id``'s ``heat_base`` to ``new_heat_base``, CAS-guarded.

    Pre-condition:  ``new_heat_base > old_heat_base`` (the caller —
                    ``core.memory_reheat.compute_reheat_target`` — never
                    returns a decision with ``changed=True`` otherwise;
                    this function does not re-derive the target, only
                    writes it).
    Post-condition: if ``memory_id``'s ``heat_base`` is STILL exactly
                    ``old_heat_base`` at write time, it is set to
                    ``new_heat_base`` and this returns True. Otherwise
                    (a concurrent writer already changed ``heat_base``
                    between this campaign's scan and this write — a
                    consolidation decay tick, another campaign run, a
                    user ``rate_memory`` update, etc.) nothing is written
                    and this returns False, so the caller can count it as
                    a skipped race rather than silently overwriting a
                    concurrent change. Never touches
                    ``heat_base_set_at``, ``consolidation_stage``, or any
                    other column — deliberately does NOT reset the decay
                    clock (I6-D5: this is a ``heat_base`` recalibration,
                    not an ``anchor``-style protection; the row keeps
                    decaying from its existing timeline, which is exactly
                    what the campaign's J+30 re-measurement is designed
                    to observe).
    """
    # ::REAL cast on old_heat_base is not stylistic — psycopg sends a
    # Python float as a double-precision parameter; comparing the REAL
    # (float4) column directly to that double literal fails even for a
    # value round-tripped from the SAME column read moments earlier
    # (e.g. observed 0.1::real widened to double != Python's 0.1 double
    # literal — float4 0.1 and float8 0.1 are different bit patterns).
    # Casting the parameter back down to REAL before comparing makes both
    # sides the same float4 value the column actually stores, so the CAS
    # check only fails on a genuine concurrent change, never on a false
    # precision mismatch.
    with conn.cursor() as cur:
        cur.execute(
            """UPDATE memories
                  SET heat_base = %(new_heat_base)s
                WHERE id = %(memory_id)s
                  AND heat_base = %(old_heat_base)s::REAL""",
            {
                "memory_id": memory_id,
                "old_heat_base": old_heat_base,
                "new_heat_base": new_heat_base,
            },
        )
        return cur.rowcount > 0


__all__ = [
    "DEFAULT_REHEAT_SCAN_LIMIT",
    "list_deliberate_below_target",
    "apply_reheat",
]
