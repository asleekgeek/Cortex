# ADR-0341: mcp_server/handlers/consolidate.py implementation decisions

Status: accepted; preserved from the existing implementation during issue #514.

These are historical implementation records, not new algorithm or threshold choices.
Source: `mcp_server/handlers/consolidate.py`; original SHA-256 `0a0176986d67bd2bcdc686117c241ac3440e89ff7b35f65a378e13f116f803b8`.

## Original docstring, lines 205–209

````text
"""Run a cycle, inject duration_ms into its result dict.

    Addresses issue #13 (darval): per-stage telemetry so operators can
    see where time actually goes on real stores.
    """
````

## Original comment, lines 244–251

````text
# Constant-memory consolidate (sharded-popping-harbor): every stage now
    # STREAMS the memory corpus in bounded chunks via
    # ``store.iter_memories_for_decay()`` (decay/compression/memify/sleep/
    # homeostatic) or a streaming reducer (emergence, wiki cluster count), so
    # peak RAM is one chunk plus bounded accumulators rather than the whole
    # ~1GB corpus. This trades the single issue-13 shared load for one bounded
    # cursor scan per stage — the correct trade at scale, where the shared list
    # would OOM. A future single-pass combined reducer can fold these scans.
````

## Original comment, lines 255–260

````text
# Fact derivation (INC6.1b, 2026-07-10): gated by the same `memify` flag
    # as the prune/strengthen/reweight cycle above (one user-facing switch,
    # per the schema description), but tracked as its own top-level stage so
    # the failed_stages rollup below can see it independently. Routed through
    # the real write gate (async remember() call) — it cannot run inside the
    # sync `_run_cycles` above, so it lives here instead.
````

## Original comment, lines 264–270

````text
# 2026-05-18: autonomous wiki maintenance. The wiki has to stay up
    # to date without a human in the loop, so every consolidation cycle
    # purges stale + stub pages and reports the curation backlog
    # (coverage gaps + cluster jobs). Existing pages get the same
    # treatment as freshly authored ones — nothing the system produced
    # gets a free pass once policy tightens. Failure here is non-fatal:
    # a wiki edge case must never block memory consolidation.
````

## Original comment, lines 288–289

````text
# Back-compat: keep ``pending_curations`` populated for callers
        # that read the legacy key (SessionStart preamble pre-2026-05-18).
````

## Original comment, lines 298–300

````text
# Aggregate rollup — surfacing partial failures (issue #13, code-reviewer).
    # Without this, a caller that only reads duration_ms cannot tell that
    # one or more stages errored inside _timed.
````

## Original comment, lines 307–309

````text
# Update the autonomy stamp so SessionStart's TTL gate sees this run.
    # User directive 2026-05-18: consolidate must never require manual
    # invocation; the stamp closes the loop with the SessionStart hook.
````

## Original docstring, lines 324–328

````text
"""Run optional maintenance cycles based on args flags.

    Each memory-consuming stage is passed no list, so it streams the corpus in
    bounded chunks (constant memory) instead of sharing a single resident load.
    """
````

## Original schema description, interim lines 48–66

````text
Run scheduled memory-system maintenance cycles: thermodynamic heat decay, full-text → gist → tag compression, episodic→semantic CLS transfer (McClelland 1995), synaptic plasticity LTP/LTD (Hebb 1949, Bi & Poo 1998), microglial pruning of orphan edges (Wang 2020), homeostatic scaling (Turrigiano 2008), cascade stage advancement (Kandel 2001), and optional deep-sleep replay. Each cycle is delegated to a focused sub-module under handlers/consolidation/; durations are tracked per stage with partial-failure rollup. Use this on a daily/weekly cadence (or after large ingest bursts) to keep recall fast and the heat distribution healthy. Distinct from `wiki_consolidate` (operates on wiki PAGES not memories) and `forget` (one-off deletion, no lifecycle). Mutates memories + entities + relationships tables. Latency varies (~5-60s typical, deep mode minutes). Returns per-cycle counters, duration_ms per stage, status (ok|partial), and failed_stages list. The `cls` and `memify` stages include `reason_for_zero` / `reason_for_inaction` when the cycle produces no mutations, distinguishing early-return from a genuine quiet-store pass (issue #14 P2).
````

## Original schema description, interim lines 158–164

````text
Cap on how many pages each purge axis (stubs, classifier rejects) may delete in a single consolidate cycle. Acts as a safety rail: a buggy classifier change costs at most one cap's worth of pages before the next cycle exposes the regression. Default 500. Pass 0 to disable the cap (one-shot full sweep).
````

