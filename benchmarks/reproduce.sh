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
#   --reranker-cell <id>  W4-2 experiment (l2-2x|l2-3x|l12-2x|l12-3x);
#                         requires --no-ablation and pre-provisioned pinned cache.
#   --results-dir <path>  Explicit cell output directory (default remains timestamped).
#   --only decision-ids   Exact wiki ID known-item coverage (no model calls).
#   --no-regression       Blocking gate: also run --baseline-ref's benchmarks
#                          in the same container and fail only if HEAD is
#                          worse than ITS OWN baseline by more than
#                          REGRESSION_TOLERANCE — use this instead of
#                          lowering FLOOR_* when main itself no longer
#                          clears the published floors (see check_floors'
#                          comment below and benchmarks/lib/bench_regression.sh).
#                          Full runs (no --quick/--limit) only; roughly
#                          doubles wall time (runs the suite twice).
#   --baseline-ref <ref>   Ref --no-regression compares HEAD against.
#                          Default: origin/main.
#   Anything else is passed through to the underlying run_benchmark.py calls.
#
# Environment overrides:
#   CORTEX_BENCH_PORT   pin the host port for the ephemeral PG (default: a
#                       kernel-assigned free port, discovered per run — see
#                       "Per-run container isolation" below). Set this only if
#                       you need a stable, predictable port; you take on the
#                       cross-worktree collision risk it existed to prevent.
#
# Per-run container isolation (fix 2026-07-11, incident: two concurrent
# `make longmemeval` runs from different worktrees silently cross-
# contaminated each other's scores with no visible error — 0.9163 isolated
# vs. 0.78-0.86 measured under concurrency. Root cause: every worktree
# checkout runs this SAME script but with a FIXED container name
# (cortex-bench-pg) and FIXED port (55432), so two runs from different
# worktrees raced on ONE shared container/database. The intra-worktree
# mkdir-lock below did not (and structurally cannot) catch this: its lock
# directory lives under REPO_ROOT, which is a *different path per worktree*,
# so two worktrees each acquire their own lock and both proceed into
# start_db() believing they are the only run. Same family as 2304cdda
# (tests_py/conftest.py per-process throwaway DB) — the fix is the same
# shape: give every run its own throwaway container AND port, name-tagged
# with the owning PID so a future diagnostic never has to guess again.
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

# ── Published floors the FULL runs are checked against. --limit/--quick runs
# skip the check (partial runs are not comparable to n=500 / n=1986 figures).
# Values: README benchmark tables (E1 v3 campaign). Tolerance 0.005 (0.5 pp)
# per the regression gate in benchmarks/results/a3_longmemeval_post_refactor.md
# (design §8). BEAM-100K is intentionally NOT checked: its published proxy
# numbers predate the 200→395-question split re-basing, and the README scopes
# BEAM to within-system comparison only.
#
# NON-BLOCKING as of the fix below (same disposition as the pyright ratchet,
# issue #188: "raising the floor would just hide the debt" — NO rebaseline,
# keep the drift visible without failing builds). Source: main@6ec76a0e
# measures LongMemEval MRR 0.904988 (< 0.914), LoCoMo MRR 3-run mean
# 0.779868 (< 0.805) and Recall@10 0.889506 (< 0.915) via THIS SAME script
# (cdeust/Cortex PR #492, 2026-09-07) — main itself no longer clears these
# floors, so treating them as blocking fails every PR built on top of main
# regardless of what that PR changes. The blocking gate for a PR is
# --no-regression (benchmarks/lib/bench_regression.sh): whether HEAD is
# worse than its OWN baseline, not whether it clears a number nothing
# currently clears. check_floors below still prints PASS/FAIL per metric —
# that visibility is the point — it just no longer exits 1.
FLOOR_LME_R10=0.982
FLOOR_LME_MRR=0.914
FLOOR_LOCOMO_R10=0.915
FLOOR_LOCOMO_MRR=0.805
FLOOR_TOLERANCE=0.005

# ── Ephemeral PostgreSQL + pgvector (any PG>=15 with vector works; the schema
# code creates the extension itself on first connect).
#
# CONTAINER and PG_PORT are per-run and finalized inside start_db(): the name
# carries this process's PID + a random suffix (mirrors conftest.py's
# cortex_test_pw<pid>_<hex>), and the port is kernel-assigned (docker -p 0)
# unless CORTEX_BENCH_PORT pins one explicitly. BENCH_DB_URL is therefore
# only valid AFTER start_db() returns — nothing before it in this script
# reads BENCH_DB_URL.
PG_IMAGE="pgvector/pgvector:pg16"
CONTAINER="cortex-bench-pg-$$-$(od -An -N4 -tx1 /dev/urandom | tr -d ' \n')"
PG_PORT=""
BENCH_DB_URL=""

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
RESULTS_DIR="$REPO_ROOT/benchmarks/results/repro/$STAMP"
LOCK_DIR="$REPO_ROOT/benchmarks/.reproduce.lock"

