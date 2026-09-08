---
title: "ADR-0161 — mcp_server/core/document_model.py rationale"
status: accepted
source: mcp_server/core/document_model.py
---

# ADR-0161 — mcp_server/core/document_model.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Pure core (zero I/O): every type here is a plain in-memory value object.
Both document adapters (docx via ``core.docx_parser``, Confluence storage
format via ``core.confluence_parser``) parse the bytes/strings they are
handed into a :class:`ParsedDocument`; :func:`core.document_normalizer`
turns that single shape into the wiki page + memory payloads the existing
``wiki_write``/``remember`` path already consumes.
````

## module — original line 10 (docstring)

````text
This is the seam the live-Confluence REST connector (enterprise-backlog#28,
OUT of scope here) is built to reuse: that connector fetches storage-format
XHTML over REST and hands the string to ``confluence_parser`` →
``ParsedDocument`` → ``document_normalizer`` → the same write path, with a
:class:`DocumentProvenance` carrying the page URL + version instead of a
file path + content hash. No parsing/normalization logic is duplicated for
the live leg — only the byte-source (file read vs REST fetch) differs, and
that lives in infrastructure/handlers, never here.

````

## DocumentParseError — original line 28 (docstring)

````text
    A loud failure by design (issue #192 edge case: malformed XML must
    surface a hard error, never a partial silent write). The handler maps
    this to an ``{"ingested": false, ...}`` response BEFORE any wiki page or
    memory is written, so a malformed document leaves the store untouched.
    
````

## DocumentTable — original line 37 (docstring)

````text
A table extracted from a document: a list of rows, each a list of
    cell strings. The header row (if any) is simply ``rows[0]`` — the model
    does not distinguish it, the renderer does.
````

## DocumentSection — original line 48 (docstring)

````text
    ``level`` is the heading depth (0 = document preamble text that appears
    before the first heading; 1 = top-level heading, 2 = subheading, ...).
    ``body`` is the concatenated paragraph text under the heading (tables
    excluded — those are carried structurally in ``tables`` so the renderer
    can emit real markdown tables rather than flattened text).
````

## document_section_is_empty — original line 61 (docstring)

````text
True when the section carries no body text and no tables — a
    headings-only section (issue #192 edge case). The renderer still
    emits the heading; the memory writer skips empty sections so a bare
    heading does not become a contentless memory.
````

## document_section_is_empty — original line 66 (docstring)

````text
    A free function, not a method: mutmut categorically excludes the body
    of any `@dataclass`-decorated class (`mutmut/mutation/file_mutation.py:
    236`), so logic placed on `DocumentSection` methods would carry zero
    mutation coverage no matter how the test loader names the module
    (issue #262 3rd pass; issue #282).
    
````

## ParsedDocument — original line 79 (docstring)

````text
    ``image_count`` is the number of embedded images detected and
    deliberately NOT ingested (issue #192 non-goal: no OCR / no image
    extraction). It drives the explicit skip notice (F1) — a non-zero count
    is surfaced to the caller, never silently dropped.
    
````

## parsed_document_is_empty — original line 91 (docstring)

````text
True when the document yielded no text and no tables at all
    (issue #192 edge case: empty doc). Distinct from a malformed doc,
    which raises :class:`DocumentParseError` instead.
````

## DocumentProvenance — original line 104 (docstring)

````text
    ``source`` is a file path (export ingestion) or a page URL (the live
    REST connector, enterprise-backlog#28). ``version`` is a content hash
    for files (so re-ingesting an unchanged file is idempotent) or the
    Confluence page version number for the live leg. ``source_kind`` is one
    of ``"docx"`` / ``"confluence-export"`` / ``"confluence-api"`` — the
    tag prefix that lets ``recall``/staleness treat documents the way they
    treat code references.
````

## document_provenance_dedup_tag — original line 120 (docstring)

````text
    A prior ingestion of the same ``(source, version)`` carries this
    exact tag; the handler checks for it and skips re-writing (§13.1-A6
    idempotent re-ingest). A NEW version produces a different tag, so an
    updated document is re-ingested rather than silently ignored.
````

## document_provenance_source_tag — original line 131 (docstring)

````text
Version-independent tag anchoring every memory to this source, so
    all ingested versions of one document are recall-linkable.
````
