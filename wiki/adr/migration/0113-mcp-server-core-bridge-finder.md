---
title: "ADR-0113 — mcp_server/core/bridge_finder.py rationale"
status: accepted
source: mcp_server/core/bridge_finder.py
---

# ADR-0113 — mcp_server/core/bridge_finder.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## _index_memories — original line 226 (docstring)

````text
    Two producers feed this function with different shapes:
      - ``brain_index["memories"]`` is already an id-keyed ``dict``.
      - ``scanner.discover_all_memories()`` returns a ``list`` of records
        (``file``/``path``/``project``/``body``/... — see
        ``scanner._parse_memory_file``). Passing that list straight into
        ``dict.update`` raised ``ValueError: dictionary update sequence
        element #0 has length 9; 2 is required`` whenever the live home held
        real memory files (issue #174) — empty homes skipped the branch, so
        the defect only surfaced against production data.
````

## _index_memories — original line 236 (docstring)

````text
    A ``dict`` is returned unchanged. A ``list`` is keyed by the record's
    stable ``path`` (fallback ``file`` then ``name``); records that carry no
    identifier are keyed by object identity so distinct records never collide.
    
````

## module — original line 15 (comment)

````text
# source: pre-existing tuned value, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````
