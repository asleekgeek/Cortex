# Reproducing the Cortex benchmarks

Every published Cortex retrieval number comes from the scripts in this
directory, run against the **production code path**: data is ingested
through `mcp_server.core.memory_ingest`, retrieval goes through the same
PL/pgSQL `recall_memories()` + FlashRank reranking that serves live MCP
calls. There is no benchmark-only retriever.

## One-command reproduction (LongMemEval)

Requirements: Docker, [uv](https://docs.astral.sh/uv/), ~1.5 GB free disk
(dataset + embedding models), no API keys.

```bash
make longmemeval-smoke   # 10 questions, a few minutes — verifies the harness
make longmemeval         # full 500 questions, ~40 min on a laptop
```

The harness downloads the official LongMemEval-S dataset from the
authors' Hugging Face repository (sha256-pinned), provisions an
ephemeral PostgreSQL + pgvector container on port 55432 (it never
touches an existing Cortex install), runs the benchmark, prints the
Recall@K / MRR table, and removes the container. `KEEP_DB=1 make
longmemeval` keeps the database for inspection. Every run also emits a
reproducibility manifest (commit, config, dataset hash) via
`benchmarks/_repro.py`.

Measured wall-clock for the full run: **39.6 min** on Apple Silicon with
CPU embeddings (`benchmarks/results/a3_longmemeval_post_refactor.md`).

## What the numbers mean (metric scope)

Cortex reports **session-level retrieval Recall@10 and MRR**: for each
of the 500 questions, all haystack sessions are loaded into the store,
production recall runs, and the run scores whether the answer-bearing
session(s) appear in the top 10.

- The comparable published baseline is the best retrieval configuration
  in the LongMemEval paper itself (Wu et al., ICLR 2025): **Recall@10
  78.4%**. Cortex: **98.4%** (n=500).
- This is **not** the end-to-end QA accuracy that LLM-answering
  leaderboards report (an LLM answers from the retrieved context and a
  judge scores the answer). Retrieval recall and QA accuracy are
  different measurements; do not compare one to the other.
- The same scoping discipline applies to BEAM: see the BEAM note in
  `CLAUDE.md` — the retrieval-proxy MRR there is used only for
  within-system comparisons, never as a head-to-head claim.

If your numbers differ from the published ones, open an issue with the
printed reproducibility manifest and we will publish the discrepancy.

## Other benchmarks

| Benchmark | Runner | Dataset |
|---|---|---|
| LongMemEval (ICLR 2025), 500 Q | `longmemeval/run_benchmark.py` | auto-downloaded by the harness |
| LoCoMo (ACL 2024), 1,986 Q | `locomo/run_benchmark.py` | see runner's download hint |
| BEAM (ICLR 2026) | `beam/run_benchmark.py --split 100K` | see runner's download hint |
| MemoryAgentBench, EverMemBench, Episodic | respective `run_benchmark.py` | see runner's download hint |

Ablation studies (per-mechanism lesion runs) live in
`benchmarks/lib/ablation_runner` and their results under
`benchmarks/results/ablation/`.
