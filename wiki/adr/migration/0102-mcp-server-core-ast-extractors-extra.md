---
title: "ADR-0102 — mcp_server/core/ast_extractors_extra.py rationale"
status: accepted
source: mcp_server/core/ast_extractors_extra.py
---

# ADR-0102 — mcp_server/core/ast_extractors_extra.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Split from ast_extractors.py to stay under 300 lines.

````

## extract_go_definitions — original line 34 (docstring)

````text
    Equivalent-mutant notes (#369): a Go `function_declaration` always carries
    a `parameters` node — `func F()` still has an empty one — so the `else ""`
    signature fallback is unreachable. Likewise a `method_declaration` always
    carries a receiver, and a receiver always contains a `type_identifier`, so
    `_extract_go_receiver` never returns `""` from this call site and the
    unqualified `else` branch below is unreachable. Both fallbacks are kept as
    guards; the reachable behaviour is pinned in
    `test_ast_extractor_definitions.py::TestGoDefinitions`.
    
````

## _extract_swift_node — original line 126 (docstring)

````text
    Iterative (see `ast_extractors._walk_type`): one Python frame per AST level
    raised an uncaught RecursionError on deeply nested sources. Descendants are
    pushed reversed, so `defs` keeps its depth-first pre-order. The branch
    structure is the original if/elif/else: a `_SWIFT_KIND_MAP` node never
    reaches the catch-all descent, and an unnamed one descends nowhere.
    
````
