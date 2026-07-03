#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# THE single source of truth for reproducing Cortex's benchmark + ablation
# numbers. One command, one clean ephemeral database, deterministic output.
#
#   make reproduce            # everything: all benchmarks + ablation sweep
#   make reproduce-smoke      # same pipeline, tiny limits — end-to-end in minutes
#
# What it does, in order, against ONE isolated PostgreSQL+pgvector container:
#   1. Fetches + sha256-verifies every dataset it can pin (LongMemEval-S).
#   2. Starts an ephemeral pgvector container on a private port, isolated from
#      any Cortex install you already run.
#   3. Runs each retrieval benchmark through the SAME production PL/pgSQL recall
#      path (no benchmark-only retriever): LongMemEval-S, LoCoMo, BEAM-100K.
#   4. Runs the ablation sweep (baseline + the v4.0 mechanism group) through the
#      SAME harnesses via benchmarks/lib/ablation_runner.py.
#   5. Writes every result as JSON under benchmarks/results/repro/<timestamp>/,
#      writes a MANIFEST.json (git sha, dataset sha, image, package versions),
#      prints one consolidated table, and tears the container down.
#
# Every harness self-cleans: BenchmarkDB purges is_benchmark rows on open and
# deletes its own on close, so the phases are independent and the whole run is
# deterministic — take it, hit play, get the same numbers.
#
# Scope flags (compose):
#   --only <b>[,<b>...]   Run only these benchmarks (longmemeval|locomo|beam).
#   --no-ablation         Skip the ablation sweep (benchmarks only).
#   --ablation-only       Skip the plain benchmarks (ablation sweep only).
#   --ablate-on <b>       Which benchmark the ablation sweep drives (default: locomo).
#   --quick               Small per-benchmark limits (fast end-to-end verification).
#   --limit N             Explicit per-benchmark question/conversation cap.
#   --keep-db             Leave the container running afterwards (debugging).
#   Anything else is passed through to the underlying run_benchmark.py calls.
#
# Environment overrides:
#   CORTEX_BENCH_PORT   host port for the ephemeral PG (default 55432)
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# ── The v4.0 mechanism group the ablation sweep covers — the SINGLE place this
# list is defined. Enum NAMEs from mcp_server/core/ablation.py; ablation_runner
# validates each against the live enum (unknown name => hard error), so a rename
# there surfaces here immediately. B1 procedural memory is intentionally absent:
# it is an opt-in recall_skills tool outside the recall-fusion path with no
# ablation guard, so it cannot move these benchmarks' recall. ACTIVE_FORGETTING
# is included though it predates v4.0 — it is the circuit that actually
# soft-deletes rows and thus the prime suspect for any multi-session recall drop.
V4_MECHANISMS=(
    ACTIVE_FORGETTING
    VALUE_PRIORITY
    HABITUATION
    CONFLICT_MONITOR
    DUAL_PROCESS
    SLEEP_PHASES
    TARGETED_REACTIVATION
    EXTINCTION
    STRESS_MODULATION
    GOAL_MAINTENANCE
    FORWARD_MODEL
    CONFABULATION_GATE
    ATTENTIONAL_CONTROL
)

# ── LongMemEval-S dataset (the one dataset we can pin by content hash).
DATASET_PATH="$REPO_ROOT/benchmarks/longmemeval/longmemeval_s.json"
# source: https://huggingface.co/datasets/xiaowu0162/LongMemEval
DATASET_URL="https://huggingface.co/datasets/xiaowu0162/LongMemEval/resolve/main/longmemeval_s"
# source: measured 2026-07-03 against the HF copy (278,025,796 bytes),
# byte-identical to the file behind every published Cortex result.
DATASET_SHA256="08d8dad4be43ee2049a22ff5674eb86725d0ce5ff434cde2627e5e8e7e117894"

# ── Ephemeral PostgreSQL + pgvector (any PG>=15 with vector works; the schema
# code creates the extension itself on first connect).
PG_IMAGE="pgvector/pgvector:pg16"
PG_PORT="${CORTEX_BENCH_PORT:-55432}"
CONTAINER="cortex-bench-pg"
BENCH_DB_URL="postgresql://postgres:cortex_bench@localhost:${PG_PORT}/cortex_bench"

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
RESULTS_DIR="$REPO_ROOT/benchmarks/results/repro/$STAMP"

# ── Parsed options (defaults) ────────────────────────────────────────────────
ONLY=""                 # empty => all benchmarks
RUN_ABLATION=1
RUN_BENCHMARKS=1
ABLATE_ON="locomo"
QUICK=0
LIMIT=""
KEEP_DB=0
PASSTHROUGH=()
started_container=0

# ── Helpers ──────────────────────────────────────────────────────────────────
need_cmd() {
    command -v "$1" >/dev/null 2>&1 || { echo "error: '$1' is required but not installed." >&2; exit 1; }
}

sha256_of() {
    if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}'
    else shasum -a 256 "$1" | awk '{print $1}'; fi
}

