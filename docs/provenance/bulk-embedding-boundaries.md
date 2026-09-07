# W3-4: remaining raw-vector batch boundaries

## 1. Scope and reference

This supplements W3-4's direct-encoder/cache patch. It does not complete W3-4.
Reference: `d0f7c19bf64a2d994b2e9a2a9818244c994bc972`, followed by W3-1a,
W3-2 and the first W3-4 patch, in that order. The supplemental diff excludes
those prerequisites. No model, dimensions, normalization rule or cache capacity
changes here. Real-model quality, host timings and the empirical LRU decision
remain open.

The differential fixtures in `tests_py/fixtures/w3_4/*.py.txt` contain eleven
original function bodies, copied before this supplement. Their ASTs match the
reference bodies exactly. Tests execute them with the same storage/encoder
doubles as the new bodies; these are source fixtures, not replacement handlers.

| Fixture | Original module under `mcp_server/handlers/` | Original source SHA-256 |
|---|---|---|
| `remember` | `remember.py` | `9805012140cf787aae77dce1e744c313e68ac5dbf11530445256a7338c77a87c` |
| `seed` | `seed_project.py` | `6a09efe88f0e7eb2bd60cc34ab9fa89ea63b838c4846a7797a077bf0f849723b` |
| `lessons` | `record_session_end_memory.py` | `3ad45053a5ada8f20205affaf5c81ae5a54824752a477ac5b315bad60c7c245e` |
| `compression` | `consolidation/compression.py` | `3183c81e3a7246e8fe56cbe8461013df23216b5d182265f0d5305770b76a64a6` |
| `codebase` | `codebase_analyze.py` | `8ad8b2f40500457a61a5786381dd18d1c0d1e3660aa701eee5ac70c1a1839445` |
| `wiki_seed` | `wiki_seed_codebase.py` | `1835ad61c3ade58e521ccbe23bff0a358eebe01b031f3d35be325a8df8174a42` |

## 2. Preparation contract and invariants

`remember.prepare_write` extracts the original pre-encode phase, in order:
content hardening, connection root, argument defaults, write-class validation,
store lookup, supersession validation, domain resolution, producing-channel
classification, then the W3-1a preflight. The ordinary public handler uses the
same phase. No public MCP payload parameter changes.

`remember_bulk.prepare_bulk` accepts only explicitly forced or deliberate
writes, refuses supersession inputs and refuses a prepared gate observation.
It retains rejection/error positions and batches only valid hardened raw text.
`PreparedEncoding` explicitly carries preparation, engine/result and start
time; there is no proxy, global rendezvous, ContextVar or scheduled task.

The allowed callers do not modify the process environment, git metadata or
cognitive profile files between their writes. Domain resolution still reads
git first, then an explicit hint or the original profile fallback. Profile
loading/migration, where needed, remains in entry order. Remember's continuation
writes memory, triggers, entities, heat and mood; it does not save profiles or
change root scope. Provenance grading, novelty observation, curation and every
post-encode store read remain in their original sequential continuation.
This is a single-process contract, not isolation against an external writer
changing configuration or files during the call.

Ordinary input, validation and encoding errors are delivered at the original
item. Abort-on-error callers stop preparing after a validation/input failure;
the invalid entry and later entries are not encoded. Prior successful writes,
IDs, counters and heat updates occur before the error is raised during replay.
Best-effort callers retain their per-item catch and continue policy.

## 3. Implemented paths

| Caller | Nominal raw-vector batch | Retained boundary |
|---|---|---|
| `seed_project._store_discoveries` | One for validated harvested discoveries | Add `seeded`; original heat policy and success IDs after each write; abort at the same error item |
| `record_session_end_memory._try_store_lesson_candidates` | One for valid nonempty suggestions | Original strip/drop, exact summary prefix, deliberate provenance, per-suggestion catch/count |
| `codebase_analyze._process_files` | One when source reads are independent of writer state | Missing/incrementally unchanged files excluded; metadata then entities/relationships after each write |
| `wiki_seed_codebase.handler` via `wiki_seed_batch.import_files` | One when source reads are independent of writer state | Existing text truncation/tags; per-file errors/counts; pipeline only after imports |
| `compression._compress_to_tag_from_gist` legacy missing-gist/vector phase | One for its gist and tag | Only the phase whose two encodes have no intervening archive/update |

