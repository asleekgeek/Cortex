---
title: "ADR-0295 — mcp_server/core/wiki_classifier_gates.py rationale"
status: accepted
source: mcp_server/core/wiki_classifier_gates.py
---

# ADR-0295 — mcp_server/core/wiki_classifier_gates.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Extracted from ``wiki_classifier.py`` (issue #134, file exceeded the
500-line hard limit in coding-standards.md §4). These are the pure
functions the legacy-kind router (``wiki_classifier._classify_to_legacy_kind``)
calls to decide whether content is admitted to the wiki, before routing
it to a kind. No I/O, no globals — pattern tables live in
``wiki_classifier_patterns.py``.

````

## positive_score — original line 92 (docstring)

````text
    Signals (8 total):
      1. Multiple structural elements (heading/list/code)
      2. Contains declarative claim-shaped sentences
      3. Cites paper, ADR, URL, or function/file reference
      4. Minimum substantive length (≥ 200 chars)
      5. Has curated/knowledge tag
      6. Is atomic (not too long, not too short) — 200-3000 chars
      7. Domain vocabulary density — at least 3 distinct technical tokens
      8. References files or code entities
    
````

## module — original line 73 (comment)

````text
# At least this many declarative claims are needed to earn the claims point.
# source: pre-existing tuned value, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````

## module — original line 78 (comment)

````text
# Atomic-scope band. source: comment at gate 6 below — the 200–3000 char band
# is an unsourced engineering default for "a self-contained note"
# (calibration pending), NOT a value from Luhmann's Zettelkasten method.
````

## module — original line 84 (comment)

````text
# source: comment at gate 7 below — "at least 3 distinct CamelCase/snake_case
# technical tokens".
````

## module — original line 129 (comment)

````text
# 6. Atomic scope. The 200–3000 char band is an unsourced engineering
#    default for "a self-contained note" (calibration pending), NOT a
#    value from Luhmann's Zettelkasten method, which sets no char range.
````
