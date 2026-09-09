---
title: "ADR-0101 — mcp_server/core/ast_extractors_clike.py rationale"
status: accepted
source: mcp_server/core/ast_extractors_clike.py
---

# ADR-0101 — mcp_server/core/ast_extractors_clike.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Node-type names verified empirically against tree-sitter-language-pack
grammars (c, cpp, csharp). C/C++ carry function names inside nested
``function_declarator`` nodes; C# uses ``name`` fields like Java.
````

## module — original line 7 (docstring)

````text
Split from ast_extractors.py to stay under 300 lines.

````

## _declarator_name — original line 38 (docstring)

````text
    Equivalent-mutant note (#369): the two checks below have identical bodies,
    so which tuple a node type sits in is not observable, and mutating a type
    string only changes behaviour if that type is the *terminal* declarator of
    a `function_definition`. In practice the chain terminates at `identifier`
    (free functions) or `qualified_identifier` (out-of-line members, including
    `C::~C`), so the remaining four names are carried for grammars and forms
    that do not currently reach here. They are kept rather than pruned because
    the split reads as a deliberate plain-vs-qualified distinction that a
    future caller may need to act on differently — the same judgement as the
    `decorated_definition` arm in `ast_extractors._walk_for_calls`.
    
````

## _walk_csharp — original line 131 (docstring)

````text
    Iterative (see `ast_extractors._walk_type`): one Python frame per AST level
    raised an uncaught RecursionError on deeply nested sources. Descendants are
    pushed reversed, so `defs` keeps its depth-first pre-order.
    
````
