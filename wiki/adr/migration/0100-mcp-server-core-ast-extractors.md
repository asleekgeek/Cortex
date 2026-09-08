---
title: "ADR-0100 — mcp_server/core/ast_extractors.py rationale"
status: accepted
source: mcp_server/core/ast_extractors.py
---

# ADR-0100 — mcp_server/core/ast_extractors.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## _walk_type — original line 35 (docstring)

````text
    Iterative on purpose. The recursive form consumed one Python frame per AST
    level and raised RecursionError at an AST depth of ~1003 under the default
    limit of 1000 — reachable on minified or generated sources in third-party
    repositories, and unhandled (no caller catches RecursionError). Heap depth
    replaces stack depth; the traversal order is unchanged.
    
````

## _extract_python_func — original line 110 (docstring)

````text
    Equivalent-mutant note (#369): a `function_definition` node always carries
    both a `name` and a `parameters` child, so the two `else ""` fallbacks here
    are unreachable. They are guards against a grammar that stops guaranteeing
    it, not live branches.
    
````

## _extract_python_class — original line 143 (docstring)

````text
    Equivalent-mutant note (#369): a `class_definition` always carries a
    `name`, so that `else ""` is unreachable. The `superclasses` fallback is
    NOT — `class C: pass` has no base list — and is pinned in
    `test_ast_extractor_edges.py::TestSignatureTruncation`.
    
````

## _extract_js_node — original line 188 (docstring)

````text
    Equivalent-mutant notes (#369), all turning on which callers supply a
    non-empty `parent`:
````

## _extract_js_node — original line 191 (docstring)

````text
    * `parent` is `""` at both entry points here (`extract_js_definitions` and
      the `export_statement` recursion) and is only non-empty when
      `_extract_js_class` recurses into a class body. Passing `None` instead of
      `""` is therefore unobservable — every use is a truthiness test.
    * `method_definition` is only reached from that class-body recursion, so
      `parent` is always set when the arm below runs and its `else` branch is
      unreachable. Mutating the arguments inside it cannot be detected.
    * `"function"` is a legacy tree-sitter node type. The current grammar emits
      `function_expression` for anonymous function expressions, so nothing
      reaches the second entry of the tuple. Kept for grammar compatibility.
    
````

## _callee_basename — original line 296 (docstring)

````text
    Equivalent-mutant note (#369): the `1` in both splits is unobservable.
    `rsplit(sep, n)[-1]` is the text after the last separator for every n, and
    `split(sep, n)[0]` is the text before the first separator for every n. Only
    the *direction* matters, and that is pinned — see
    `test_ast_extractor_edges.py::TestCalleeBasenameEdges`.
    
````

## _walk_for_calls — original line 342 (docstring)

````text
    Iterative for the same reason as `_walk_type`: one Python frame per AST
    level raised RecursionError on deeply nested sources, and no caller
    catches it. The explicit stack carries the enclosing class scope with
    each node, and descendants are pushed reversed so they pop before the
    remaining siblings — preserving the depth-first pre-order the recursive
    form had, and with it the insertion order of `out`.
    
````

## module — original line 17 (comment)

````text
# source: pre-existing tuned value, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````

## module — original line 47 (comment)

````text
# Reversed, so siblings pop left-to-right and the result stays
# pre-order document order — identical to the recursive form.
````

## module — original line 356 (comment)

````text
# Equivalent-mutant note (#369): mutating "body" here, or the `or`
# to `and`, is undetectable. The body node is itself a child, so
# descending `child.children` reaches it via the catch-all and
# finds the same definitions in the same order. The fallback stays
# because grammars without a `body` field rely on it.
````

## module — original line 365 (comment)

````text
# Mirrors `_extract_python_children`'s dispatch, where the same
# branch is load-bearing: that function has no catch-all, so
# without it a decorated definition is invisible. Here the `else`
# below already reaches the wrapped node, which makes this arm
# behaviourally identical today — and its mutants unkillable.
#
# It is kept, not deleted, because it is the seam for behaviour
# that was never filled in: calls made *in the decorator*
# (`@app.route("/api")`, `@retry(times=3)`) currently produce no
# edge anywhere. Issue #372 carries the design decision and the
# implementation; deleting the arm would foreclose the question
# rather than answer it.
````

## module — original line 380 (comment)

````text
# Equivalent-mutant note (#369): the `else ""` arm is unreachable —
# every node type in _FUNCTION_NODE_TYPES carries a name in all
# grammars in use (verified by sweep). It stays as a guard against
# a grammar that stops doing so, which would otherwise crash here.
````
