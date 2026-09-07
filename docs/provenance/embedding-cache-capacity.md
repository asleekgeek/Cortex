# Embedding cache: context identity and rejected capacity reduction

The scalar cache retains its pre-W3-4 capacity of 128. Ordinary `encode_batch`
keeps the original batch inputs and does not read or populate the scalar cache.
Only the existing explicit `warm_cache` API populates it from batch vectors.
Scalar lookup counters and a zero-capacity measurement control remain available.

This retains existing behavior; it does not establish 128 as an optimal size.
The eight-entry candidate passed its initial working-set fixture but failed the
subsequent context/eviction counterexample. Removing the cache also changes the
existing warm_cache contract. No replacement capacity is adopted on this evidence.

## Real-model context counterexamples

Reference `1b497a61a57e566f033eb26f9f15bf7fd2f1c1e4`, rejected candidate
`0454cb4ea7f6cb122e0fd9dde7ac4e806237d9a3`. CPU, Python3.13.7,
SentenceTransformers5.6.1, PyTorch2.13.0, NumPy2.5.1, MiniLM revision
`1110a243fdf4706b3f48f1d95db1a4f5529b4d41`. Four repetitions, first discarded;
model warmed outside each replay, cache cleared before every scenario. One
heavy local process, offline model cache, identical dependencies on both sides.

| Scenario | Exact API traces, all retained pairs | Maximum absolute float32 delta |
|---|---|---:|
| Cold batch | Equal | 0 |
| Scalar then batch | Different | 1.0617077350616455e-7 |
| Batch then scalar | Different | 1.0617077350616455e-7 |
| Explicit warm then scalar | Equal | 0 |
| Batch with duplicate input | Equal on this fixture | 0 |
| Same text in a later singleton batch | Different | 1.0617077350616455e-7 |
| Repeated scalar | Equal | 0 |
| Warm nine observed texts, then encode the first (128→8 entries) | Different | 1.0617077350616455e-7 |

The inputs were already recorded by the public compression-workload probe;
there is no invented tolerance. Stored scalar and batch bytes differ even
though their text is identical. A text-only cache substitutes one computation
context for another. PyTorch documents that mathematically equivalent batched
and individual operations need not produce bitwise-identical results:
https://docs.pytorch.org/docs/2.14/notes/numerical_accuracy.html#batched-computations-or-slice-computations
That general contract is consistent with the measured PyTorch2.13 result here;
it is not a claim that the documentation's runtime version was benchmarked.

The complete real inference traces and execution manifests are at
`/private/tmp/cortex-green-w3-4-counterexample-cache-before.json`,
`/private/tmp/cortex-green-w3-4-counterexample-cache-after.json`, and
`/private/tmp/cortex-green-w3-counterexamples-after-stop.json`.
The recorded public vectors in `tests_py/fixtures/w3_4/cache_context.json`
exercise the actual cache with a provider double, without importing a neural
runtime. Three context tests fail on the rejected candidate; explicit warming
passes. The double is a cache regression test, not a new model measurement.

## Historical working-set measurement (candidate rejected)

The 14-call public resident-capture trace contains eight unique texts:
`benchmarks/fixtures/green_capture_embedding_session.jsonl`, SHA256
`56c6626bc2369eeedbf0e07f393e1862fe8cb0dd7a8fe7caa9cd5e34703577d7`.
It was measured on `2870f53d6bf133a55685c000d920cef3263863e2`, before removal
of the shared batch cache. Four repetitions per condition, first discarded;
initialization and the optional session primer excluded from the timing.

| Capacity | Primer | Hits / 14 | Median CPU ms | Median wall ms |
|---:|:---:|---:|---:|---:|
| 0 | False | 0 | 65.673 | 50.926 |
| 0 | True | 0 | 63.973 | 54.949 |
| 8 | False | 6 | 40.275 | 30.449 |
| 8 | True | 14 | 0.137 | 0.158 |
| 128 | False | 6 | 41.646 | 34.754 |
| 128 | True | 14 | 0.132 | 0.198 |

All vector digests on that trace were
`26f406355a13538dd7d1f40603526f5b0bb5e696020770389ea115a1414d6919`.
Those observations remain valid for that candidate and fixture. They cannot
justify the rejected capacity or batch cache for other API histories. These
are historical timings, not performance numbers for the corrected engine.
Raw records: `/private/tmp/cortex-green-w3-4-cache-final/`.

For future measurements the retained script is
`python -m scripts.measure_embedding_cache --fixture SESSION.jsonl --output
RESULT.json --capacity N`, optionally `--warm-session`, in the closed offline
benchmark environment. Its counters now observe scalar lookups only; batch
calls do not change cache statistics. Record the new source SHA and compare
complete output digests before interpreting any timing or hit-rate changes.

## Corrected engine: real replay

At `4a224e70d9c3aa85f6d5283188c1997c3d9a8e86`, all eight API scenarios above
match the reference's complete vector-byte traces in every retained repetition
(maximum delta0), including the nine-text warm/eviction case. Both capacities
are128. The before/after processes use identical actual Python, packages, model
revision and inputs. The corrected batch body is AST-identical to the reference
apart from its docstring. The four recorded-provider regression tests pass;
three failed before the correction.

Proofs: `/private/tmp/cortex-green-w3-4-corrected-cache-after.json` and
`/private/tmp/cortex-green-w3-4-corrected-real-proofs.json`. These establish the
observed context identity, not an optimal capacity or a full retrieval floor.
