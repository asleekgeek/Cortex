---
title: "ADR-0239 — mcp_server/core/replay_formatting.py rationale"
status: accepted
source: mcp_server/core/replay_formatting.py
---

# ADR-0239 — mcp_server/core/replay_formatting.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## should_micro_checkpoint — original line 41 (docstring)

````text
    Triggers on error detection, decisions, high surprise, or critical tags.
    Returns (should_checkpoint, reason).
    
````

## module — original line 26 (comment)

````text
# Above this surprise value an event alone warrants a micro-checkpoint.
# source: pre-existing tuned value, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````
