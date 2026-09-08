# PostgreSQL recall plan experiment (W4-1)

This is a plan and SQL-equivalence instrument, not a retrieval-quality or
energy benchmark. It never loads a model and never reads DATABASE_URL.
It requires the name **and full Docker ID** of the retained container from
the chosen `benchmarks/reproduce.sh --keep-db` run. It verifies that name,
ID, running state, image reference read from reproduce.sh, and the
`POSTGRES_DB=cortex_bench` identity. Subsequent commands use the immutable ID.

The runner creates a UUID-named database inside that container, applies the
production DDL, then runs the same `DELETE ... WHERE is_benchmark = TRUE`
cleanup as BenchmarkDB. It deliberately does not instantiate BenchmarkDB:
`BenchmarkDB.open()` instantiates EmbeddingEngine after that cleanup.
Dedicated fixture loading follows cleanup; no BenchmarkDB lifecycle may
purge the corpus between loading and measuring. A finally block drops only
the database this invocation created, leaving the retained container and
`cortex_bench` database available to its owner. All raw SQL/output/plans
remain in the requested output directory on success or measurement failure.

Run only in the parent's serialized benchmark slot, after full before/after
quality runs have been arranged. The name and ID below must be supplied
from that session's reproduce.sh container; no discovery of other databases.

```bash
uv run --no-sync --extra benchmarks python -m benchmarks.pg_recall_plans.run \
  --container "$REPRODUCE_CONTAINER" --container-id "$REPRODUCE_CONTAINER_ID" \
  --rows 30000 --output benchmarks/results/w4-1-plans
```

The output path must not exist. `--rows` cannot be smaller than W4-1's
30,000-row minimum. Repeat explicitly with larger corpora to establish a
tested envelope; success at one size does not establish a universal bound.
The example exercises only 30,000 rows. Larger corpora remain unmeasured until
separate runs supply their own evidence; this harness does not infer an upper
corpus limit. The SQL records `count(*)` from its fixture and the transaction's
`NOW()` in `results.jsonl`; both are copied into `summary.json`.
No Docker or PostgreSQL command is run by importing these modules or by
requesting `--help`.

The synthetic corpus is a deterministic coverage grammar, not a claimed
production distribution. Row i has direction `[i, row_count, 0, …]` in the
schema's 384 dimensions and MD5(i) text. Every 100th row also contains
`needle target`, providing selective content queries. Divisibility by
2/3/5/7 independently cycles domain, directory, curated source and global
scope. Five stages and three valences cover the existing effective_heat
branches; age is i hours and heat_base is i / row_count. These are fixture
inputs, not retrieval thresholds. PostgreSQL computes embeddings' cosine
distances, tsvector, trigrams and effective_heat itself. The separate PG
tests add NULL/zero vectors, zero weights, source NULL, stale/superseded
rows, confidence/tag/agent/trust boosts and the top-K filter boundary.

Both functions run in one transaction, so NOW() and all decay ages are
identical. The reference is the exact d0f7c19b function, with only its name,
comments and obsolete DROP changed; it predates the two new partial indexes.
The before phase runs without those indexes; after creates them twice to
check idempotence and ANALYZEs again. Global and scoped requests run with
normal index scans and with index/bitmap scans disabled solely for the
exact semantic control. No HNSW tuning is applied. Versions and GUCs are
recorded, including pgvector's iterative-scan availability when present.

Normal plan measurements use `needle target` as before. Exact controls use
the unique MD5 token of fixture row 30,000 in both functions. The broad query
has equal full-text scores at the inner top-K cutoff: changing a plan can select
a different tied pool member, which can subsequently change the final result.
That is not merely a permutation of final rows. The original broad-query
experiment is retained in the W4-1 measurement report, including its differences;
the deterministic witness does not prove equivalence for every tied query.
Full retrieval floors remain mandatory. The 30,000 anchor is the plan's minimum
fixture size, so that row exists for every accepted `--rows` value.

The function now requests a custom plan locally. The first measured automatic
run switched to a generic plan after five calls, lost HNSW and exceeded the
buffer budget. PostgreSQL documents that heuristic in
[PREPARE](https://www.postgresql.org/docs/16/sql-prepare.html) and its override in
[plan_cache_mode](https://www.postgresql.org/docs/16/runtime-config-query.html#GUC-PLAN-CACHE-MODE).
The isolated ablation records the overhead and index use across all repetitions;
the setting restores the caller's policy on return and leaves ANN parameters alone.

The review applies the four-repetition/first-discarded protocol from
the remediation plan's [§3](../../../tasks/codex-green-remediation-plan.md#3-méthodes-de-mesure-réutilisées-par-plusieurs-items)
to these PG measurements (the original four-repetition bullet describes hook
CPU; the PG bullet specifies ANALYZE/BUFFERS). Each of the eight
before/after × normal/exact × global/scoped cases has four observations.
Execution order is before, then after; within each phase normal precedes exact,
and each repetition runs global then scoped. All 32 labels in execution order
are recorded in the summary. The fixture is loaded once and never modified
between measurements; all repetitions share the same transaction clock.

`nested-plans.log` contains actual auto_explain JSON from inside the stored
functions, with ANALYZE and BUFFERS enabled. An outer Function Scan is not
accepted as index evidence. GIN Bitmap Index Scan + sort counts as index
use. `summary.json` lists every index, CTE rows/loops, shared hits+reads,
temporary blocks and outer executor time (which includes nested execution).
It also lists missing/added rows and changed fields, with ordering reported
separately because the existing SQL has no tie-breaker. No numeric tolerance
is silently applied. NaN equality follows PostgreSQL's numeric semantics.
Each observation remains in the report. For each case, repetition 1 is excluded
only from performance statistics; repetitions 2–4 produce median/min/max for
executor milliseconds, shared hits+reads and both temporary-block counts.
All four before/after pairs retain exact row/field comparison and separate
ordering reports. Duplicate, absent, extra or reordered measurement labels
fail analysis rather than overwriting a result or silently reducing sample size.

The plan gate requires both exact-control result sets to match in all four
repetitions, including the discarded performance sample. Each retained normal
after plan must show all three requested indexes, at most 10,000
shared hits+reads and at most 200 ms (W4-1 contract). A failing retained sample
cannot be hidden by a passing median. These thresholds are unchanged. ANN differences are
reported separately, never labelled exact. These measurements include
auto_explain instrumentation overhead and start after fixture loading;
they are not cold-storage measurements. Fixture loading, ANALYZE and the
cardinality observation precede measurements; the first normal phase runs before
the exact controls. Discarding one sample does not remove ordering/cache bias,
so the fixed order must be reported alongside any delta.

Full `benchmarks/reproduce.sh --no-ablation` runs before and after remain
mandatory for LongMemEval/LoCoMo floors. BEAM has no floor in reproduce.sh;
the script says so and this instrument cannot manufacture one. Attach
the run's SHA, manifest, uptime/df before and after, raw plans and full
quality results. The instrument's manifest additionally hashes the exact
executed SQL, since a dirty worktree SHA alone cannot identify the patch.

Production operations are owner-run only: deploy the reviewed schema
migration during an appropriate maintenance window. The new index creation
is the existing idempotent migration path, not concurrent live DDL; no
production migration, DROP INDEX, VACUUM FULL or data purge is performed here.

Primary-source rationale: [design note](../../docs/provenance/pg-recall-pools-design.md).
