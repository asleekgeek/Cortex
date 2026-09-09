---
title: "ADR-0317 — mcp_server/core/wiki_title.py rationale"
status: accepted
source: mcp_server/core/wiki_title.py
---

# ADR-0317 — mcp_server/core/wiki_title.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Extracted from ``wiki_classifier.py`` (issue #134, file exceeded the
500-line hard limit in coding-standards.md §4). Deriving a title is a
distinct concern from classifying content into a kind: it only needs
the content, the already-decided kind, and optionally tags/entities.

````

## derive_title — original line 88 (docstring)

````text
    Strategy (inspired by Alexander pattern-language P4 + Eco; framing only):
    1. Strip known prefixes
    2. Walk lines; accept the first that passes ``_line_is_title_candidate``
    3. Fall back to entity-based title if 2+ entities are supplied
    4. Otherwise return "" — caller is responsible for a deterministic
       fallback (e.g. ``memory-<hash>``). Returning a raw 80-char content
       prefix here used to leak filesystem paths, timestamps, and sentence
       fragments into slugs.
    
````

## module — original line 30 (comment)

````text
# 2026-05-17: markdown unwrappers. Applied with ``sub(r"\1", ...)`` (keep
# inner text) before the path-detection patterns so a line like
# ``**File:** `/Users/.../remember.py` `` is tested against the path
# detector as ``File: /Users/.../remember.py`` — previously the backtick
# before ``/Users/`` wasn't whitespace so the path filter missed and the
# raw markdown-wrapped path leaked into the wiki page title.
````

## module — original line 44 (comment)

````text
# Lines at or below this length are too short to serve as a page title.
# source: pre-existing tuned value, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````

## module — original line 49 (comment)

````text
# Titles longer than this are truncated to a word boundary before the ellipsis.
# source: pre-existing tuned value, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````

## module — original line 54 (comment)

````text
# An entity-derived title joins this many leading entities.
# source: structural — the title is built as "A + B" from entities[:2]
````

## module — original line 101 (comment)

````text
# Unwrap markdown formatting first so the underlying text is
# what gets prefix-stripped and tested. Without this step,
# ``**File:** `/path` `` keeps its asterisks/backticks, the
# backtick blocks the path detector at line 178 from matching
# the embedded ``/Users/`` segment, and the raw markdown leaks
# through as the page title.
````