One batch means one public `encode_batch` for these raw vectors, not one batch
for the whole remember operation. W3-2's normalized-neighbor comparisons and
actual new merge texts can still encode separately. An empty eligible lot
does not initialize an engine or call either encoder.

After a whole-batch ordinary error, `embedding_batch` logs ERROR and retries
each eligible text scalarly, retaining the original per-item errors. Thus the
recovery branch makes one failed batch plus N scalar calls. If engine lookup
itself fails, its first item receives that error and subsequent continuations
retry lookup/scalar encoding at their original item. Extra speculative model
work can occur for valid entries beyond a later store failure; no later writes
occur for an aborting caller.

## 4. Executed counterexamples and remaining scalar paths

| Remaining path | Executed evidence | Guarantee preserved by leaving it scalar |
|---|---|---|
| `import_sessions._process_session_items` / `_store_memory` | `test_bulk_gate_dependencies`: two identical entries yield one store/one bounded rejection with live observations; freezing the first observation yields two stores | Earlier insertion changes habituation; bounded rejection performs no encode |
| `consolidation.memify_derive._derive_one` | Same module: live results are created/rejected; frozen results are created/created, with source IDs changing from 1 to 2 | Gate, provenance IDs, idempotence markers and counters follow prior writes |
| Codebase/wiki inputs aliasing writer state | `test_bulk_file_boundaries`: a store double writes a plain text state file; its later source alias sees the new text. Forcing preparation sees stale text; guarded execution matches the original | Reads remain interleaved with writes for state paths and aliases |
| `compression.run_compression_cycle` and `_compress_memory` across memories | `test_compression_batch_boundaries`: the actual schedule crosses the existing 168-hour threshold during a fake encoder advance; live schedule compresses IDs 1/2, a frozen schedule only ID 1 | Current clock-dependent schedule, protected/semantic skips, chunk order and MVCC read strategy |
| Normal compression 0→2 | Late tag RuntimeError and KeyboardInterrupt tests both retain the previously committed gist archive/update | Gist is committed before tag generation/encoding; no artificial atomicity |
| Compression 0→1 and 1→2 | Their one-vector phase has no independent second vector; cross-memory regrouping has the schedule counterexample above | Original archive/update and statistics order |