parse_args() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --only)          ONLY="$2"; shift 2 ;;
            --only=*)        ONLY="${1#*=}"; shift ;;
            --no-ablation)   RUN_ABLATION=0; shift ;;
            --ablation-only) RUN_BENCHMARKS=0; shift ;;
            --ablate-on)     ABLATE_ON="$2"; shift 2 ;;
            --ablate-on=*)   ABLATE_ON="${1#*=}"; shift ;;
            --quick)         QUICK=1; shift ;;
            --limit)         LIMIT="$2"; shift 2 ;;
            --limit=*)       LIMIT="${1#*=}"; shift ;;
            --keep-db)       KEEP_DB=1; shift ;;
            *)               PASSTHROUGH+=("$1"); shift ;;
        esac
    done
}

want_bench() {
    # want_bench <name> -> 0 if this benchmark should run given --only
    [ -z "$ONLY" ] && return 0
    case ",$ONLY," in (*",$1,"*) return 0 ;; esac
    return 1
}

fetch_longmemeval() {
    if [ -f "$DATASET_PATH" ]; then
        echo "==> LongMemEval dataset present."
    else
        echo "==> Downloading LongMemEval-S (~265 MB) from the official HF repo..."
        curl -L --fail --progress-bar -o "$DATASET_PATH" "$DATASET_URL"
    fi
    local actual; actual="$(sha256_of "$DATASET_PATH")"
    if [ "$actual" != "$DATASET_SHA256" ]; then
        echo "error: LongMemEval dataset checksum mismatch." >&2
        echo "  expected: $DATASET_SHA256" >&2
        echo "  actual:   $actual" >&2
        echo "Delete $DATASET_PATH and retry." >&2
        exit 1
    fi
    echo "==> LongMemEval checksum OK."
}

start_db() {
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
        echo "==> Reusing running container ${CONTAINER}."; return
    fi
    docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
    echo "==> Starting ephemeral PostgreSQL (${PG_IMAGE}) on port ${PG_PORT}..."
    docker run -d --name "$CONTAINER" \
        -e POSTGRES_PASSWORD=cortex_bench \
        -e POSTGRES_DB=cortex_bench \
        -p "${PG_PORT}:5432" \
        "$PG_IMAGE" >/dev/null
    started_container=1
    echo "==> Waiting for PostgreSQL to accept connections..."
    until docker exec "$CONTAINER" pg_isready -U postgres -d cortex_bench >/dev/null 2>&1; do
        sleep 1
    done
}

teardown() {
    if [ "$started_container" = "1" ] && [ "$KEEP_DB" != "1" ]; then
        echo "==> Removing ephemeral container ${CONTAINER} (--keep-db to keep)."
        docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
    fi
}

# One benchmark through the production recall path, result JSON to RESULTS_DIR.
run_bench() {
    local name="$1"; shift          # longmemeval-s | locomo | beam-100K
    local script="$1"; shift        # path to run_benchmark.py
    local out="$RESULTS_DIR/${name}.json"
    echo
    echo "════════════════════════════════════════════════════════════════════"
    echo "  BENCHMARK: $name"
    echo "════════════════════════════════════════════════════════════════════"
    DATABASE_URL="$BENCH_DB_URL" uv run --extra benchmarks python \
        "$script" --results-out "$out" "$@" "${PASSTHROUGH[@]}"
}

# Map a short benchmark name (locomo|beam|longmemeval) to the ablation runner's
# full benchmark ID (locomo|beam-100K|longmemeval-s). Idempotent: a full ID
# passed in maps to itself.
ablation_bench_id() {
    case "$1" in
        longmemeval|longmemeval-s) echo "longmemeval-s" ;;
        beam|beam-100K)            echo "beam-100K" ;;
        locomo)                    echo "locomo" ;;
        *)                         echo "$1" ;;
    esac
}

run_ablation_sweep() {
    local bench_id; bench_id="$(ablation_bench_id "$ABLATE_ON")"
    echo
    echo "════════════════════════════════════════════════════════════════════"
    echo "  ABLATION SWEEP on '$bench_id' (baseline + ${#V4_MECHANISMS[@]} mechanisms)"
    echo "════════════════════════════════════════════════════════════════════"
    local mech_args=()
    local m
    for m in "${V4_MECHANISMS[@]}"; do mech_args+=(--mechanism "$m"); done
    local quick_arg=()
    [ "$QUICK" = "1" ] && quick_arg+=(--quick)
    # ablation_runner establishes the BASELINE itself when absent, then runs one
    # trial per --mechanism, saving to benchmarks/results/ablation/<bench>/.
    DATABASE_URL="$BENCH_DB_URL" uv run --extra benchmarks python \
        "$REPO_ROOT/benchmarks/lib/ablation_runner.py" \
        --benchmark "$bench_id" "${mech_args[@]}" "${quick_arg[@]}"
}

