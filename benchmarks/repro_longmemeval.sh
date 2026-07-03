#!/usr/bin/env bash
# One-command reproduction of the LongMemEval retrieval benchmark.
#
#   make longmemeval          # full 500-question run
#   make longmemeval-smoke    # 10-question sanity run
#
# What it does:
#   1. Downloads the official LongMemEval-S dataset (sha256-pinned).
#   2. Starts an ephemeral PostgreSQL + pgvector container, isolated
#      from any existing Cortex install (separate port and database).
#   3. Runs benchmarks/longmemeval/run_benchmark.py through the SAME
#      PL/pgSQL recall path production uses (no benchmark-only retriever).
#   4. Prints the Recall@K / MRR table and tears the container down.
#
# Measured wall-clock for the full 500 questions: 39.6 min on Apple
# Silicon with CPU embeddings.
# source: benchmarks/results/a3_longmemeval_post_refactor.md (2026-04-17)
#
# Metric scope: session-level retrieval Recall@10 / MRR. This is NOT the
# end-to-end QA accuracy that LLM-answering leaderboards report. The
# comparable published baseline is the best retrieval configuration in
# the LongMemEval paper (Wu et al., ICLR 2025): Recall@10 78.4%.
#
# Environment overrides:
#   CORTEX_BENCH_PORT   host port for the ephemeral PG (default 55432)
#   KEEP_DB=1           keep the container running after the run
#
# Extra arguments are passed through to run_benchmark.py
# (e.g. --limit 10, --n-runs 3, --results-out path.json).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATASET_PATH="$REPO_ROOT/benchmarks/longmemeval/longmemeval_s.json"

# Official dataset location, per the LongMemEval authors' HF repository.
# source: https://huggingface.co/datasets/xiaowu0162/LongMemEval
DATASET_URL="https://huggingface.co/datasets/xiaowu0162/LongMemEval/resolve/main/longmemeval_s"
# source: measured 2026-07-03 against the HF copy (278,025,796 bytes),
# byte-identical to the file behind every published Cortex result.
DATASET_SHA256="08d8dad4be43ee2049a22ff5674eb86725d0ce5ff434cde2627e5e8e7e117894"

# pgvector's official image; any PostgreSQL >= 15 with the vector
# extension available works (mcp_server/infrastructure/pg_schema.py
# creates the extensions itself on first connect).
PG_IMAGE="pgvector/pgvector:pg16"
PG_PORT="${CORTEX_BENCH_PORT:-55432}"
CONTAINER="cortex-bench-pg"
BENCH_DB_URL="postgresql://postgres:cortex_bench@localhost:${PG_PORT}/cortex_bench"

started_container=0

need_cmd() {
    command -v "$1" >/dev/null 2>&1 || {
        echo "error: '$1' is required but not installed." >&2
        exit 1
    }
}

sha256_of() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    else
        shasum -a 256 "$1" | awk '{print $1}'
    fi
}

fetch_dataset() {
    if [ -f "$DATASET_PATH" ]; then
        echo "==> Dataset present: $DATASET_PATH"
    else
        echo "==> Downloading LongMemEval-S (~265 MB) from the official HF repo..."
        curl -L --fail --progress-bar -o "$DATASET_PATH" "$DATASET_URL"
    fi
    echo "==> Verifying dataset checksum..."
    local actual
    actual="$(sha256_of "$DATASET_PATH")"
    if [ "$actual" != "$DATASET_SHA256" ]; then
        echo "error: dataset checksum mismatch." >&2
        echo "  expected: $DATASET_SHA256" >&2
        echo "  actual:   $actual" >&2
        echo "The upstream file changed or the download is corrupt." >&2
        echo "Delete $DATASET_PATH and retry; open an issue if it persists." >&2
        exit 1
    fi
    echo "==> Checksum OK."
}

start_db() {
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
        echo "==> Reusing running container ${CONTAINER}."
        return
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
    until docker exec "$CONTAINER" pg_isready -U postgres -d cortex_bench \
        >/dev/null 2>&1; do
        sleep 1
    done
}

teardown() {
    if [ "$started_container" = "1" ] && [ "${KEEP_DB:-0}" != "1" ]; then
        echo "==> Removing ephemeral container ${CONTAINER} (KEEP_DB=1 to keep)."
        docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
    fi
}

main() {
    need_cmd docker
    need_cmd curl
    need_cmd uv
    if ! docker info >/dev/null 2>&1; then
        echo "error: the Docker daemon is not running." >&2
        echo "Start it (Docker Desktop, 'colima start', ...) and retry." >&2
        exit 1
    fi
    fetch_dataset
    start_db
    trap teardown EXIT
    echo "==> Running the benchmark through the production recall path..."
    echo "    (full 500-question run takes ~40 min; pass --limit N for less)"
    cd "$REPO_ROOT"
    DATABASE_URL="$BENCH_DB_URL" uv run --extra benchmarks python \
        benchmarks/longmemeval/run_benchmark.py "$@"
}

main "$@"
