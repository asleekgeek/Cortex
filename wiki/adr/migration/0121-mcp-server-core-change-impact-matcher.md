---
title: "ADR-0121 — mcp_server/core/change_impact_matcher.py rationale"
status: accepted
source: mcp_server/core/change_impact_matcher.py
---

# ADR-0121 — mcp_server/core/change_impact_matcher.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 1 (docstring)

````text
Phase 4 (ADR-0046) — match code-change impact sets to memories.
````

## module — original line 3 (docstring)

````text
Given:
  * a set of impacted qualified names (from ``ap.detect_changes`` /
    ``ap.get_impact``),
  * a set of file paths touched by the commit,
  * an iterable of memory rows (``{memory_id, content, tags, ...}``),
````

## module — original line 9 (docstring)

````text
return a deterministic list of ``(memory_id, matched_terms)`` pairs
identifying memories whose content mentions any impacted symbol or file.
````

## module — original line 12 (docstring)

````text
Pure logic — no I/O. Case-insensitive substring match on the *content*
field plus tag intersection. The handler is responsible for deciding
what to do with the matches (heat bump, tag annotation, user report).

````

## match_memories — original line 59 (docstring)

````text
    The match is case-insensitive. Results are ordered by descending
    match_count then ascending id so the output is stable across runs.
    
````