write_manifest() {
    local git_sha; git_sha="$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || echo unknown)"
    DATABASE_URL="$BENCH_DB_URL" uv run --extra benchmarks python - "$RESULTS_DIR" "$git_sha" "$DATASET_SHA256" "$PG_IMAGE" <<'PY'
import json, sys, platform, subprocess
from pathlib import Path
results_dir, git_sha, ds_sha, pg_image = sys.argv[1:5]
def ver(pkg):
    try:
        import importlib.metadata as m
        return m.version(pkg)
    except Exception:
        return "absent"
manifest = {
    "git_sha": git_sha,
    "longmemeval_dataset_sha256": ds_sha,
    "pg_image": pg_image,
    "python": platform.python_version(),
    "packages": {p: ver(p) for p in
                 ("datasets", "sentence-transformers", "psycopg", "psycopg-pool")},
    "results_files": sorted(p.name for p in Path(results_dir).glob("*.json")),
}
out = Path(results_dir) / "MANIFEST.json"
out.write_text(json.dumps(manifest, indent=2))
print(f"==> Wrote {out}")
PY
}

print_summary() {
    local abl_id; abl_id="$(ablation_bench_id "$ABLATE_ON")"
    uv run --extra benchmarks python - "$RESULTS_DIR" "$REPO_ROOT/benchmarks/results/ablation/$abl_id" <<'PY'
import json, sys
from pathlib import Path
repro_dir, abl_dir = Path(sys.argv[1]), Path(sys.argv[2])
def load(p):
    try: return json.loads(Path(p).read_text())
    except Exception: return {}
print("\n" + "=" * 68)
print("  CONSOLIDATED RESULTS  ({})".format(repro_dir.name))
print("=" * 68)
print(f"{'benchmark':<20}{'MRR':>12}{'Recall@10':>14}{'n':>8}")
print("-" * 68)
for f in sorted(repro_dir.glob("*.json")):
    if f.name == "MANIFEST.json": continue
    d = load(f)
    mrr = d.get("overall_mrr"); r10 = d.get("overall_recall10")
    n = d.get("n_questions") or d.get("n_conversations") or d.get("n") or ""
    smrr = f"{mrr:.4f}" if isinstance(mrr, (int, float)) else "—"
    sr10 = f"{r10:.4f}" if isinstance(r10, (int, float)) else "—"
    print(f"{f.stem:<20}{smrr:>12}{sr10:>14}{str(n):>8}")
# Ablation deltas vs baseline, if present.
base = load(abl_dir / "BASELINE.json")
b_mrr = base.get("mrr") or base.get("overall_mrr")
if isinstance(b_mrr, (int, float)):
    print("\n" + "-" * 68)
    print(f"  ABLATION vs baseline MRR={b_mrr:.4f} on {abl_dir.name}")
    print(f"{'mechanism ablated':<28}{'MRR':>10}{'ΔMRR':>12}")
    print("-" * 68)
    for f in sorted(abl_dir.glob("*.json")):
        if f.stem == "BASELINE": continue
        d = load(f)
        m = d.get("mrr") or d.get("overall_mrr")
        if not isinstance(m, (int, float)): continue
        print(f"{f.stem:<28}{m:>10.4f}{m - b_mrr:>+12.4f}")
print("=" * 68)
PY
}

main() {
    parse_args "$@"
    need_cmd docker; need_cmd curl; need_cmd uv
    if ! docker info >/dev/null 2>&1; then
        echo "error: the Docker daemon is not running (start Docker Desktop / colima)." >&2
        exit 1
    fi
    mkdir -p "$RESULTS_DIR"

    # Only fetch datasets for benchmarks that will actually run.
    if [ "$RUN_BENCHMARKS" = "1" ] && want_bench longmemeval; then fetch_longmemeval; fi
    if [ "$RUN_ABLATION" = "1" ] && [ "$ABLATE_ON" = "longmemeval-s" ]; then fetch_longmemeval; fi

    start_db
    trap teardown EXIT
    cd "$REPO_ROOT"

    # Per-benchmark limit args.
    lm_args=(); lo_args=(); be_args=(--split 100K)
    if [ -n "$LIMIT" ]; then lm_args+=(--limit "$LIMIT"); lo_args+=(--limit "$LIMIT"); be_args+=(--limit "$LIMIT")
    elif [ "$QUICK" = "1" ]; then lm_args+=(--limit 10); lo_args+=(--limit 1); be_args+=(--limit 2); fi

    if [ "$RUN_BENCHMARKS" = "1" ]; then
        want_bench longmemeval && run_bench "longmemeval-s" \
            "benchmarks/longmemeval/run_benchmark.py" "${lm_args[@]}"
        want_bench locomo && run_bench "locomo" \
            "benchmarks/locomo/run_benchmark.py" "${lo_args[@]}"
        want_bench beam && run_bench "beam-100K" \
            "benchmarks/beam/run_benchmark.py" "${be_args[@]}"
    fi

    if [ "$RUN_ABLATION" = "1" ]; then
        run_ablation_sweep
    fi

    write_manifest
    print_summary
    echo
    echo "==> All artifacts under: $RESULTS_DIR"
    if [ "$RUN_ABLATION" = "1" ]; then
        echo "==> Ablation artifacts under: benchmarks/results/ablation/$(ablation_bench_id "$ABLATE_ON")/"
    fi
}

main "$@"
