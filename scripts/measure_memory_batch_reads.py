"""Count real W4-3 function SQL calls using fixture stores, without DB/ML imports.

--before points to the repository (or file snapshot) immediately before W4-3,
including its W3-1a/W3-2 prerequisites. --after defaults to this repository.
This is a call-count experiment for the changed stages, not the recall floors.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests_py._memory_read_fakes import (  # noqa: E402 — enable execution from any cwd
    Engine,
    SqlSpy,
    final_stage,
    gate_functions,
    rows_fixture,
    source_functions,
    stage_retriever,
)


def load_stage(root, path, names, scope):
    filename = root / path
    defined = {
        n.name
        for n in ast.walk(ast.parse(filename.read_text()))
        if isinstance(n, ast.FunctionDef)
    }
    return source_functions(
        filename, [name for name in names if name in defined], scope
    )


def result_record(store, output):
    encoded = json.dumps(
        output, sort_keys=True, default=lambda value: value.hex()
    ).encode()
    return {
        "execute_count": store._execute.call_count,
        "output_sha256": hashlib.sha256(encoded).hexdigest(),
        "statements": [call.args[0] for call in store._execute.call_args_list],
    }


def measure_gate(root):
    store, engine = SqlSpy(rows_fixture()), Engine()
    scope = gate_functions().evaluate_observed_gate.__globals__
    functions = load_stage(
        root,
        "mcp_server/handlers/remember_helpers.py",
        [
            "compute_similarities",
            "_similarities_with_rows",
            "compute_template_normalized_similarities",
            "evaluate_observed_gate",
        ],
        scope,
    )
    request = SimpleNamespace(store=store, content="# Tool: Read\n**Read:** `/new.py`")
    output = functions.evaluate_observed_gate(request, object(), b"raw", engine)
    result = result_record(store, output)
    result["normalized_batches"] = engine.encode_batch.call_count
    return result


def measure_titans(root):
    store = SqlSpy(rows_fixture(10))
    apply, ctx, titans = final_stage(store)
    functions = load_stage(
        root,
        "mcp_server/core/pg_recall_stages.py",
        ["apply_final_stages"],
        apply.__globals__,
    )
    functions.apply_final_stages([{"memory_id": mid} for mid in store.rows], ctx)
    return result_record(store, titans.update.call_args.args[1])


def measure_assembly(root):
    store = SqlSpy(rows_fixture(10))
    candidates = [{"memory_id": mid, "score": 1.0} for mid in store.rows]
    detector = SimpleNamespace(stage_of=lambda row: row["plan_id"])
    retrieve = stage_retriever(store, candidates, detector)
    functions = load_stage(
        root,
        "mcp_server/core/pg_recall_assembly.py",
        ["_retrieve_fn"],
        retrieve.__globals__,
    )
    return result_record(store, functions._retrieve_fn("q", "current", 10))


def source_hashes(root):
    paths = [
        "mcp_server/handlers/remember_helpers.py",
        "mcp_server/core/pg_recall_stages.py",
        "mcp_server/core/pg_recall_assembly.py",
    ]
    return {
        path: hashlib.sha256((root / path).read_bytes()).hexdigest() for path in paths
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, default=ROOT)
    args = parser.parse_args()
    result = {"scope": "changed stages only; full recall/PG floors remain required"}
    for label, root in (("before", args.before), ("after", args.after)):
        result[label] = {
            "source_sha256": source_hashes(root),
            "gate": measure_gate(root),
            "titans": measure_titans(root),
            "assembly_rows": measure_assembly(root),
        }
    result["identical"] = all(
        result["before"][key]["output_sha256"] == result["after"][key]["output_sha256"]
        for key in ("gate", "titans", "assembly_rows")
    )
    print(json.dumps(result, indent=2))
    return 0 if result["identical"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
