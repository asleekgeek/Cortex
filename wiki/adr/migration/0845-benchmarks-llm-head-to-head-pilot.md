---
title: "ADR-0845 — benchmarks/llm_head_to_head/pilot.py rationale"
status: accepted
source: benchmarks/llm_head_to_head/pilot.py
---

# ADR-0845 — benchmarks/llm_head_to_head/pilot.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Per protocol §8: cheapest stress-test of the harness. Conditions A and D
are skipped in pilot because they're not load-bearing for the §8 GO/NO-GO
gate (which checks judge κ, end-to-end success rate, and B-vs-C signal
direction).
````

## module — original line 8 (docstring)

````text
This file's --dry-run mode is the Stage-0 deliverable. It:
  1. Loads N BEAM items (default 3).
  2. Builds condition contexts for A, B, C, D — verifying every builder
     produces a non-degenerate output without firing any API.
  3. Prints token counts, retrieved-passage counts, oracle-turn counts.
  4. Renders the answer prompt that WOULD be sent to the generator.
  5. Estimates Stage 2.1 cost.
  6. Does NOT call any vendor API; does NOT touch the production DB
     (condition C is stubbed in dry-run mode — see below).
````

## _build_dryrun_context — original line 95 (docstring)

````text
    Conditions B and C require runtime resources we don't want to spin
    up at scaffold time:
      - B needs a per-conversation BenchmarkDB with memories loaded into
        an HNSW-indexed table.
      - C needs the production memory store seeded under domain="beam".
    For dry-run we emit a placeholder block with the budget envelope
    (~4500 tokens per protocol §7) so the prompt rendering is exercised
    end-to-end. The token counts in the cost estimate use the same §7
    figures.
````

## run_pilot_live — original line 256 (docstring)

````text
    pre:
      - ``ANTHROPIC_API_KEY`` and ``OPENAI_API_KEY`` are set in the env
        (the cross-vendor judge needs both for the Haiku × GPT-4o pairing).
      - ``DATABASE_URL`` points at the local Cortex Postgres; pgvector +
        pg_trgm extensions installed; production schema migrated.
      - Network reachable for Anthropic + OpenAI APIs.
    post:
      - Writes ``output_dir/manifest.json`` and ``output_dir/items.jsonl``.
      - Each item × condition cell appears as one items.jsonl line with
        a real generator_response and judge_label.
      - Returns 0 on success (all cells produced); 4 on cost-ceiling abort;
        5 on dataset load failure; 6 on DB connection failure.
    invariant:
      - The smoke is bounded by ``cost_ceiling_usd`` (defence-in-depth on
        the Stage 0 $0.15 cap); the run aborts mid-loop if exceeded.
    
````

## module — original line 79 (comment)

````text
# source: structural — the k-suffix in a token count is the thousands unit
````

## inline — original line 158 (directive-rationale)

````text
# noqa: BLE001 — bench harness is fail-soft — failure is printed and the run continues or exits with a report
````

## module — original line 189 (comment)

````text
# Print first 200 chars of rendered prompt so the reader can
# eyeball the format without 196k tokens of dump.
````

## inline — original line 285 (directive-rationale)

````text
# noqa: BLE001 — bench harness is fail-soft — failure is printed and the run continues or exits with a report
````

## module — original line 295 (comment)

````text
# Pre-flight: open BenchmarkDB and seed memories under domain="beam".
# This single DB instance serves BOTH:
#   - Condition B (direct cosine query against the same memories table)
#   - Condition C (production handler reads same memories table)
# That's by design — protocol §2.B/C compares retrieval STACKS over
# the same ground-truth memory population.
````

## inline — original line 302 (directive-rationale)

````text
# noqa: PLC0415 — deferred: module hard-imports pgvector/psycopg/psycopg_pool at top level; hoisting would break installs without it
````

## inline — original line 303 (directive-rationale)

````text
# noqa: BLE001 — bench harness is fail-soft — failure is printed and the run continues or exits with a report
````

## module — original line 317 (comment)

````text
# Build the manifest scaffold up-front (write_manifest emits
# manifest.json so cost_tracking can be patched later).
````

## module — original line 353 (comment)

````text
# Open BenchmarkDB and seed BEAM memories. The seeded conversation
# is whichever conv the items belong to; for n≤3 they share the same
# conversation_idx in BEAM-10M (one mega-convo per record). We seed
# ALL turns from the items' conversations, deduplicated by content.
````
