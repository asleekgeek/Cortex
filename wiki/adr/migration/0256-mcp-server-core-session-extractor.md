---
title: "ADR-0256 — mcp_server/core/session_extractor.py rationale"
status: accepted
source: mcp_server/core/session_extractor.py
---

# ADR-0256 — mcp_server/core/session_extractor.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Pure business logic — no I/O. Receives parsed records, returns extraction results.
````

## module — original line 5 (docstring)

````text
Strategies:
  1. Decision extraction: user messages containing decision keywords
  2. Error extraction: messages about bugs, failures, debugging sessions
  3. Architecture extraction: design discussions, pattern choices
  4. Key insight extraction: important conclusions, lessons learned
  5. Tool pattern extraction: which tools were used and how
````

## module — original line 12 (docstring)

````text
Each extracted item includes content, tags, and a source classification.

````

## module — original line 109 (comment)

````text
# Messages longer than this many characters get an importance boost.
# source: pre-existing tuned value, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````
