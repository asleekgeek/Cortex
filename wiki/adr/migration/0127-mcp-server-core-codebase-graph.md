---
title: "ADR-0127 — mcp_server/core/codebase_graph.py rationale"
status: accepted
source: mcp_server/core/codebase_graph.py
---

# ADR-0127 — mcp_server/core/codebase_graph.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Takes parsed FileAnalysis objects and produces resolved edges:
- File → file import edges (resolved from module names)
- Function → function call edges
- Class → method containment edges
- Class → parent inheritance edges
- Community assignments via Leiden (Louvain fallback)
````

## module — original line 10 (docstring)

````text
Pure business logic — no I/O.

````

## build_resolved_call_edges — original line 183 (mixed-contract-rationale)

````text
    Returns:
        ``[(caller_file, caller_qname, callee_file, callee_qname),
        ...]``. The fourth position is the **full qualified name** of
        the resolved callee (e.g. ``Foo.baz``), NOT the basename. This
        matches the shape ``ingest_symbol`` uses to mint SYMBOL node
        ids and the shape AP emits for its CALLS edges; if we returned
        a basename instead, ``ingest_ast_edge`` would hash a different
        ``symbol_id`` for ``dst`` than the one stored for the target
        SYMBOL, and the edge would be dropped silently. See Wu error
        archaeology 2026-04-24 and the boundary-crossing regression
        test in tests_py/infrastructure.
    
````

## module — original line 17 (comment)

````text
# Community detection & centrality live in codebase_communities.py
# (300-line limit + SRP); re-exported so existing callers keep working.
````

## module — original line 203 (comment)

````text
# Build basename → (first-defining-file, full-qname) lookup. We key
# by basename because the tree-sitter call sites produce "baz", not
# "Foo.baz" — we resolve the basename to the known symbol, then
# emit the symbol's full qname so the edge endpoints carry the
# same string the ingester hashed at ingest_symbol time.
#
# First-wins collision semantics on basename match ``build_call_edges``
# (documented / intentional).
````
