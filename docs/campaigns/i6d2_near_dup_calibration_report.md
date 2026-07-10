# I6-D2 — Near-duplicate calibration campaign (INC6.4)

Branch `feat/near-dup-calibration`, base `main@7beb5640` (post I6-D1
exact-dedup, INC6.3). Decision: `inc6-design-campagne-memoire.md`, section
I6-D2. Q2 arbitration binding this campaign: **auto-supersession only at
the threshold where measured precision is 100%; otherwise review queue.**

## Method

1. Write-path hypothesis under test: `core/curation.py::decide_curation_action`
   treats `[0.6, 0.85)` cosine similarity as "link" and `>= 0.85` as
   "merge" (`MERGE_THRESHOLD = 0.85`, `curation.py:31`). Never validated
   retrospectively against the existing corpus.
2. Candidate-pair scan (`mcp_server/infrastructure/pg_store_near_dup.py::list_candidate_pairs`):
   an exhaustive O(n²) cosine scan over ~10k active memories is
   computationally unreasonable for a one-shot campaign (≈50M
   comparisons). Instead, for every active memory, a per-row approximate
   top-30 nearest-neighbor lookup via the existing HNSW index
   (`idx_memories_embedding`, `vector_cosine_ops`) — the same
   `ORDER BY <=> LIMIT K` pattern the production WRRF recall query
   already uses, run once per row. K=30 chosen from an ad hoc
   `EXPLAIN ANALYZE` check (2026-07-10) showing the 0.75-similarity
   candidate set per row saturates well under 30 members. This is an
   approximation — documented as such — not an exhaustive proof.
3. Deterministic stratified sample (`core/near_dup_calibration.py::stratified_sample`):
   ~100 pairs, evenly spaced by sorted `(id_a, id_b)` within each of 5
   strata around the 0.85 hypothesis (`0.75-0.80`, `0.80-0.85`,
   `0.85-0.90`, `0.90-0.95`, `0.95-1.00`) — 20 per stratum, no RNG, fully
   reproducible from the same candidate list.
4. Labeling: engineer agent (LLM judgment), reading BOTH full contents of
   every one of the 100 sampled pairs, verdict duplicate/distinct +
   1-line justification per pair — see
   `i6d2_labels_20260710T151000Z.json`.

## Distribution measured (2026-07-10, dev DB, 10024 active memories with embeddings)

Candidate pairs (undirected, deduplicated) at cosine similarity >= 0.75,
top-30 approximate neighbors per row:

| Stratum | Candidate pairs |
|---|---|
| 0.75–0.80 | 11,172 |
| 0.80–0.85 |  9,811 |
| 0.85–0.90 |  7,427 |
| 0.90–0.95 |  3,279 |
| 0.95–1.00 |  4,180 |
| **Total** | **35,869** |

Source: `docs/campaigns/i6d2_sample_to_label_20260710T150444Z.json` (`histogram` field).

## Precision measured at each threshold candidate (100 labeled pairs)

| S | n labeled >= S | duplicates | **precision** |
|---|---|---|---|
| 0.75 | 100 | 2 | 0.020 |
| 0.80 |  80 | 2 | 0.025 |
| 0.85 |  60 | 2 | 0.033 |
| 0.90 |  40 | 2 | 0.050 |
| 0.95 |  20 | 2 | 0.100 |

Source: `docs/campaigns/i6d2_calibration_report_20260710T150815Z.json`.

## Finding: the write-path hypothesis does not hold retrospectively

At every threshold candidate, precision is far below 1.0. Root cause,
visible directly in the labeled pairs (see justifications in
`i6d2_labels_20260710T151000Z.json`): the corpus is dominated by
auto-captured tool-call transcript memories (`# Tool: Read | **Read:**
...`, `# Tool: Bash | **stdout:** ...`, `# Tool: Write | **Artifact:**
...`). Their TEMPLATE text drives cosine similarity to 0.95–0.99+ even
when the referenced entity differs — most visibly, pairs of the shape
`# Tool: Read | **Read:** \`/Users/.../memories/checkpoints/<uuid>.md\``
where only the checkpoint UUID differs score 0.95–0.99 similarity while
referring to two DIFFERENT checkpoint files (different sessions'
state) — a textbook embedding-similarity false positive for
fact-level duplication, not a duplicate by any content standard.

