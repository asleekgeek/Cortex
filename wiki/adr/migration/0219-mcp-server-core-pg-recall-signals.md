---
title: "ADR-0219 — mcp_server/core/pg_recall_signals.py rationale"
status: accepted
source: mcp_server/core/pg_recall_signals.py
---

# ADR-0219 — mcp_server/core/pg_recall_signals.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Split from pg_recall.py (continuing the two documented seams cut at #368 —
pg_recall_weights.py / pg_recall_assembly.py — with a third) to bring
pg_recall.py under this repo's local 300-line file cap and 40-line method
cap (docs/agent-guidance.md § Code Style; a tightening of
coding-standards.md §4.1/§4.2).
````

## module — original line 9 (docstring)

````text
Every reader here is defensive: it duck-types against an optional method on
``store`` and returns the neutral "no signal" value (``EMPTY_GOAL`` / ``None``)
rather than fabricating one when the method is absent or the read fails —
per the zetetic source-discipline rule (coding-standards.md §8).

````

## _get_active_goal — original line 37 (docstring)

````text
    Defensive reader mirroring ``_get_user_mood``: looks for
    ``get_active_prospective_memories()`` on the store (the same method
    query_methodology uses to fire triggers) and promotes the returned trigger
    dicts into a ``goal_maintenance.GoalVector`` — the held task-set that biases
    this recall toward goal-relevant memories (Miller & Cohen 2001).
````

## _get_user_mood — original line 61 (docstring)

````text
    Looks for an explicit ``get_user_mood()`` method on the store. There is
    no such method in the current ``PgMemoryStore`` (April 2026), so this
    helper returns ``None`` and the MOOD_CONGRUENT_RERANK stage no-ops —
    per the zetetic source-discipline rule we do NOT fabricate a mood signal.
    When an upstream emotion classifier or manual checkpoint annotation
    populates a mood store, expose ``get_user_mood()`` and this helper
    will start returning real values without further wiring changes.
    
````

## inline — original line 53 (directive-rationale)

````text
# noqa: BLE001 — non-load-bearing; absence is fine
````

## inline — original line 75 (directive-rationale)

````text
# noqa: BLE001 — non-load-bearing; absence is fine
````
