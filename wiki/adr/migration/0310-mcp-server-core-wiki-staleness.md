---
title: "ADR-0310 — mcp_server/core/wiki_staleness.py rationale"
status: accepted
source: mcp_server/core/wiki_staleness.py
---

# ADR-0310 — mcp_server/core/wiki_staleness.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
A page becomes stale when the file references it cites no longer
exist on disk. Stale pages get is_stale=True and lose heat faster
(half-life multiplier).
````

## module — original line 7 (docstring)

````text
Pure logic: this module is given a page's referenced file paths and
a per-path existence map (computed by the handler with filesystem
I/O), and returns the decision.
````

## module — original line 11 (docstring)

````text
Staleness signal sources:
  - claim_events.evidence_refs where kind='file' (most reliable)
  - Inline file-pattern matches in lead/sections (best-effort)
````

## module — original line 15 (docstring)

````text
ADR-0051 STEP 4 adds ``harvest_page_refs_typed`` / ``normalize_typed_refs``:
the staleness brake above only needs the *union* of referenced paths, but
persisting them as ``wiki.page_sources`` rows (link_kind='references')
needs per-path provenance (was this path cited by a claim, or only found
by best-effort regex in the body?) so downstream consumers can weigh the
two differently. ``harvest_page_refs`` is kept and now derives from the
typed variant rather than duplicating the merge logic.

````

## normalize_typed_refs — original line 177 (docstring)

````text
    ``wiki.page_sources.source_path`` must share the same canonical form
    across every link_kind (``mcp_server.shared.wiki_source_paths
    .normalize_source_path`` — the convention ``documents`` links already
    use) so the reverse index doesn't split one real file into two rows.
````

## module — original line 37 (comment)

````text
# A page must reference at least this many files for staleness to apply
# (avoid false positives from pages with one stray file mention).
````
