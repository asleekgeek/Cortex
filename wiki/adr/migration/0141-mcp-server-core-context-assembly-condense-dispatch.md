---
title: "ADR-0141 — mcp_server/core/context_assembly/condense_dispatch.py rationale"
status: accepted
source: mcp_server/core/context_assembly/condense_dispatch.py
---

# ADR-0141 — mcp_server/core/context_assembly/condense_dispatch.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 1 (docstring)

````text
Generic memory condenser: dispatch by content shape (issue #228 split
4/4).
````

## module — original line 4 (docstring)

````text
Extracted from ``condensers.py`` (§4.1 — the original file was 391 lines,
over this repo's 300-line cap) with zero behaviour change. See
``condensers.py`` for the shared module docstring and re-export facade.

````

## _dispatch_by_tag — original line 54 (docstring)

````text
Explicit tag hints, checked before any content-shape heuristic.
````

## _dispatch_by_shape — original line 63 (docstring)

````text
Heuristic dispatch by content shape when no tag hint matched.
````

## module — original line 41 (comment)

````text
# EQUIVALENT MUTANT (#228): `<=` → `<`. Every route below opens with
# this same guard on this exact (content, token_budget) pair and
# returns content verbatim, so the boundary case agrees either way.
````
