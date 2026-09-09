---
title: "ADR-0299 — mcp_server/core/wiki_curation_gaps.py rationale"
status: accepted
source: mcp_server/core/wiki_curation_gaps.py
---

# ADR-0299 — mcp_server/core/wiki_curation_gaps.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
User direction 2026-05-18: *"Removing is not a solution, fixing the
curation by showing information that should be present and missing for
each file is a curation of the documentation."*
````

## module — original line 7 (docstring)

````text
This module is the operationalisation of that policy. Given a wiki
page (typically a per-source-file reference), it identifies which
sections SHOULD be present for a real curated explanation and which
are absent. The list of missing sections is:
````

## module — original line 12 (docstring)

````text
  1. Embedded in the page frontmatter as ``curation_gaps: [...]``.
  2. Rendered prominently at the top of the page by the wiki view.
  3. Queued as re-author jobs by the auto-curator so the in-session
     LLM fills the gaps over time.
````

## module — original line 17 (docstring)

````text
Nothing here deletes content. Pages with gaps stay on disk; the gaps
are surfaced so the reader knows what's coming and the author knows
what to write.
````

## module — original line 21 (docstring)

````text
Pure logic — no I/O. Callers pass body text + frontmatter dict.

````

## render_gap_banner — original line 349 (docstring)

````text
    The banner lists every missing section with its description so the
    reader sees concretely what's not yet written and the LLM (or human
    author) knows exactly what to add next. Empty string when the page
    is complete.
    
````

## module — original line 54 (comment)

````text
# Sections every file-doc must cover. The list is deliberately stable —
# adding/removing a section is a deliberate policy edit, not an emergent
# property of the audit.
````
