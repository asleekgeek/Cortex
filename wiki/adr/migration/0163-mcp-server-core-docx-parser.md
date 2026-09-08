---
title: "ADR-0163 — mcp_server/core/docx_parser.py rationale"
status: accepted
source: mcp_server/core/docx_parser.py
---

# ADR-0163 — mcp_server/core/docx_parser.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Zero I/O: this module is handed the already-unzipped ``word/document.xml``
string (the zip unpacking is infrastructure — ``infrastructure.document_
reader``) and turns it into a :class:`ParsedDocument`. Stdlib only
(``xml.etree.ElementTree`` parses an in-memory string — pure computation,
not I/O), so no heavyweight dependency (python-docx) is pulled in — issue
#192 §8: "Pure-Python parsing (zipfile + XML — no new heavyweight
dependency)."
````

## module — original line 11 (docstring)

````text
WordprocessingML shape actually parsed (source: ECMA-376 Part 1, §17
"WordprocessingML", the OOXML spec; namespace ``w`` =
http://schemas.openxmlformats.org/wordprocessingml/2006/main):
  - ``w:body`` holds block-level children in document order: ``w:p``
    (paragraphs) and ``w:tbl`` (tables).
  - A paragraph's style is ``w:p/w:pPr/w:pStyle@w:val``; the built-in
    heading styles are ``Heading1``..``Heading9`` and ``Title`` (§17.7.4).
  - Text lives in ``w:t`` runs; ``w:tab`` / ``w:br`` are whitespace.
  - Embedded images appear as ``w:drawing`` (DrawingML, §20.4) or the
    legacy ``w:pict`` (VML) — counted, never extracted (issue #192
    non-goal: no image ingestion).

````

## _count_images — original line 101 (docstring)

````text
Count embedded images (``w:drawing`` + legacy ``w:pict``) in the
    whole document — these are skipped, not ingested (issue #192).
````

## module — original line 43 (comment)

````text
# §12 note: several mutants here are EQUIVALENT because the input domain is
# fixed — ElementTree tags for OOXML are always the single-'}' form
# ``{uri}local`` (namespace URIs never contain '}'). So split==rsplit,
# maxsplit 1==2==unbounded, and the result list always has exactly two
# elements, making [-1]==[1]. None of those variants change the output.
````

## module — original line 73 (comment)

````text
# §12 note: the ``or ""`` → ``or "XXXX"`` mutant is EQUIVALENT — when a
# pStyle carries no w:val, both the empty string and the sentinel fail the
# ``title``/Heading regex below, so both fall through to "body text" (None).
````

## module — original line 143 (comment)

````text
# ``Title`` style names the document; it is not a section
# heading (that would duplicate the page's own title). Text
# continues under the current section.
````
