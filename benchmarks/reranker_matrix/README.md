# W4-2 reranker matrix: instrumentation, no default change

This is an experiment behind an explicit `reproduce.sh --reranker-cell` option.
Production code, the default L-12 model, SQL pools/weights/fusion, handler
headroom and the binary confidence gate are unchanged. No cell is selected
for adoption. Full measurements and a decision are still required.

| Cell | Model | Post-SQL prefix cap at benchmark top_k=10 | Floors/results |
|---|---|---:|---|
| l12-3x | current MiniLM L-12 | 30 | NOT RUN |
| l12-2x | current MiniLM L-12 | 20 | NOT RUN |
| l2-3x | TinyBERT L-2 | 30 | NOT RUN |
| l2-2x | TinyBERT L-2 | 20 | NOT RUN |

`fetch_k` here means the prefix **after** SQL fusion, before familiarity
triage. The SQL receives the same max_results and weights in every cell;
its five pool limits and complete TMM/boost computation do not change.
Only the returned prefix is varied. Other stages may change cardinality;
the sidecar records actual SQL rows, admitted rows, CE candidates, successful
reranked_count and wall/process CPU nanoseconds per call. No speedup is
inferred from the multiplier. Failed or silently skipped CE inference aborts
the experimental call. No calibration or confidence threshold changes.

The actual handler adds another overfetch when low-signal filtering is on:
`max_results=10 -> pg_recall.top_k=30 -> SQL up to 90 rows`. Thus these
experimental caps become **60/90**, not 20/30, on that normal handler path.
The pipeline slices to 30 after reranking, then the handler filters and caps
to 10 before its enrichments. With include_low_signal=true, that first
headroom is absent. This difference is externally checkable without a model:

```bash
python -m benchmarks.reranker_matrix.handler_probe
```

The probe executes the checked-in handler, recall wrapper, fetch/triage and
pipeline function bodies via AST, replacing only IO/neural stages with
fixtures. It observes the pre-enrichment cap, not final response latency or
quality. Its illustrative filter retains every second item; this is a fixture,
not a proposed change to the production low-signal rule.

## Verified model identity and cache

Sources consulted 2026-09-06:

