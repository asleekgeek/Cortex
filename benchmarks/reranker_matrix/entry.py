"""Run a benchmark or manifest script under an explicit reranker matrix cell.

source: ADR-0861
"""

from __future__ import annotations

import json
from pathlib import Path
import runpy
import sys

from benchmarks.reranker_matrix.pins import cell
from benchmarks.reranker_matrix.runtime import selected_cell

# source: ADR-0861
SCRIPTS = {
    "benchmarks/longmemeval/run_benchmark.py",
    "benchmarks/locomo/run_benchmark.py",
    "benchmarks/beam/run_benchmark.py",
    "benchmarks/lib/write_manifest.py",
}


def resolve_script(name: str) -> Path:
    root = Path(__file__).resolve().parents[2]
    script = Path(name).resolve()
    if (
        not script.is_relative_to(root)
        or script.relative_to(root).as_posix() not in SCRIPTS
    ):
        raise ValueError(
            "matrix entry accepts only reproduce.sh benchmark/manifest scripts"
        )
    return script


def evidence_path(script: Path, args: list[str]) -> Path:
    if script.name == "write_manifest.py":
        return Path(args[0]) / "reranker-cell.json"
    if "--results-out" not in args:
        raise ValueError("matrix benchmark requires explicit --results-out")
    result = Path(args[args.index("--results-out") + 1])
    return result.with_suffix(".reranker-cell.json")


def main() -> None:
    config = cell(sys.argv[1])
    script = resolve_script(sys.argv[2])
    args = sys.argv[3:]
    out = evidence_path(script, args)
    with selected_cell(config) as evidence:
        previous = sys.argv
        sys.argv = [str(script), *args]
        try:
            runpy.run_path(str(script), run_name="__main__")
        finally:
            sys.argv = previous
            out.write_text(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
