# W3-4: measured batch boundaries and rejected conversions

W3-4 retains batching only for independent codebase-file imports. Seed, lessons,
wiki imports, CLS, dream replay, stale-vector repair, embedding upgrade and
compression retain their original scalar paths. Their real-model counterexamples
violate the strict vector-identity requirement; their measured batch speedups
are rejected. Ordinary batches also keep their own inference context and do
not populate or read the scalar cache; see `embedding-cache-capacity.md`.
The one-batch-for-every-writer acceptance target is not met.

## Measurement conditions and outcomes

On 2026-09-07, original committed function fixtures and integrated handlers were
executed with the real CPU MiniLM revision
`1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, Python3.13.7,
SentenceTransformers5.6.1, Torch2.13.0 and NumPy2.5.1. Four pairs per caller,
first discarded, model already warm and raw cache cleared before each variant.
Row stores and metadata/entity collaborators are deterministic doubles. Exact
serialization distinguishes JSON types and compares all vector bytes, caller
outcomes, row fields, read/write order and telemetry counts. No tolerance,
physical-energy claim or production workload extrapolation is made.

The first fixture used 32 public energy-workload texts. It passed for eight
callers, but compression differed by up to1.3969838619232178e-7. That original
compression module was restored and a real replay confirmed zero delta in all
three retained pairs, with 64 scalar calls on both sides and no useful gain.
A transferred pair of already observed texts then exposed the other failures:

| Caller | Maximum raw float32 delta, all retained pairs | Final decision |
|---|---:|---|
| Seed | 1.0617077350616455e-7 | Original scalar caller restored |
| Lessons | 9.313225746154785e-8 | Original scalar caller restored |
| Wiki seed | 1.0617077350616455e-7 | Original scalar caller restored |
| CLS | 1.0617077350616455e-7 | Original scalar caller restored |
| Dream replay | 1.0617077350616455e-7 | Original scalar caller restored |
| Stale-vector repair | 1.0617077350616455e-7 | Original scalar caller restored |
| Embedding upgrade | 1.0617077350616455e-7 | Original scalar caller restored |
| Codebase, transferred pair | 0 | Further checks below |

All non-vector fields and event order matched on these completed counterexample
runs. Candidate source: `0454cb4ea7f6cb122e0fd9dde7ac4e806237d9a3`;
pre-W3-4 reference: `1b497a61a57e566f033eb26f9f15bf7fd2f1c1e4`.
Raw records: `/private/tmp/cortex-green-w3-4-counterexample-bulk-final.json`,
`/private/tmp/cortex-green-w3-4-counterexample-direct-final.json` and the
execution manifest `/private/tmp/cortex-green-w3-counterexamples-after-stop.json`.

## Retained codebase batch

The original 32-text codebase fixture used32 scalar calls; the candidate used
one batch. Median CPU129.897→53.814ms, wall112.143→37.516ms; every vector,
row, result and event matched. That source was
`0fe187b73fdc8386527584d99a82d46ebc7935ce`; raw record:
`/private/tmp/cortex-green-w3-4-real-remaining-callers-final.json`.
These timings describe that candidate, before the shared-cache correction.

Three additional source-0454 comparisons preserve exact results in all retained
pairs: the transferred pair,64 observed compression strings through the file
loop, and those64 strings represented as valid Python module docstrings through
the actual production parser and `build_memory_content`. A real-parser boundary
case with an empty Python file and a documented file also matches exactly.
The real-parser runs keep only storage and metadata/entity collaborators doubled.
Raw records:
`/private/tmp/cortex-green-w3-4-counterexample-codebase-real-parser.json` and
`/private/tmp/cortex-green-w3-4-counterexample-codebase-empty-docstring.json`.
A failed initial serializer attempt produced no accepted result; its corrected
replay explicitly serializes FileAnalysis dataclasses with their type and fields.
These finite fixtures are evidence for the retained path, not a universal
floating-point equivalence guarantee. Corrected-engine replay is recorded below; final repository gates and retrieval
quality remain separate requirements.

## Preserved preparation and sequential behavior

Codebase batching uses `remember.prepare_write`, `remember_bulk.prepare_bulk`
and explicit `PreparedEncoding` values. The public remember API is unchanged.
Only forced/deliberate writes without supersession or frozen gate observations
are eligible. Hardened raw text is batched; actual normalized comparisons or
new merge text can still encode separately. Empty lots load no engine.

Preparation retains validation, root/domain resolution, producing channel and
W3-1a preflight order. Each continuation retains live provenance, novelty,
curation and store reads, memory insertion, triggers, entities, heat and mood.
Input/validation failures keep their original positions. Ordinary batch errors
log and retry scalar entries with the original per-entry handling. Store failures
retain the caller's existing partial-write/continue behavior.

File reads are prepared only when independent of writer state. Resolved paths
under configured database/CLAUDE_DIR/WIKI_ROOT, aliases and multiple hard links
retain sequential reads. An executed file-backed store double proves that the
first write can change a later source read; the guarded path matches the original.
The existing source tag classifier prevents codebase/imported/seeded producer
memories from publishing wiki pages. This does not provide isolation against an
external process changing files/configuration during the operation.

Remember telemetry includes each entry's own preparation and waiting through
its continuation. Intervals can overlap and must not be summed as CPU time.
No event-loop yield or global rendezvous is added. KeyboardInterrupt propagates;
preparation/batch interruption may precede all continuations and does not promise
the scalar path's partial-write prefix. The overall operation measurement must
account for abandoned work. No atomicity claim is made.

## Other scalar boundaries

Session imports and memify derivation retain live gate observations because
prior insertions affect later decisions and source IDs. Compression's clock and
multi-stage archive/update schedule remains unchanged; a late tag error cannot
undo an earlier gist write. All originally restored writer modules are compared
against1b497a61, and their tests retain metadata, order and error assertions.

Original function bodies remain in `tests_py/fixtures/w3_4/*.py.txt` as
executable differential evidence. NumPy/provider doubles verify API and ordering
contracts but cannot prove neural scalar/batch equivalence. Full retrieval floors
and repository gates are separate acceptance checks; baseline floor failures
are not waived by these local comparisons.

## Corrected-source replay and final codebase timing

Source `4a224e70d9c3aa85f6d5283188c1997c3d9a8e86`, same pinned model and
protocol. All eight original/corrected caller comparisons pass with exactly
identical raw vectors, full outcomes, non-vector fields and event/read order.
Seed/lessons/wiki/CLS/replay/stale/upgrade now use their original scalar calls;
codebase keeps one batch. No gain is claimed for the restored scalar callers.
All eight cache API scenarios also match exactly, with capacity128 on both sides.
Execution report: `/private/tmp/cortex-green-w3-4-corrected-real-proofs.json`.

The corrected codebase path passes the actual-parser64-text fixture and the
empty-file/docstring boundary. Its final64-file timing uses the actual production
parser and content builder, observed public texts as module docstrings, real
MiniLM, and doubled storage/metadata/entity collaborators. Four paired runs,
first discarded; original caller fixtures are compared with the corrected caller.

| 64 files | Scalar API calls | Batch API calls | Median CPU ms | Median wall ms |
|---|---:|---:|---:|---:|
| Original | 64 | 0 | 346.133 | 280.398 |
| Corrected | 0 | 1 | 180.961 | 103.642 |

Every retained vector byte, row/result and event matches; no quality or physical
energy extrapolation. Final report
`/private/tmp/cortex-green-w3-4-final-host-codebase.json`; command and snapshots
`/private/tmp/cortex-green-w3-4-final-host-codebase-proof.json`.
`uptime`08:10, load3.50/4.50/4.99→3.26/4.42/4.95 for10cores;
`df -h /`38Gi available before/after. The command is the closed isolated wrapper,
root `.venv/bin/python`, and `/private/tmp/cortex-green-w3-4-final-host-codebase.py`.

Seven restored writer modules, including the earlier compression fix, are
byte-identical to1b497a61; `/private/tmp/cortex-green-w3-4-restore-source-proof.json`
records their hashes. The targeted boundary suite passes62tests with zero skips
in1.58s; Ruff/format and craftsmanship pass. The retained general preparation
helpers are exercised by codebase; the removed wiki batch helper has no caller.