Of the 100 labeled pairs, only **2** were genuine duplicates (same
underlying fact): a grep of an unchanged code block re-run after a
2-line unrelated edit shifted its line numbers (sim 0.9543), and a
`get_all_ddl()` read where one capture is a strict content-superset of
the other (sim 1.0000). Both happen to sit in the highest stratum
(0.95–1.00), yet that stratum's own precision is only 0.10 — 2 of 20 —
because the same stratum is saturated with checkpoint-UUID collisions.

**No threshold candidate (0.75, 0.80, 0.85, 0.90, 0.95) reaches 100%
measured precision.** Per I6-D2 step 6 / Q2 arbitration: **no
auto-collapse at all.**

## Treatment applied (Q2, no-threshold branch)

- Auto-supersession: **0 pairs** — the `run_near_dup_apply_pass` /
  `pg_store_memory_dedup.supersede_to_existing` write path exists and is
  tested (28/28, see below) but was never invoked against the dev DB in
  this campaign, because no threshold qualified. Zero DB writes.
- Review queue: **all 35,869 measured candidate pairs**
  (`docs/campaigns/i6d2_review_queue_full_20260710T150842Z.json`, id/id/
  similarity only — content extracts omitted from the full-queue
  artifact for size; the 100-pair labeled sample carries full extracts
  and is the audit trail for this campaign's conclusion). A reviewer
  processing any entry can fetch content on demand via
  `pg_store_near_dup.fetch_contents`.
- Acceptance-criterion note: the "SQL avant/après montrant une
  décroissance" criterion is **vacuous** here — no supersession lot was
  applied, so there is nothing to show decreasing. This is the honest,
  measured outcome, not a shortfall in the tooling: the tooling
  (candidate scan, stratification, precision selection, component
  election, CAS supersede-to-existing) is built, tested, and reusable
  the moment corpus composition changes enough to clear 100% precision
  at some band (e.g., after I6-D4's corpus-repair levers reduce
  auto-capture boilerplate collisions).

## Artifacts

- `i6d2_sample_to_label_20260710T150444Z.json` — full candidate scan
  (histogram) + the 100-pair deterministic stratified sample with full
  contents.
- `i6d2_labels_20260710T151000Z.json` — 100 labels (id_a, id_b,
  similarity, verdict, justification) — the auditable trail.
- `i6d2_calibration_report_20260710T150815Z.json` — precision per
  threshold candidate + selected threshold (`null`).
- `i6d2_review_queue_full_20260710T150842Z.json` — all 35,869 candidate
  pairs (id/id/similarity), the full review-queue backlog.

## Tooling (new, reusable for a future recalibration)

- `mcp_server/core/near_dup_calibration.py` — pure: stratification,
  deterministic sampling, precision-by-threshold, threshold selection,
  union-find connected components. 16 tests.
- `mcp_server/infrastructure/pg_store_near_dup.py` — candidate-pair HNSW
  scan, content fetch, member-stats fetch (effective_heat/created_at,
  reusing the exact-dedup CTE-hop pattern). 7 tests.
- `mcp_server/handlers/consolidation/near_dup_calibration_pass.py` —
  `run_near_dup_sample` (measurement) + `run_near_dup_apply_pass`
  (component supersession above S + review queue below S, reusing
  `core.memory_dedup_exact.elect_survivor` and
  `pg_store_memory_dedup.supersede_to_existing` from I6-D1). 5 tests.
- `scripts/near_dup_calibrate.py` — CLI: `sample`, `calibrate`, `apply`.

**28/28 tests green** (16 core + 7 infrastructure + 5 handler, all live
against `cortex_test`). `ruff format --check` and `ruff check` clean.