- [FlashRank Config.py](https://github.com/PrithivirajDamodaran/FlashRank/blob/main/flashrank/Config.py)
  maps the model names to the ONNX filenames and identifies TinyBERT L-2 as
  the library default. The installed lock-pinned FlashRank 0.2.10 Config.py
  and Ranker.py were also read. Ranker requires config.json,
  tokenizer_config.json, special_tokens_map.json and tokenizer.json, and
  optionally reads vocab.txt. Its native download URL uses mutable main.
- [Official FlashRank model metadata at the pinned revision](https://huggingface.co/api/models/prithivida/flashrank/revision/858a1ac046a05663a35367eac852d7f76feeefdd?blobs=true)
  returned the following immutable revision and archive SHA256 values.
- Original [TinyBERT L-2 card](https://huggingface.co/cross-encoder/ms-marco-TinyBERT-L2-v2)
  and [MiniLM L-12 card](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L12-v2)
  identify the trained architectures. Their published MS MARCO/TREC numbers
  are not Cortex quality floors and are not used to choose a cell here.

Repository: `prithivida/flashrank`.
Revision: `858a1ac046a05663a35367eac852d7f76feeefdd`.
Upstream archive repository declares CC-BY-SA-4.0; original model cards
separately declare Apache-2.0. Retain upstream provenance with downloaded files.

| Key | Archive | Archive SHA256 | API archive bytes |
|---|---|---|---:|
| l2 | ms-marco-TinyBERT-L-2-v2.zip | 752eddf1c5ece3c5e6115e9ab52eb3b16436bbf9b3a091cbb62b5b8eadc47105 | 3421983 |
| l12 | ms-marco-MiniLM-L-12-v2.zip | bdd3772b651ffc34f70e414049285bb55ccc6d1b8e29d0640f836d44f70ec77a | 22696961 |

Both pinned archives were downloaded and verified on 2026-09-07 in the
experimental durable cache below. L-2 ONNX SHA256 is
`a2b09fb0de692c052a55f4165c9461377b4a31115673b7adb428503d69109196`;
L-12 ONNX SHA256 is
`d3dd7b09fcf06b0c070081d6819b5effbb40b667bcad78b2d7543400271141d1`.
Every extracted file was compared against its pinned archive. The archives
contain six (L-2) and seven (L-12) `__MACOSX/._*` companion entries. These
metadata entries stay in the verified archive and are reported explicitly;
they are not extracted into the model tree. A companion must correspond to
a real model member. Traversal, symlinks, unrelated or unpaired paths still
fail before extraction. Thirty-three targeted tests pass, including both
directory and file companions. No inference or quality result is implied by
successful cache provisioning.

The experimental cache is `$XDG_CACHE_HOME/flashrank-matrix/<revision>/`,
falling back to `~/.cache/flashrank-matrix/<revision>/` via the existing
shared.platform helper. `CORTEX_RERANKER_MATRIX_CACHE` can specify its durable
parent. Temporary roots are explicitly refused. Model subdirectories remain
named as FlashRank expects; production `~/.cache/flashrank` is not modified.
Every preflight verifies the pinned archive hash and compares every extracted
file to that archive. Missing, changed or extra files fail before model import.
ONNX SHA256 is then derived from the verified archive content and included
in evidence; no unavailable L-2 ONNX hash has been invented.

Owner/root provisioning, when the download slot is authorized (outside /tmp):

```bash
python -m benchmarks.reranker_matrix.cache urls l2
python -m benchmarks.reranker_matrix.cache urls l12
```

These commands only print the exact URL, SHA256 and durable target archive
path. For the default cache parent, the owner-run commands are:

```bash
RERANKER_ARCHIVE_ROOT="${XDG_CACHE_HOME:-$HOME/.cache}/flashrank-matrix/858a1ac046a05663a35367eac852d7f76feeefdd"
mkdir -p "$RERANKER_ARCHIVE_ROOT"
curl --fail --location \
  'https://huggingface.co/prithivida/flashrank/resolve/858a1ac046a05663a35367eac852d7f76feeefdd/ms-marco-TinyBERT-L-2-v2.zip' \
  --output "$RERANKER_ARCHIVE_ROOT/ms-marco-TinyBERT-L-2-v2.zip"
curl --fail --location \
  'https://huggingface.co/prithivida/flashrank/resolve/858a1ac046a05663a35367eac852d7f76feeefdd/ms-marco-MiniLM-L-12-v2.zip' \
  --output "$RERANKER_ARCHIVE_ROOT/ms-marco-MiniLM-L-12-v2.zip"
```

If overriding the cache parent, use the durable paths printed by `urls`.
The `urls` command checks durability before these downloads. Then run:

```bash
python -m benchmarks.reranker_matrix.cache prepare l2
python -m benchmarks.reranker_matrix.cache prepare l12
```

Preparation never downloads anything itself. It validates the archive before
safe extraction, preserves the archive for later checks, and refuses an
existing mismatched cache instead of deleting it. Root/owner handles a corrupt
cache explicitly. Offline mode is forced inside every cell. The same selection
wraps the benchmark **and write_manifest.py**, so a L-2 result cannot accidentally
receive a L-12 hash in MANIFEST.json. Process-local patches and singleton state
are restored on exit. Production files and the existing CI cache key are
untouched; if a future cell is adopted, its revision, verified ONNX hash,
production cache path and CI key must change together. A future experimental
CI cache key must include this pinned revision, never only the model nickname.

## Reproducible execution and limits

Print the four commands without loading a model or starting Docker:

```bash
python -m benchmarks.reranker_matrix.matrix --output benchmarks/results/w4-2
```

In the parent's exclusive heavy-work slot, after provisioning both caches:

```bash
python -m benchmarks.reranker_matrix.matrix --output benchmarks/results/w4-2 --execute
```

The output directory must be new. Four full, sequential `reproduce.sh
--no-ablation` invocations use identical options and deterministic run ID;
only the cell and output path differ. No quick/limit option is inserted.
FlashRank must match the inspected 0.2.10 contract before any load. The final
matrix refuses mismatched schema/gate/code/lock hashes, package versions,
embedding revision, PG image or LongMemEval dataset SHA across cells.
LoCoMo and BEAM loader outputs are also fingerprinted in a read-only pass
before recall; their hashes must match across cells. The loader returns the
same re-iterable object, not a rewritten corpus. This pass is outside the CE
call timer and is performed in all cells.
Each uses reproduce.sh's independent ephemeral container, data cleanup,
datasets, production path and existing floor checks. Failures are retained;
the driver continues to the next cell and returns failure after collecting
all four outcomes. `matrix.json` includes each subprocess status, raw result
artifacts and measured reranker work. Logs are per cell. No best-cell selection
is automated. Inspect manifests for matching dataset/schema/gate identities
and load/disk snapshots before comparing quality or timing.

The runner's full LongMemEval/LoCoMo floors remain authoritative. Its BEAM
corpus was rebased and has **no validated floor**: report BEAM measurements
and this limitation, never a fabricated pass. LoCoMo's existing same-commit
variance/repetition policy remains in reproduce.sh. Do not adopt another
cell without the required floors and owner decision. All table cells above
remain NOT RUN until those artifacts exist.

Sources for measurements: Python [time](https://docs.python.org/3/library/time.html)
perf_counter_ns/process_time_ns and [statistics.median](https://docs.python.org/3/library/statistics.html#statistics.median).
Model/cache protocols: installed FlashRank 0.2.10 and the verified primary
sources above. Matrix/candidate sizes: W4-2 contract and current SQL/handler
boundaries, exercised by the fixture probe.
