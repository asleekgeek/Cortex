---
title: "ADR-0230 — mcp_server/core/prospective.py rationale"
status: accepted
source: mcp_server/core/prospective.py
---

# ADR-0230 — mcp_server/core/prospective.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
"Remember to do X when Y happens" — the ability to remember intentions.
````

## module — original line 5 (docstring)

````text
Trigger types:
  - directory_match: fires when working in a specific directory
  - keyword_match: fires when content contains specific keywords
  - entity_match: fires when specific entities appear
  - time_based: fires at specific times (HH:MM or weekday:N)
````

## module — original line 11 (docstring)

````text
Auto-extraction detects prospective intent from natural language:
  - "TODO: ...", "FIXME: ...", "remember to ...", "next time ..."
  - "don't forget ...", "when we ...", "later ...", "should also ..."
````

## module — original line 15 (docstring)

````text
Pure business logic — no I/O.

````

## module — original line 51 (comment)

````text
# Preference constraints: "Prefer X over Y", "Use X instead of Y"
````

## module — original line 66 (comment)

````text
# Actionable phrases shorter than this are noise.
# source: pre-existing tuned value, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````

## module — original line 71 (comment)

````text
# Keywords of length <= 2 are ignored as noise.
# source: pre-existing tuned value, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````

## module — original line 124 (comment)

````text
# Word-boundary match, not substring containment: the pre-2026-06-10
# `kw in content_lower` fired "ask" on "task" — with 317 harvested
# triggers active, nearly every recall query matched something.
# Correctness fix, not tuning.
# See docs/provenance/bounded-io-phase2-design.md M1.
````
