---
title: "ADR-0105 — mcp_server/core/ast_parser.py rationale"
status: accepted
source: mcp_server/core/ast_parser.py
---

# ADR-0105 — mcp_server/core/ast_parser.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Replaces regex-based extraction with proper AST parsing. Extracts:
- Imports with resolved target files
- Function/method definitions with scope
- Class definitions with inheritance
- Function call sites for call graph edges
- Class-method containment
````

## module — original line 10 (docstring)

````text
Falls back to regex parser if tree-sitter is not installed.
````

## module — original line 12 (docstring)

````text
Pure business logic — no I/O. Callers pass file content as bytes.

````

## _is_ast_language — original line 67 (docstring)

````text
    Sound by construction: `AST_SUPPORTED` is declared
    `frozenset[SupportedLanguage]`, so a name the pack does not ship fails
    the type check at its definition rather than silently widening here.
    
````

## inline — original line 57 (directive-rationale)

````text
# noqa: PLC0415, F401 — optional-feature probe: ImportError here is a handled degraded mode
````

## inline — original line 91 (directive-rationale)

````text
# noqa: PLC0415 — optional-feature probe: ImportError here is a handled degraded mode
````

## module — original line 101 (comment)

````text
# Same degraded mode as ImportError above, reached differently: the
# pack imported fine but could not fetch/verify this grammar right
# now. Logged every call, not just the first — this runs once per
# file, not once per process like a singleton model load, so
# suppressing repeats would hide a mid-run outage.
````

## module — original line 137 (comment)

````text
# Caller-qualified call map — works across every language the
# extractor covers because it targets tree-sitter node types shared
# across grammars (function_definition, function_declaration,
# method_definition, call, call_expression). Empty on regex fallback
# or when a grammar doesn't expose those names.
````

## module — original line 240 (comment)

````text
# Keyed by the language pack's own `SupportedLanguage` literal, not by `str`:
# that makes the type checker verify every key below against the grammars the
# pack actually ships, and it is what lets `_get_extractor_and_tree` hand
# `get_parser` a value of the type its signature asks for. The pack types that
# parameter `SupportedLanguage` up to 1.6.x and `str` from 1.9 on, so a plain
# `str` type-checks under one resolution of the dependency pin and fails under
# another — the divergence issue #253 was filed for. See the pin's own comment
# in pyproject.toml for the measured per-release type surface.
````

## module — original line 258 (comment)

````text
# The extractor table IS the definition of "AST-supported": a language is
# supported exactly when queries exist for it. Derived rather than restated,
# so `_EXTRACTORS[language]` is total once `_is_ast_language` has narrowed —
# there is no second list that can drift out of step with this one.
````
