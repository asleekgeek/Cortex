# LongMemEval-S · SQLite three-way — issue #169 (Phase B, on the #173 seams)

Harness: `benchmarks/longmemeval/run_sqlite_fallback_bench.py`
(a #169-specific harness — the production `run_benchmark.py` drives PostgreSQL +
pgvector and has no no-vector / embedding-mode toggle, so it cannot express this
three-way SQLite comparison. This harness reuses the production harness's
dataset loading + scoring functions verbatim: `session_to_memory_content`,
`parse_longmemeval_date`, `compute_heat_with_decay`, `compute_mrr`,
`recall_at_k_binary`.)

- Dataset: `longmemeval_s.json` (Wu et al., ICLR 2025), variant `s`.
- Branch: `feat/semantic-fallback-169b`; run against commit `8347944` (this PR's
  implementation commit — fresh numbers on the Phase B code, replacing the old
  branch's figures).
- Date: 2026-07-24 (UTC).
- Bounded run: `--limit 50` questions. Full floors are NOT required — the
  PostgreSQL / sentence-transformers production path is untouched by #169; this
  measures only the SQLite fallback path #169 introduces.
- Environment: CPU, macOS dev host, in-memory `SqliteMemoryStore` per question
  (`:memory:`), zero network for the no-vector and fallback modes. The fallback
  mode selects the algorithmic provider via `ModelState` (bogus model name +
  `CORTEX_EMBEDDING_ZERO_DOWNLOAD=1`); the process singleton is installed in the
  factory so the store stamps provenance and the query-space filter is active.

## Results (n = 50)

| mode                      |   MRR | Recall@10 | elapsed |
|---------------------------|------:|----------:|--------:|
| (a) no-vector baseline    | 0.275 |     46.0% |   5.2 s |
| (b) algorithmic fallback  | 0.378 |     66.0% |  38.6 s |
| (c) sentence-transformers | 0.609 |     94.0% |  49.6 s |

Fallback vs no-vector: **ΔMRR = +0.102, ΔRecall@10 = +20.0 pp** →
**fallback BEATS the no-vector baseline** (issue #169 adoption criterion met).

## Reading

The fallback lands where a download-free approximation should: materially above
the no-vector floor (recovering ~half the MRR gap and ~40% of the Recall@10 gap
to the neural encoder), and clearly below neural — which is why the two spaces
are kept from cross-ranking and why the consolidate upgrade cycle re-embeds
fallback memories to neural once the model is present.

Reproduce:

```
python3 benchmarks/longmemeval/run_sqlite_fallback_bench.py --limit 50 \
    --results-out benchmarks/results/semantic-fallback-169/lme-s-sqlite-3way.json
```