The file counterexample uses a plain file and a store double, not a real
database or a production observation. `file_reads_are_independent` resolves
paths/symlinks and excludes CLAUDE_DIR, WIKI_ROOT and both configured database
parent directories. Multiple hard links also keep the scalar route, since
another name may address mutable state. Resolution/settings errors retain the
scalar route and emit a debug diagnostic. This is deliberately conservative.
[Python's `os.stat_result.st_nlink`](https://docs.python.org/3.13/library/os.html#os.stat_result)
defines link multiplicity; the check is structural, not a tuned threshold.

An earlier suspected wiki-publication counterexample was disproved:
`wiki_classifier_patterns.AUDIT_TAGS` rejects `seeded`, `codebase` and
`imported` before user classification rules. A test invokes the real
`wiki_sync.build_from_memory` and proves that these producer tags yield no
page, even alongside `adr`. The file-state counterexample above does not claim
that these paths publish wiki pages.

## 5. Timing and interruption semantics

Each eligible entry records `perf_counter()` immediately before its own
remember preparation. The timestamp passes to the optional fourth parameter
of `_telemetry_wrap.instrument`. A success or failure in `store_prepared`
records elapsed time from that timestamp, including its preparation, later
preparations, batch work/recovery and preceding continuations. The intervals
overlap: `remember_ms` describes per-entry latency and must not be summed as
CPU consumption. No average allocation of batch duration is invented.

Caller-specific file reading, parsing or argument construction stays outside
the remember timing boundary, as in the original callers. Input-construction
failures emit no remember sample. Ordinary validation, engine lookup, encoding
and store failures do emit a failed sample when replay reaches their entry.
The default telemetry wrapper still starts a fresh clock on every public call
and records BaseException from a continuation before propagating it.

An interruption during preparation/batching occurs before continuations:
`KeyboardInterrupt` is not caught or downgraded. Its partial write prefix can
differ from the scalar reference (tested: one prior scalar write versus zero
batch writes). Entries never continued, including abandoned entries, emit no
completed remember sample. This does not promise interruption equivalence or
atomicity. The enclosing operation/process measurement remains necessary to
account for abandoned batch work.

## 6. Lightweight proof and review constraints

The supplemental runner passes 105 targeted tests with stdlib unittest and
NumPy float32 doubles. It blocks SQLite/psycopg connections and imports of
torch, sentence_transformers, flashrank and onnxruntime. The suite includes
W3-1a, W3-2, the first W3-4 cache/direct paths and the supplemental boundaries.
This is neither a model-quality proof nor a performance benchmark.

New timing tests use a simulated clock and assert exact per-entry intervals
for success, validation, getter, batch recovery and store failures. Default
wrapper behavior, continuation interruption, caller abandonment and absence
of extra event-loop yields are also checked. Source fixtures preserve the
eleven reference bodies rather than reimplementing expected behavior.

New files are below 300 lines; new functions stay within 40 lines, four
parameters and three control-flow nesting levels. Existing long function
spans do not grow: remember's main body shrinks, codebase's existing
six-parameter loop keeps its span. New batching helpers live in the bounded
`codebase_analyze_batch` module, with explicit callbacks and no import of the
caller. The existing codebase module grows from 461 to 485 lines for wiring
and shared argument/continuation helpers; its existing file-size violation
remains, with no craftsmanship baseline additions.

## 7. Integration and measurements still required

Integrate after W3-1a, W3-2 and the direct W3-4 patch, then run repository
gates. Reproduce the targeted suite using the archived isolated runner and
locked Python; no production state or model download is required.

For actual scalar→batch proof, replay the same authorized isolated fixture
against the original and integrated bodies, preserving raw text/order and
recording each code/fixture SHA, model revision, lockfile and backend. Use the
project §3 protocol (four runs, first discarded), one heavy run at a time.
Compare full caller outcomes, row/vector IDs, archive/update order and all
float32 vectors before reporting timing deltas; invoke the project's isolated
quality reproduction for the existing floors, without inventing tolerances.
Report enclosing user+sys CPU, wall and peak RSS; do not sum overlapping
remember latencies. Include encoding call counts and recovery diagnostics.

The previously delivered `scripts/measure_embedding_cache.py` separately
compares disabled/default capacity and cold/warm session replay with fixture
and code hashes. Keep the existing durable model cache and zero-download
guards. Its capacity experiment does not replace this before/after caller
comparison. The final capacity measurements justify eight entries on the
observed test session; see `embedding-cache-capacity.md`. They do not establish
a capacity optimum or replace the separate bulk-caller measurements.

### Final real-neural seed and lesson callers

At `3ec76b597d95f020f34b30cabc8118764d4a7303`, the original committed caller/
remember fixtures and the integrated seed/lesson callers were executed with
the real pinned MiniLM engine. The row store and other collaborators remained
deterministic doubles. Inputs were 32 public texts from the existing energy
workload. Four pairs per caller, first discarded; cache cleared before each.
All retained pairs preserve caller results, row contents/metadata, event and
read order, telemetry counts and every raw float32 vector byte (zero delta).

| Caller, 32 texts | Scalar calls before | Batch calls after | CPU median before/after | Wall median before/after |
|---|---:|---:|---:|---:|
| Seed | 32 | 1 | 117.659 / 34.391 ms | 105.798 / 23.381 ms |
| Lessons | 32 | 1 | 138.759 / 57.006 ms | 125.292 / 40.059 ms |

Python 3.13.7, CPU, MiniLM revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`.
Proof with all row/vector bytes, code and fixture hashes, load and disk:
`/private/tmp/cortex-green-w3-4-real-bulk-callers-final.json`; exact command:
`/private/tmp/cortex-green-final-probes-execution.json`. No physical energy or
production corpus extrapolation follows from these two caller fixtures.

Pending: other real-model bulk-caller comparisons, full retrieval floors,
and the explicitly scalar boundaries above.
W4-4's official API token-count calibration over 100 captured handler payloads
and the BEAM floors are still pending separate work; this supplement provides
no evidence that those criteria have passed.