# ── Parsed options (defaults) ────────────────────────────────────────────────
ONLY=""                 # empty => all benchmarks
RUN_ABLATION=1
RUN_BENCHMARKS=1
ABLATE_ON="locomo"
QUICK=0
LIMIT=""
KEEP_DB=0
RERANKER_CELL=""        # explicit W4-2 experiment; production defaults unchanged
NO_REGRESSION=0
PASSTHROUGH=()
started_container=0

# shellcheck source=benchmarks/lib/bench_regression.sh
. "$REPO_ROOT/benchmarks/lib/bench_regression.sh"

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
            --reranker-cell) RERANKER_CELL="$2"; shift 2 ;;
            --results-dir)   RESULTS_DIR="$2"; shift 2 ;;
            --no-regression) NO_REGRESSION=1; shift ;;
            --baseline-ref)  BASELINE_REF="$2"; shift 2 ;;
            --baseline-ref=*) BASELINE_REF="${1#*=}"; shift ;;
            *)               PASSTHROUGH+=("$1"); shift ;;
        esac
    done
    check_reranker_cell
}

check_reranker_cell() {
    # Cell preflight precedes Docker/model loading. Its cache must already
    # contain the separately fetched, SHA-verified pinned archive and files.
    if [ -n "$RERANKER_CELL" ]; then
        if [ "$RUN_ABLATION" != "0" ]; then
            echo "error: --reranker-cell requires --no-ablation" >&2
            exit 1
        fi
        (cd "$REPO_ROOT" && uv run --extra benchmarks python -m \
            benchmarks.reranker_matrix.cache check "$RERANKER_CELL")
    fi
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

# Ephemeral container lifecycle (start_db/wait_for_db/remove_container and the
# orphan sweep). Sourced, not inlined, so this driver stays within the size
# limits of coding-standards.md §4; see that file for the readiness-probe
# provenance.
# shellcheck source=benchmarks/lib/bench_container.sh
. "$REPO_ROOT/benchmarks/lib/bench_container.sh"

# Intra-worktree guard only: two reproduce.sh invocations from the SAME
# checkout still share RESULTS_DIR's parent and DATASET_PATH, so a second
# concurrent run in this worktree can race the first's `curl` writing
# longmemeval_s.json (partial/corrupt file) or collide on a same-second
# STAMP. Cross-worktree contamination — the 2026-07-11 incident where two
# `make longmemeval` runs from different worktrees shared one FIXED
# container/port and silently corrupted each other's scores — is no longer
# possible regardless of this lock: start_db() now gives every run its own
# container name and port (see the file-header note). This lock cannot see
# across worktrees anyway (LOCK_DIR is under REPO_ROOT, which differs per
# checkout) — it never could, which is why it did not catch that incident.
# mkdir is the portable atomic lock — flock(1) does not ship on macOS.
acquire_lock() {
    if mkdir "$LOCK_DIR" 2>/dev/null; then
        echo $$ > "$LOCK_DIR/pid"
        return
    fi
    local holder; holder="$(cat "$LOCK_DIR/pid" 2>/dev/null || echo '?')"
    if [ "$holder" != "?" ] && kill -0 "$holder" 2>/dev/null; then
        echo "error: another reproduce.sh run (pid $holder) is already active." >&2
        echo "Concurrent runs share one database and corrupt each other's results." >&2
        echo "Wait for it to finish (or stop it), then retry." >&2
        exit 1
    fi
    echo "==> Removing stale lock (pid $holder is not running)."
    rm -rf "$LOCK_DIR" && mkdir "$LOCK_DIR" && echo $$ > "$LOCK_DIR/pid"
}

teardown() {
    remove_container
    rm -rf "$LOCK_DIR"
}

# One benchmark through the production recall path, result JSON to RESULTS_DIR.
run_bench() {
    local name="$1"; shift          # longmemeval-s | locomo | beam-100K
    local script="$1"; shift        # path to run_benchmark.py
    local out="$RESULTS_DIR/${name}.json"
    local entry=("$script")
    if [ -n "$RERANKER_CELL" ]; then
        entry=(-m benchmarks.reranker_matrix.entry "$RERANKER_CELL" "$script")
    fi
    echo
    echo "════════════════════════════════════════════════════════════════════"
    echo "  BENCHMARK: $name"
    echo "════════════════════════════════════════════════════════════════════"
    # ${arr[@]+...} keeps set -u safe when the array is empty on bash 3.2
    # (stock macOS /bin/bash); plain "${arr[@]}" aborts there. Fixed upstream
    # in bash 4.4, but strangers' Macs ship 3.2.
    DATABASE_URL="$BENCH_DB_URL" uv run --extra benchmarks python \
        "${entry[@]}" --results-out "$out" "$@" \
        ${PASSTHROUGH[@]+"${PASSTHROUGH[@]}"}
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
        --benchmark "$bench_id" "${mech_args[@]}" \
        ${quick_arg[@]+"${quick_arg[@]}"}
}

write_manifest() {
    local entry=("$REPO_ROOT/benchmarks/lib/write_manifest.py")
    if [ -n "$RERANKER_CELL" ]; then
        entry=(-m benchmarks.reranker_matrix.entry "$RERANKER_CELL" "${entry[0]}")
    fi
    local git_sha; git_sha="$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || echo unknown)"
    DATABASE_URL="$BENCH_DB_URL" uv run --extra benchmarks python \
        "${entry[@]}" \
        "$RESULTS_DIR" "$git_sha" "$DATASET_SHA256" "$PG_IMAGE" "$CONTAINER" "$PG_PORT" "$$"
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
    mrr = d.get("overall_mrr")
    # BEAM's runner writes overall_r10 / total_questions; the others write
    # overall_recall10 / n_questions. Explicit None checks — 0.0 is a value.
    r10 = d.get("overall_recall10")
    if r10 is None:
        r10 = d.get("overall_r10")
    n = ""
    for key in ("n_questions", "n_conversations", "total_questions", "n"):
        if d.get(key) is not None:
            n = d[key]
            break
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

# Report full-run results against the published floors: any score more than
# FLOOR_TOLERANCE below its floor prints FAIL. NON-BLOCKING (see the
# FLOOR_* comment above) — informational only, never exits 1. Rounds `got`
# to the same 4-decimal precision this prints before computing delta/status,
# so the verdict matches exactly what's on screen: comparing at a hidden
# precision beyond what's displayed is how a value that reads "0.9140" on
# one line could judge differently than "0.9140" on another.
#
# CAVEAT — this checks a SINGLE run, but LoCoMo's own same-commit noise is
# large relative to FLOOR_TOLERANCE. Measured 2026-07-14 at HEAD 5542aa71
# (v4.14.1), 3 isolated reps via `--only locomo`: MRR 0.7978 / 0.8019 / 0.8010
# (mean 0.8002, stdev 0.0022) against FLOOR_LOCOMO_MRR=0.805 tol=0.005 (needs
# >=0.800) — rep1 alone reads FAIL, reps 2 and 3 individually PASS, and the
# release's own actual stopping rule (the 3-run mean) passes by +0.0002. A
# signal-to-tolerance ratio of ~2.3 means a single unlucky rep has a real,
# observed chance of a false FAIL. Data + provenance:
# benchmarks/results/repro/20260714-floors-rebaseline/. Do NOT treat a single
# LoCoMo FAIL from this function as proof of a code regression — before
# bisecting, rerun `--only locomo` two more times and judge the floor against
# the 3-run mean (matching how 4.14.0/4.14.1 were actually released). This
# script does not automate that averaging; it is a manual step for whoever is
# gating a release.
check_floors() {
    uv run --extra benchmarks python - "$RESULTS_DIR" \
        "$FLOOR_LME_R10" "$FLOOR_LME_MRR" "$FLOOR_LOCOMO_R10" "$FLOOR_LOCOMO_MRR" \
        "$FLOOR_TOLERANCE" <<'PY'
import json, sys
from pathlib import Path
rd = Path(sys.argv[1])
lme_r10, lme_mrr, loc_r10, loc_mrr, tol = map(float, sys.argv[2:7])
floors = {
    "longmemeval-s": {"overall_recall10": lme_r10, "overall_mrr": lme_mrr},
    "locomo": {"overall_recall10": loc_r10, "overall_mrr": loc_mrr},
}
failed = False
for stem, expected in floors.items():
    p = rd / f"{stem}.json"
    if not p.exists():
        continue  # benchmark was scoped out via --only
    d = json.loads(p.read_text())
    for key, floor in expected.items():
        got = d.get(key)
        if not isinstance(got, (int, float)):
            print(f"FLOOR CHECK {stem}.{key}: metric missing — FAIL")
            failed = True
            continue
        got = round(got, 4)
        delta = got - floor
        status = "PASS" if delta >= -tol else "FAIL"
        if status == "FAIL":
            failed = True
        print(f"FLOOR CHECK {stem}.{key}: {got:.4f} vs floor {floor:.4f} ({delta:+.4f}) {status}")
if failed:
    print("\nFLOOR CHECK: full-run scores deviate from the published numbers (non-blocking).")
    print("This does not fail the build — see the FLOOR_* comment above for why, and use")
    print("--no-regression to gate a PR against its own baseline instead.")
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

    # Machine-load snapshot at cell START, before start_db so it predates
    # even the container/DB overhead — the counterpart to write_manifest's
    # end-of-run snapshot (2026-08-10 sweep-contention incident: a crashed
    # cell was the only visible symptom of contention that also silently
    # affected cells which merely finished; see write_manifest.py's
    # machine_load_snapshot docstring). Uses the base interpreter, not
    # `--extra benchmarks`, deliberately: this must succeed even if the
    # benchmarks extra install itself is what's under contention.
    uv run python "$REPO_ROOT/benchmarks/lib/write_manifest.py" \
        --snapshot "$RESULTS_DIR"

    # Only fetch datasets for benchmarks that will actually run.
    if [ "$RUN_BENCHMARKS" = "1" ] && want_bench longmemeval; then fetch_longmemeval; fi
    if [ "$RUN_ABLATION" = "1" ] && [ "$ABLATE_ON" = "longmemeval-s" ]; then fetch_longmemeval; fi

    if [ "$NO_REGRESSION" = "1" ]; then preflight_regression_datasets; fi

    acquire_lock
    trap teardown EXIT
    start_db
    cd "$REPO_ROOT"

    # Per-benchmark limit args.
    lm_args=(); lo_args=(); be_args=(--split 100K)
    if [ -n "$LIMIT" ]; then lm_args+=(--limit "$LIMIT"); lo_args+=(--limit "$LIMIT"); be_args+=(--limit "$LIMIT")
    elif [ "$QUICK" = "1" ]; then lm_args+=(--limit 10); lo_args+=(--limit 1); be_args+=(--limit 2); fi

    if [ "$RUN_BENCHMARKS" = "1" ]; then
        want_bench longmemeval && run_bench "longmemeval-s" \
            "benchmarks/longmemeval/run_benchmark.py" \
            ${lm_args[@]+"${lm_args[@]}"}
        want_bench locomo && run_bench "locomo" \
            "benchmarks/locomo/run_benchmark.py" \
            ${lo_args[@]+"${lo_args[@]}"}
        want_bench beam && run_bench "beam-100K" \
            "benchmarks/beam/run_benchmark.py" "${be_args[@]}"
        if want_bench decision-ids; then
            uv run --extra benchmarks python -m benchmarks.decision_ids.run_bench \
                --output "$RESULTS_DIR/decision-ids.json"
        fi
    fi

    if [ "$RUN_ABLATION" = "1" ]; then
        run_ablation_sweep
    fi

    write_manifest
    print_summary
    # Full runs only: partial runs are not comparable to the published n.
    if [ "$RUN_BENCHMARKS" = "1" ] && [ -z "$LIMIT" ] && [ "$QUICK" = "0" ]; then
        check_floors
    fi

    # No-regression gate (blocking): run the same suite on BASELINE_REF in
    # this same container, then fail only if HEAD is worse than that
    # baseline by more than REGRESSION_TOLERANCE. See --no-regression above
    # and benchmarks/lib/bench_regression.sh's header for why this replaces
    # the (now non-blocking) floor check as the thing a PR must pass.
    if [ "$NO_REGRESSION" = "1" ]; then
        if [ "$RUN_BENCHMARKS" != "1" ] || [ -n "$LIMIT" ] || [ "$QUICK" = "1" ]; then
            echo "error: --no-regression requires a full benchmark run (no --ablation-only, --quick or --limit)." >&2
            exit 1
        fi
        run_baseline_benchmarks
        check_regression
    fi

    echo
    echo "==> All artifacts under: $RESULTS_DIR"
    if [ "$RUN_ABLATION" = "1" ]; then
        echo "==> Ablation artifacts under: benchmarks/results/ablation/$(ablation_bench_id "$ABLATE_ON")/"
    fi
}

main "$@"
