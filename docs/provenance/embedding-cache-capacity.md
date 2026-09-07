# Embedding cache capacity: observed test session

The default capacity is eight entries: the eight distinct embedding inputs
observed in one real resident capture worker serving four synthetic Bash events.
The checked-in fixture is `benchmarks/fixtures/green_capture_embedding_session.jsonl`;
its 14 calls preserve the worker's exact order and arguments. It contains synthetic
content only. SHA256: `56c6626bc2369eeedbf0e07f393e1862fe8cb0dd7a8fe7caa9cd5e34703577d7`.

On 2026-09-07, the pinned neural model `all-MiniLM-L6-v2` revision
`1110a243fdf4706b3f48f1d95db1a4f5529b4d41` replayed capacities 0, 8 and the
previous 128. Python 3.12.11, macOS ARM64, source
`6588b408d82dedbd0e207d3a1d40364efbbe0131`; four repetitions per condition,
first discarded. One local heavy process; durable offline model cache; model
initialization and the optional complete-session primer are outside replay timing.

| Capacity | Primer | Hits / 14 | Median CPU ms | Median wall ms |
|---:|:---:|---:|---:|---:|
| 0 | False | 0 | 63.449 | 48.517 |
| 0 | True | 0 | 63.457 | 48.371 |
| 128 | False | 6 | 39.516 | 30.118 |
| 128 | True | 14 | 0.116 | 0.174 |
| 8 | False | 6 | 40.957 | 33.351 |
| 8 | True | 14 | 0.112 | 0.143 |

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
`/private/tmp/cortex-green-w3-4-capacity8-real/`.

These measurements precede the final merge-base synchronization. They establish
the sizing hypothesis; final validation must repeat them on the published head.
