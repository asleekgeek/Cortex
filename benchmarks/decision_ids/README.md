# Decision ID source-coverage benchmark

Run `python -m benchmarks.decision_ids.run_bench --output result.json`, or select
`--only decision-ids` in the reproduction driver.

The five boundary IDs exist only in a temporary canonical project wiki. The
baseline executes the pre-change unified-search handler at the pinned commit
with an empty memory source and AP disabled. The candidate must return each ID
first, with zero embedding, memory-store, AP or semantic-recall calls.

This checks wiki source coverage and deterministic identity dispatch. It does
not measure PostgreSQL ranking, model quality or full retrieval performance.
The recorded initial result is `docs/benchmarks/issue-514-known-item.json`.
