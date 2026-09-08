---
title: "ADR-0265 — mcp_server/core/staleness.py rationale"
status: accepted
source: mcp_server/core/staleness.py
---

# ADR-0265 — mcp_server/core/staleness.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Determines whether a stored memory is stale by examining the file references
it contains. Caller is responsible for resolving paths and checking existence;
this module only provides the logic to extract refs and score staleness.
````

## module — original line 7 (docstring)

````text
A memory is considered stale when:
  - It references files that no longer exist (hard stale)
  - It references files whose content has drifted significantly (soft stale)
  - Its content describes a state that contradicts current filesystem state
````

## module — original line 12 (docstring)

````text
No I/O performed here. Callers pass pre-resolved existence/change data.

````

## _build_staleness_reason — original line 143 (docstring)

````text
Build a human-readable staleness reason string.
````

## module — original line 32 (comment)

````text
# Matches backslash-separated paths — Windows relative (``src\core\x.py``)
# and drive-absolute (``C:\Users\me\x.py``). Without this, refs stored with
# backslashes are invisible to staleness detection on Windows.
# source: RAPPORT_INSTALLATION_CORTEX_WINDOWS.md §5.6
````

## module — original line 58 (comment)

````text
# Candidate paths at or above this length are rejected as non-filesystem
# strings.
# source: pre-existing tuned bound, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````

## module — original line 81 (comment)

````text
# Backslash paths are normalized to '/' so a single ref is stored
# regardless of the separator the author used; resolution works with
# forward slashes on every OS.
````

## module — original line 179 (comment)

````text
# Bug fix (I6-D6, found while wiring de-stale rehabilitation): a memory
# with ZERO missing/changed refs must never be stale, regardless of how
# strict `threshold` is set. The naive `score >= threshold` boundary
# broke at threshold=0.0 (the documented "flag anything with one
# missing reference" setting): score=0.0 >= threshold=0.0 was True for
# a memory whose refs ALL resolved, permanently blocking
# de-stale rehabilitation at that threshold. `score > 0` gates out the
# no-problem case without changing behavior for any threshold > 0
# (there, score=0 already implied score < threshold under the old
# formula too).
````
