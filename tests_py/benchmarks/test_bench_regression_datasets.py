"""Run the actual baseline shell against a tiny repo and a fake model runner."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess

import pytest

LIBRARY = Path(__file__).resolve().parents[2] / "benchmarks/lib/bench_regression.sh"
DATASETS = {
    "longmemeval": "longmemeval_s.json",
    "locomo": "locomo10.json",
}


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def _repository(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "fixture@example.invalid")
    _git(repo, "config", "user.name", "Fixture")
    (repo / ".gitignore").write_text("*.json\n.claude/\nresults/\n")
    for name in DATASETS:
        directory = repo / "benchmarks" / name
        directory.mkdir(parents=True)
        (directory / "run_benchmark.py").write_text("# Fake runner reads no code.\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "baseline")
    _git(repo, "branch", "baseline")
    (repo / "candidate.txt").write_text("candidate\n")
    _git(repo, "add", "candidate.txt")
    _git(repo, "commit", "-qm", "candidate")
    return repo


def _runner(tmp_path: Path) -> Path:
    binary = tmp_path / "bin"
    binary.mkdir()
    uv = binary / "uv"
    uv.write_text("""#!/bin/sh
set -eu
for argument do
    case "$argument" in
        */run_benchmark.py) script="$argument" ;;
    esac
done
directory="${script%/*}"
name="${directory##*/}"
case "$name" in
    longmemeval) filename=longmemeval_s.json ;;
    locomo) filename=locomo10.json ;;
esac
cmp "$directory/$filename" "$REPO_ROOT/benchmarks/$name/$filename"
printf '%s\\n' "$name" >> "$RUNNER_LOG"
if [ "$FAIL_RUNNER" = 1 ]; then exit 17; fi
""")
    uv.chmod(0o755)
    return binary


def _run(tmp_path: Path, selected: str, *, missing=False, fail=False):
    repo = _repository(tmp_path)
    for name, filename in DATASETS.items():
        if name in selected.split(",") and not missing:
            (repo / "benchmarks" / name / filename).write_bytes(
                b'["exact", "\xc3\xa9"]\n'
            )
    binary = _runner(tmp_path)
    environment = dict(
        os.environ,
        PATH=str(binary) + os.pathsep + os.environ["PATH"],
        REPO_ROOT=str(repo),
        RESULTS_DIR=str(repo / "results"),
        BASELINE_REF="baseline",
        ONLY=selected,
        QUICK="0",
        LIMIT="",
        BENCH_DB_URL="unused-fixture",
        RUNNER_LOG=str(tmp_path / "calls"),
        FAIL_RUNNER="1" if fail else "0",
        LIBRARY=str(LIBRARY),
    )
    result = subprocess.run(
        [
            "bash",
            "-c",
            """set -euo pipefail
source "$LIBRARY"
PASSTHROUGH=()
want_bench() { case ",$ONLY," in *",$1,"*) return 0;; *) return 1;; esac; }
run_baseline_benchmarks
""",
        ],
        env=environment,
        capture_output=True,
        text=True,
    )
    return result, repo, tmp_path / "calls"


@pytest.mark.parametrize("selected", ["longmemeval", "locomo", "longmemeval,locomo"])
def test_baseline_uses_exact_selected_ignored_inputs(tmp_path, selected):
    result, repo, calls = _run(tmp_path, selected)
    assert result.returncode == 0, result.stderr
    assert calls.read_text().splitlines() == selected.split(",")
    assert _git(repo, "worktree", "list", "--porcelain").count("worktree ") == 1


def test_missing_dataset_fails_before_runner_and_cleans_worktree(tmp_path):
    result, repo, calls = _run(tmp_path, "longmemeval", missing=True)
    assert result.returncode != 0
    assert "dataset missing or unreadable" in result.stderr
    assert not calls.exists()
    assert _git(repo, "worktree", "list", "--porcelain").count("worktree ") == 1


def test_first_runner_failure_is_preserved_and_cleans_worktree(tmp_path):
    result, repo, calls = _run(tmp_path, "longmemeval,locomo", fail=True)
    assert result.returncode == 17
    assert calls.read_text().splitlines() == ["longmemeval"]
    assert _git(repo, "worktree", "list", "--porcelain").count("worktree ") == 1
