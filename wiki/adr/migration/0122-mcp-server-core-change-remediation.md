---
title: "ADR-0122 — mcp_server/core/change_remediation.py rationale"
status: accepted
source: mcp_server/core/change_remediation.py
---

# ADR-0122 — mcp_server/core/change_remediation.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 1 (docstring)

````text
Remediation policy for memories impacted by a code change (fleet-watch #110).
````

## module — original line 3 (docstring)

````text
Detection (``handlers/consolidation/memory_staleness_pass.py``) marks an impacted
memory stale — it points at the bug. Remediation goes one step further: it
decides HOW to make the memory correct again, safely, so a commit that
invalidates a memory also repairs it.
````

## module — original line 8 (docstring)

````text
Two classes, because auto-rewriting prose from a diff risks fabrication:
````

## module — original line 10 (docstring)

````text
  - CODE-DERIVED memories (written by codebase ingestion — ``agent_context ==
    'codebase'``) can be refreshed *mechanically*: re-ingesting the changed file
    with ``codebase_analyze`` (incremental, content-hash tracked) supersedes the
    old AST-derived fact with the current one. Action: ``REINGEST``.
  - HAND-AUTHORED memories (decisions, lessons) must NOT be silently rewritten;
    a machine cannot re-derive an author's intent from a diff. Action:
    ``FLAG_STALE`` — mark stale and surface for a human/LLM to re-author.
````

## module — original line 18 (docstring)

````text
Pure: a memory dict in, an action out. Callers own the I/O (the re-ingest call,
the stale mark). ``agent_context == 'codebase'`` is the same marker
``handlers/codebase_analyze_helpers.py`` and ``handlers/change_impact.py`` use to
scope code-derived rows, reused here — not a new classification signal.

````
