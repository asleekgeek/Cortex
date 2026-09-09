---
title: "ADR-0197 — mcp_server/core/memory_decomposer.py rationale"
status: accepted
source: mcp_server/core/memory_decomposer.py
---

# ADR-0197 — mcp_server/core/memory_decomposer.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Inspired by the ai-architect artifact chunking strategy: split at natural
structural boundaries (speaker turns for conversations, headings for
markdown), not arbitrary character limits. Each chunk carries extracted
entities for graph-based retrieval.
````

## module — original line 8 (docstring)

````text
Chunking strategies:
  1. Conversation content: group by speaker turn pairs (2-3 exchanges)
  2. Markdown content: split at ## heading boundaries
  3. Short content (< threshold): pass through unchanged
````

## module — original line 13 (docstring)

````text
Pure business logic — no I/O.

````

## module — original line 46 (comment)

````text
# Directive language markers (Searle 1969 speech act theory: directives).
# Tight patterns: only match explicit user directives, not general conversation.
# "always use X", "never do Y", "make sure to Z" — not "I should go".
````

## module — original line 143 (comment)

````text
# Person-name candidates of length <= 2 are ignored as noise.
# source: pre-existing tuned value, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````
