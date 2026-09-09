---
title: "ADR-0199 — mcp_server/core/memory_domain_backfill.py rationale"
status: accepted
source: mcp_server/core/memory_domain_backfill.py
---

# ADR-0199 — mcp_server/core/memory_domain_backfill.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 1 (docstring)

````text
Derive the true domain for memories stuck with an empty ``domain``
column (I6-D3, ADR-0051-family batch-completion campaign).
````

## module — original line 4 (docstring)

````text
``memories.domain`` is set once, at ``remember`` time, from whatever
``directory``/``domain`` hint the caller supplied
(``handlers/remember.py::_resolve_domain``). For 1 355 rows that
derivation failed or was never attempted (root cause fixed for future
writes by issue #95's ``normalize_project_id`` casing fix) — the stock
of already-written rows still carries ``domain = ''``.
````

## module — original line 11 (docstring)

````text
This module re-derives the domain from evidence the memory row already
carries, in a strict priority order, and refuses to guess when no
evidence resolves:
````

## module — original line 15 (docstring)

````text
  1. ``directory_context`` (the raw cwd stored by ``post_tool_capture``
     at write time, ``pg_schema.py:29``) — resolved via the injected
     ``resolve_directory`` callable (production: ``resolve_cwd``, the
     same git-root-based function ``remember``'s write path already
     uses, ``remember.py:246``).
  2. a ``project:<slug>`` tag (written by ``backfill_memories``,
     ``backfill_memories.py:161-164``) — resolved via the injected
     ``resolve_project_tag`` callable (production: ``slug_to_domain``,
     the same function ``backfill_memories`` already uses,
     ``backfill_helpers.py:157-166``).
  3. neither resolves → orphan. No neighbor/embedding/similarity
     inference (Q3 arbitrage: no retroactive fabrication of
     provenance) — the row stays domain-less and is tagged
     ``domain-orphan`` so the state is explicit and requeryable.
````

## module — original line 30 (docstring)

````text
Pure logic, no I/O — filesystem/git walks and registry lookups are
injected via ``resolve_directory``/``resolve_project_tag`` so this
module stays unit-testable without touching a real tree or DB, and so
it can live in core/ per the Dependency Rule (core imports shared/ +
stdlib only).

````

## derive_memory_domain — original line 84 (docstring)

````text
    Pre-condition:  ``directory_context`` and ``tags`` are the memory
                    row's own columns (``tags`` already JSON-decoded to
                    a list of strings); ``resolve_directory`` maps a
                    raw cwd to a canonical domain or ``""`` when it
                    cannot (mirrors ``resolve_cwd``'s contract:
                    deterministic, no fabrication); ``resolve_project_tag``
                    maps a project slug to a canonical domain or ``""``
                    (mirrors ``slug_to_domain``).
    Post-condition: returns ``DomainDerivation(domain, evidence)``.
                    ``domain`` is non-empty iff a source resolved;
                    ``evidence`` names the winning source
                    (``"directory_context"`` beats ``"project_tag"``
                    when both would resolve — directory evidence is
                    written unconditionally by every capture, tag
                    evidence only by backfill imports, so directory
                    evidence is checked first). Neither source
                    resolving returns ``DomainDerivation("", "")`` —
                    the orphan case; callers must not invent a domain
                    for it.
    
````
