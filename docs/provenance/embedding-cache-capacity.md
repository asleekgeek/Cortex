# Embedding cache capacity: observed test session

The default capacity is eight entries: the eight distinct embedding inputs
observed in one real resident capture worker serving four synthetic Bash events.
The checked-in fixture is `benchmarks/fixtures/green_capture_embedding_session.jsonl`;
its 14 calls preserve the worker's exact order and arguments. It contains synthetic
content only. SHA256: `56c6626bc2369eeedbf0e07f393e1862fe8cb0dd7a8fe7caa9cd5e34703577d7`.

On 2026-09-07, the pinned neural model `all-MiniLM-L6-v2` revision
`1110a243fdf4706b3f48f1d95db1a4f5529b4d41` replayed capacities 0, 8 and the
previous 128. Python 3.13.7, macOS ARM64, source
`2870f53d6bf133a55685c000d920cef3263863e2`; four repetitions per condition,
first discarded. One local heavy process; durable offline model cache; model
initialization and the optional complete-session primer are outside replay timing.

| Capacity | Primer | Hits / 14 | Median CPU ms | Median wall ms |
|---:|:---:|---:|---:|---:|
| 0 | False | 0 | 65.673 | 50.926 |
| 0 | True | 0 | 63.973 | 54.949 |
| 8 | False | 6 | 40.275 | 30.449 |
| 8 | True | 14 | 0.137 | 0.158 |
| 128 | False | 6 | 41.646 | 34.754 |
| 128 | True | 14 | 0.132 | 0.198 |

Eight preserves both the cold-session 6/14 hits and the primed-session 14/14 hits
of capacity 128. All compared output vector digests are identical:
`26f406355a13538dd7d1f40603526f5b0bb5e696020770389ea115a1414d6919`.
Capacity eight is the smallest bound that retains this fixture's entire observed
working set between replays. It is not an optimal capacity claim for other users
or corpora. The timings do not establish a speed advantage of 8 over 128; eight
uses a smaller configured bound without losing any measured hits here. A longer
trace can justify a different capacity. Full retrieval floors remain separate.

Reproduce each cell with `python -m scripts.measure_embedding_cache --fixture
benchmarks/fixtures/green_capture_embedding_session.jsonl --output RESULT.json
--capacity CAPACITY`, adding `--warm-session` for primed cells. Set
`CORTEX_EMBEDDING_ZERO_DOWNLOAD=1` in the isolated measurement environment; run
cells serially. Raw local records and host before/after evidence:
`/private/tmp/cortex-green-w3-4-cache-final/`.

These measurements follow the final main rebase. The engine, cache and lockfile
SHA-256 values recorded in each result still match this checkout after the
separate W3-2 scalar-scoring correction. The final resident-worker trace also
reproduced the fixture SHA above. This proves the measured test-session capacity;
full retrieval floors and bulk-caller comparisons remain separate gates.
