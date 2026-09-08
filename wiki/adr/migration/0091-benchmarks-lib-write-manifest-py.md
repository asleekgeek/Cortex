# ADR-0091: benchmarks/lib/write_manifest.py implementation decisions

Status: accepted; preserved from the existing implementation during issue #514.

These are historical implementation records, not new algorithm or threshold choices.
Source: `benchmarks/lib/write_manifest.py`; original SHA-256 `a287409f62fc9bc8131d0360f715df01fdad9826a3a3fd1338db36700487bc42`.

## Original docstring, lines 1–20

````text
"""Write the MANIFEST.json describing exactly what produced a benchmark run.

Extracted verbatim from the heredoc previously embedded in
``benchmarks/reproduce.sh::write_manifest`` (behaviour unchanged) so the shell
driver stays within the size limits of coding-standards.md §4 and so this
provenance logic can be read, diffed and tested as Python.

Machine-load and disk-space snapshots live in sibling modules
(``machine_load_snapshot.py``, ``disk_space_snapshot.py``) — see their
docstrings for the two incidents that motivate recording them alongside
``git_sha`` in every manifest.

Usage (from reproduce.sh):
    python benchmarks/lib/write_manifest.py \\
        RESULTS_DIR GIT_SHA DATASET_SHA256 PG_IMAGE CONTAINER PG_PORT RUNNER_PID

    # Cell-start snapshot (call BEFORE start_db, so it also predates the
    # benchmark's own container/DB overhead):
    python benchmarks/lib/write_manifest.py --snapshot RESULTS_DIR
"""
````

## Original docstring, lines 89–97

````text
"""Exact model revision this run's EmbeddingEngine loaded.

    i7d3 reproducibility-gap fix (2026-07-11): uv.lock pins the Python package
    version but NOT the HF model weights an unpinned model name resolves
    against (refs/main can move independently of any pyproject/uv.lock change,
    with zero signal in this manifest before this fix). See
    mcp_server/infrastructure/embedding_engine.py's "Model revision pin"
    docstring for the incident this closes.
    """
````

## Original docstring, lines 111–118

````text
"""Load state + weights sha256 of the reranker, as this run observed it.

    Reranker cache-durability fix (2026-07-11, incident: silent reranker skip).
    Same shape of gap as embedding_revision above: a bare-except swallow in
    mcp_server.core.reranker let 6 LongMemEval runs execute with CE reranking
    silently disabled (MRR 0.9163 -> 0.8636), with nothing in the manifest to
    show it.
    """
````

## Original comment, lines 186–189

````text
# Alongside git_sha, not buried: see machine_load_snapshot.py and
        # disk_space_snapshot.py's docstrings for why (2026-08-10 sweep
        # incidents — CPU contention, then a full disk, both invisible in
        # a cell that merely finishes). Two points per resource, not one.
````

## Original comment, lines 195–200

````text
# Per-run container isolation fix (2026-07-11, incident: two concurrent
        # runs from different worktrees shared one fixed container/port and
        # silently cross-contaminated scores — 0.9163 isolated vs. 0.78-0.86
        # under concurrency). Recorded so a future diagnostic can always match a
        # result set to the exact container/port/PID that produced it instead
        # of guessing.
````

## Reviewed remaining docstring (benchmarks/lib/write_manifest.py, interim lines 53–60)

````text
Read back the cell-start snapshot written by `write_start_snapshot`.

Returns None (never raises) when absent — e.g. a `reproduce.sh` call
that predates this fix, or a caller that skipped the `--snapshot` step.
A missing start snapshot must not block the end-of-run manifest from
being written; the `_at_start` fields are simply absent in that case,
which is itself an observable fact rather than a silent guess.
````

