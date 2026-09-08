---
title: "ADR-0316 — mcp_server/core/wiki_thermodynamics.py rationale"
status: accepted
source: mcp_server/core/wiki_thermodynamics.py
---

# ADR-0316 — mcp_server/core/wiki_thermodynamics.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Pages live in an ecology, not a library: they earn existence through
citation and access, lose it through idleness, staleness, and
redundancy. This module is the pure-logic layer that decides:
````

## module — original line 7 (docstring)

````text
  - how much heat a page decays per tick
  - when a page transitions between lifecycle_states
  - when a page gets archived
````

## module — original line 11 (docstring)

````text
Same physics as pg_store memory decay, with lifecycle-aware half-lives:
````

## module — original line 13 (docstring)

````text
  active     half-life 30d   — current cognitive territory
  area       half-life 90d   — ongoing reference, touched occasionally
  archived   no decay        — already at floor
  evergreen  no decay        — protected (cross-domain knowledge)
````

## module — original line 18 (docstring)

````text
Pure logic — no I/O. The handler reads pages, calls these helpers,
writes back the new (heat, lifecycle_state, is_stale, archived_at).

````

## transition_lifecycle — original line 115 (docstring)

````text
    Returns (new_state, transitioned, rationale).
    
````

## module — original line 38 (comment)

````text
# Lifecycle transition thresholds.
#
# source: none — engineering default, calibration pending. No published
# paper or measured benchmark backs these four cut points (searched:
# docs/provenance/, git log -S on this file back to origin 9b7bf2d0
# "feat(wiki redesign): Phase 4 — Thermodynamics", no ADR). The HALF_LIFE_DAYS
# values above and the module docstring's "same physics as pg_store memory
# decay" claim cover the *decay* mechanism (exponential half-life), not
# these lifecycle *transition* cut points — that claim does not extend a
# source to ACTIVE_TO_AREA_HEAT/AREA_TO_ARCHIVED_HEAT/ARCHIVED_REVIVAL_HEAT.
# Same unsourced-engineering-default family as core/reconsolidation.py's
# _RECONS_HEAT_BUMP_* constants and the wiki citation heat bump
# (infrastructure/pg_schema.py WIKI_TRIGGERS_DDL, cfd8e4c3). See
# docs/provenance/blend-weight-calibration.md for the procedural precedent
# this codebase follows to graduate a placeholder like these to a cited,
# measured value (that document itself does not cover these constants).
# No behavior change: comment-only addition, values unchanged.
````

## inline — original line 59 (comment)

````text
# re-promote on citation bump above this
````

## module — original line 150 (comment)

````text
# Revival happens via citation trigger (bumps heat directly);
# if heat already crossed the threshold we re-promote.
````

## module — original line 236 (comment)

````text
# Build label like "active->area" — caller supplies prior state
# via original_heats? No — we only have new_lifecycle here.
# Use just the destination state for simplicity.
````

## module — original line 263 (comment)

````text
# re-exported so tests don't need a separate import
````
