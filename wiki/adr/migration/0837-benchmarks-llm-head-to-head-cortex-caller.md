---
title: "ADR-0837 — benchmarks/llm_head_to_head/cortex_caller.py rationale"
status: accepted
source: benchmarks/llm_head_to_head/cortex_caller.py
---

# ADR-0837 — benchmarks/llm_head_to_head/cortex_caller.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
PROTOCOL §11.1 ANTI-CHEATING (load-bearing invariant for the whole study):
````

## module — original line 5 (docstring)

````text
This module MUST invoke the production handler entry point
``mcp_server.handlers.recall.handler`` directly, with arguments that
already exist in the production schema. NO monkey-patching. NO benchmark-
only kwargs. NO ``--benchmark-mode`` flag. NO alternative code path.
````

## module — original line 10 (docstring)

````text
The unit test ``tests_py/handlers/test_beam_anticheat.py`` reads THIS
file's source code and asserts:
  1. The only import targeting ``mcp_server.handlers.recall`` is exactly
     ``from mcp_server.handlers.recall import handler``.
  2. No call to ``setattr``, ``__class__``, or any monkey-patch primitive.
  3. The kwargs passed to ``handler({...})`` are a subset of the keys
     declared in ``recall.schema['inputSchema']['properties']``.
````

## module — original line 18 (docstring)

````text
If you change this file, the anti-cheating test must still pass without
modification, OR a protocol addendum must be filed (§11 forbids silent
deviation).
````

## module — original line 44 (comment)

````text
# Pre-registered max_results value matching condition B's k=20 (protocol §2.C
# uses the same retrieval depth as B so the comparison isolates the stack).
````

## module — original line 61 (comment)

````text
# The production handler is async. Run it on a fresh loop so the
# benchmark orchestrator (synchronous) can call us. This is the same
# pattern any synchronous caller of an MCP tool uses.
````
