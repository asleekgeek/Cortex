# Frequent-token subsampling: on / off / CBM-faithful — issue #184

The evidence that chose the fix for the §8 source-fidelity defect in
`mcp_server/shared/algorithmic_embedding.py`. The shipped embedder strided the
*whole* per-position loop whenever a **document** exceeded `_MAX_OCCUR = 512`
tokens, and cited CBM's `CBM_SEM_MAX_OCCUR` — but CBM
(`semantic.c:874 cooccur_sparse_one_target`) strides only a **single token's**
co-occurrence pass when that **token** occurs > 512 times, never the first-order
term. This harness measured which behavior a retrieval benchmark actually wants.

- Harness: `compare_subsampling.py` (this directory) — monkeypatches the
  `embed_text` the #169 SQLite fallback provider calls, then drives the exact
  `run_sqlite_fallback_bench._eval_mode("fallback", …)` scoring path so the only
  variable is the embedding function.
- Dataset: `benchmarks/longmemeval/longmemeval_s.json` (Wu et al., ICLR 2025),
  variant `s`, `--limit 50`.
- Date: 2026-07-25 (UTC). Environment: CPU, macOS dev host, in-memory
  `SqliteMemoryStore` per question, `CORTEX_EMBEDDING_ZERO_DOWNLOAD=1`.

## Why this dataset exercises the branch

Measured on the n=50 haystack (2556 stored memories):

- token count per memory: median **1622**, p90 2782, max 6008.
- **86.2%** of memories exceed `_MAX_OCCUR = 512` tokens → the *shipped*
  document-length stride fires on the majority of stored vectors.
- the largest single-token within-document repetition is **609**; only **2 of
  2556** memories contain a token repeating > 512 times → the *CBM-faithful*
  per-token trigger is inert on realistic prose, exactly as `semantic.h:52`
  claims ("Rare/high-IDF … tokens fall under the cap and are untouched").

So this is not a synthetic stress: the shipped striding was silently active on
most of the benchmark, and the two semantics are genuinely distinguishable here.

## Variants

- **off** — stride forced to 1 (no subsampling anywhere).
- **current** — the shipped behavior: `stride = max(1, n // _MAX_OCCUR)` applied
  to the whole loop (first-order terms included).
- **faithful_a** — CBM-faithful: first-order terms always complete; a token
  whose within-document occurrence count exceeds `_MAX_OCCUR` has *only its
  co-occurrence pass* strided.

## Results (LongMemEval-S, n = 50)

| variant     |    MRR | Recall@10 | elapsed | vs off              |
|-------------|-------:|----------:|--------:|---------------------|
| off         | 0.3786 |     68.0% |  62.0 s | —                   |
| current     | 0.3777 |     66.0% |  31.8 s | ΔMRR −0.0009, ΔR@10 −2.0 pp |
| faithful_a  | 0.3786 |     68.0% |  57.3 s | ΔMRR ±0.0000, ΔR@10 ±0.0 pp |

## Decision

**faithful_a (option (a) in the issue).** The shipped document-length striding
does not merely fail to help — it **hurts** (−2.0 pp Recall@10), because it drops
the first-order term at half the positions of the ~86% of memories over the cap,
a document CBM would never subsample. `faithful_a` is byte-identical in score to
`off` here (it fires on only 2/2556 memories) while restoring §8 source fidelity:
the `# source:` comment and the module docstring — which already described the
CBM per-token semantics — now match the code. Removal would score the same as
`faithful_a` but would delete a source-faithful, genuinely-firing (2/2556) cost
guard that the docstring documents and the issue's acceptance criteria (tested
stride branch + boundary + negative assertion) expect to remain.

The cost guard's benefit is bounded work on a *pathological single-token* memory;
its cost is nil on normal prose. It is kept for parity with the cited source, not
as a hot-path optimization.

Reproduce:

```
python3 benchmarks/results/subsample-fidelity-184/compare_subsampling.py
```
