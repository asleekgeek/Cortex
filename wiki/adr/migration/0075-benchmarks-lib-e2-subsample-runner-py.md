# ADR-0075: benchmarks/lib/e2_subsample_runner.py implementation decisions

Status: accepted; preserved from the existing implementation during issue #514.

These are historical implementation records, not new algorithm or threshold choices.
Source: `benchmarks/lib/e2_subsample_runner.py`; original SHA-256 `8836941cf2000f065904ccd2af6ca598eb83a16ddb9d988916b330f2bdb5486a`.

## Original docstring, lines 1–26

````text
"""E2a — Real-benchmark subsampling for the E2 retrieval claim.

Replays LongMemEval / LoCoMo / BEAM-100K at increasing N by subsampling
their native corpora deterministically. This is the **claim-bearing** E2
retrieval runner; the synthetic-corpus latency runner
(``benchmarks.lib.latency_runner``) is latency-only.

Per N, runs cortex_full + cortex_flat using the shared E2 condition
toggles (``benchmarks.lib._e2_conditions``). Memories are loaded via the
production write path (BenchmarkDB → memory_ingest), and queries go
through the production read path (BenchmarkDB → pg_recall) — same code
as the standalone benchmarks. Outputs JSON per (benchmark, N, cond) and
a summary.csv.

Falsifiability (per docs/provenance/verification-protocol.md §E2): the gap between
cortex_full and cortex_flat MRR on at least one of {LongMemEval-S,
LoCoMo, BEAM-100K} at N=full must be >= 5pp; otherwise the
thermodynamic-structure-matters claim is refuted.

CLI:
    python -m benchmarks.lib.e2_subsample_runner \\
        --benchmark longmemeval-s --n 100 1000 \\
        --queries 50 --seed 42 \\
        --db-url postgresql://localhost:5432/cortex_e2_subsample \\
        [--quick]
"""
````

## Original comment, lines 159–162

````text
# require_reranker=True: this is the claim-bearing E2 retrieval
        # runner (module docstring) -- a silently-degraded first-stage-only
        # pipeline would corrupt the falsifiable cortex_full vs cortex_flat
        # MRR gap this module exists to measure (INC7.2 audit).
````

