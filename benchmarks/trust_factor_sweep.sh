#!/usr/bin/env bash
# source: ADR-0871
# source: ADR-0871
#
#
#
# source: ADR-0871
#
#
# source: ADR-0871
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
# source: ADR-0871
#
#
#
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT" || exit 1

# source: ADR-0871
#
GRID=(1.0 0.8 0.7 0.6 0.5)

# source: ADR-0871
#
#
QUICK_FLAG=""
[[ "${1:-}" == "--quick" ]] && QUICK_FLAG="--quick"

# source: ADR-0871
#
OUT_ROOT="benchmarks/results/trust-factor-sweep/active"
mkdir -p "$OUT_ROOT"
LOG="${OUT_ROOT}/sweep.log"

snapshot_json() {
    uv run python -c "
import json, sys
sys.path.insert(0, 'benchmarks/lib')
from machine_load_snapshot import machine_load_snapshot
from disk_space_snapshot import disk_space_snapshot
print(json.dumps({'machine_load': machine_load_snapshot(), 'disk_space': disk_space_snapshot()}))
"
}

next_pending_w() {
    uv run python -c "
import sys
sys.path.insert(0, 'benchmarks/lib')
from sweep_progress import next_pending_w
w = next_pending_w([1.0, 0.8, 0.7, 0.6, 0.5], '${OUT_ROOT}')
print('' if w is None else w)
"
}

W="$(next_pending_w)"
if [[ -z "$W" ]]; then
    echo "GRID COMPLETE — every cell in ${GRID[*]} has a status:complete entry in ${OUT_ROOT}/PROGRESS.json." | tee -a "$LOG"
    echo "NEXT: apply the decision rule and record the chosen W in docs/provenance/trust-factor-calibration.md." | tee -a "$LOG"
    exit 0
fi

CELL_DIR="${OUT_ROOT}/cell_W${W}"
mkdir -p "$CELL_DIR"
echo "" | tee -a "$LOG"
echo "=== cell W=${W} — started $(date -u +%H:%M:%SZ) ===" | tee -a "$LOG"

START_SNAPSHOT="$(snapshot_json)"

# source: ADR-0871
#
CORTEX_UNTRUSTED_ORIGIN_FACTOR="$W" \
    benchmarks/reproduce.sh \
    --only longmemeval,locomo,beam \
    --no-ablation \
    $QUICK_FLAG \
    >"${CELL_DIR}/reproduce.log" 2>&1
rc=$?

END_SNAPSHOT="$(snapshot_json)"

if [[ $rc -eq 0 ]]; then
    echo "cell W=${W}: OK" | tee -a "$LOG"
    STATUS="complete"
else
    echo "cell W=${W}: FAILED rc=${rc} (see ${CELL_DIR}/reproduce.log)" | tee -a "$LOG"
    STATUS="failed"
fi

# source: ADR-0871
#
#
latest_repro="$(ls -td benchmarks/results/repro/*/ 2>/dev/null | head -1)"
echo "${latest_repro}" > "${CELL_DIR}/repro_dir.txt"
echo "cell W=${W} results: ${latest_repro}" | tee -a "$LOG"

uv run python -c "
import json, sys
sys.path.insert(0, 'benchmarks/lib')
from sweep_progress import record_cell_result

start = json.loads('''${START_SNAPSHOT}''')
end = json.loads('''${END_SNAPSHOT}''')
record_cell_result(
    '${OUT_ROOT}',
    ${W},
    status='${STATUS}',
    repro_dir='${latest_repro}' or None,
    snapshots={
        'machine_load_at_start': start['machine_load'],
        'disk_space_at_start': start['disk_space'],
        'machine_load_at_end': end['machine_load'],
        'disk_space_at_end': end['disk_space'],
    },
)
"

echo "" | tee -a "$LOG"
echo "cell W=${W} recorded to ${OUT_ROOT}/PROGRESS.json — control returned." | tee -a "$LOG"
remaining="$(next_pending_w)"
if [[ -n "$remaining" ]]; then
    echo "NEXT PENDING CELL: W=${remaining}. Re-run this script to continue." | tee -a "$LOG"
else
    echo "GRID COMPLETE — every cell has reported." | tee -a "$LOG"
fi
