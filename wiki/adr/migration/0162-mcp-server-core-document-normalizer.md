---
title: "ADR-0162 — mcp_server/core/document_normalizer.py rationale"
status: accepted
source: mcp_server/core/document_normalizer.py
---

# ADR-0162 — mcp_server/core/document_normalizer.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 4 (docstring)

````text
Zero I/O: builds strings and plain payload dicts; the handler performs the
actual ``wiki_write``/``remember`` writes. This is the single place a parsed
document (from ANY adapter — docx, Confluence export, or the live REST
connector of enterprise-backlog#28) becomes the shapes the existing memory/
wiki path already understands, so document ingestion rides the same
staleness/validation machinery as code references (issue #192).

````

## NormalizedDocument — original line 41 (docstring)

````text
    ``notices`` carries human-readable, caller-surfaced signals — chiefly the
    skipped-image notice (issue #192 F1: never silent) and the empty-document
    notice. ``image_count`` is echoed so the handler can assert emission.
````

## normalize_document — original line 128 (mixed-contract-rationale)

````text
    Precondition:  ``doc`` is a parsed document (possibly empty); ``prov``
                   identifies its source and version.
    Postcondition: returns a :class:`NormalizedDocument`. Every produced
                   payload — the wiki markdown frontmatter and every memory —
                   carries the provenance source + version (issue #192:
                   provenance on every produced page/memory). A non-zero
                   ``doc.image_count`` yields an explicit skipped-image notice
                   (F1). An empty document yields a page + empty notice and no
                   section memories (edge case: empty doc). Headings-only
                   sections render their heading but produce no memory.
    
````

## module — original line 54 (comment)

````text
# §12 note: the mutant that widens ``.strip("-")`` to ``.strip("X-")`` is
# EQUIVALENT — ``slug`` is already lowercased and contains only [a-z0-9-],
# so no 'X' can ever be at a boundary; both strip exactly the same chars.
````
