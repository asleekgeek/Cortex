"""Small fixtures for the plan harness; never connect to Docker or PostgreSQL."""

from __future__ import annotations

import json
from argparse import Namespace
from unittest.mock import patch

import pytest

from benchmarks.pg_recall_plans.evidence import (
    compare_rows,
    parse_plans,
    summarize_group,
)
from benchmarks.pg_recall_plans.fixture import (
    DIMENSIONS,
    MIN_ROWS,
    load_sql,
    vector_sql,
)
from benchmarks.pg_recall_plans.run import arguments, main, validate_container
from benchmarks.pg_recall_plans.sql import experiment_sql, phase_sql


def test_fixture_is_deterministic_and_purges_before_loading():
    script = load_sql(MIN_ROWS)
    assert script == load_sql(MIN_ROWS)
    assert script.index("DELETE FROM memories WHERE is_benchmark") < script.index(
        "INSERT INTO memories"
    )
    assert f"generate_series(1, {MIN_ROWS})" in script
    assert script.index("ANALYZE memories") > script.index("generate_series")
    assert str(DIMENSIONS - 2) in vector_sql()


def test_before_then_partial_indexes_then_after_share_one_clock():
    script = experiment_sql(MIN_ROWS)
    before = script.index("'before-normal-global-r1'")
    index = script.index("CREATE INDEX IF NOT EXISTS idx_memories_curated_heat_base")
    after = script.index("'after-normal-global-r1'")
    assert before < index < after
    assert script.startswith("BEGIN;") and script.endswith("COMMIT;")
    assert "auto_explain.log_nested_statements = on" in script
    assert "SET hnsw." not in script
    assert "enable_indexscan = off" in phase_sql("after")


@pytest.mark.parametrize(
    "args",
    [
        [],
        ["--container", "prod", "--container-id", "id", "--output", "x"],
        [
            "--container",
            "cortex-bench-pg-1-ab",
            "--container-id",
            "id",
            "--output",
            "x",
            "--rows",
            "3",
        ],
    ],
)
def test_cli_rejects_missing_or_unsafe_options_before_docker(args):
    with patch("sys.argv", ["run", *args]), pytest.raises(SystemExit):
        arguments()


def test_container_must_match_reproduce_image_and_identity():
    info = [
        {
            "Config": {"Image": "not-the-reproduce-image", "Env": []},
            "State": {"Running": True},
        }
    ]
    with patch("benchmarks.pg_recall_plans.run.command") as execute:
        execute.return_value.stdout = json.dumps(info)
        with pytest.raises(RuntimeError, match="different image"):
            validate_container("cortex-bench-pg-1-ab", "fixture-id")


def test_container_id_must_match_chosen_run():
    info = [
        {
            "Id": "actual-id",
            "Config": {
                "Image": "pgvector/pgvector:pg16",
                "Env": ["POSTGRES_DB=cortex_bench"],
            },
            "State": {"Running": True},
        }
    ]
    with patch("benchmarks.pg_recall_plans.run.command") as execute:
        execute.return_value.stdout = json.dumps(info)
        with pytest.raises(RuntimeError, match="ID does not match"):
            validate_container("cortex-bench-pg-1-ab", "different-id")


def test_failure_drops_only_the_new_database_by_immutable_container_id(tmp_path):
    args = Namespace(
        container="cortex-bench-pg-1-ab",
        container_id="chosen-id",
        rows=MIN_ROWS,
        output=tmp_path / "result",
    )
    with (
        patch("benchmarks.pg_recall_plans.run.arguments", return_value=args),
        patch("benchmarks.pg_recall_plans.run.validate_container", return_value={}),
        patch("benchmarks.pg_recall_plans.run.host_evidence", return_value={}),
        patch("benchmarks.pg_recall_plans.run.command") as execute,
        patch(
            "benchmarks.pg_recall_plans.run.run_experiment",
            side_effect=RuntimeError("fixture"),
        ),
    ):
        with pytest.raises(RuntimeError, match="fixture"):
            main()
    create, drop = [call.args[0] for call in execute.call_args_list]
    assert create[2] == drop[2] == "chosen-id"
    assert create[3] == "createdb" and drop[3] == "dropdb"
    assert create[-1] == drop[-1] and create[-1].startswith("cortex_w4_")
    assert (args.output / "manifest.json").is_file()


def test_nested_bitmap_index_evidence_and_outer_buffer_accounting():
    nested = {
        "Query Text": "WITH eligible AS NOT MATERIALIZED ...",
        "Plan": {
            "Node Type": "Bitmap Heap Scan",
            "Plans": [
                {
                    "Node Type": "Bitmap Index Scan",
                    "Index Name": "idx_memories_content_trgm",
                }
            ],
        },
    }
    outer = {
        "Query Text": "SELECT json_build_object('case', 'after-normal-global')",
        "Plan": {
            "Actual Total Time": 42,
            "Shared Hit Blocks": 80,
            "Shared Read Blocks": 2,
        },
    }
    raw = "\n".join(
        "NOTICE: duration: 42 ms plan:\n" + json.dumps(p) for p in [nested, outer]
    )
    groups = parse_plans(raw)
    summary = summarize_group(groups["after-normal-global"])
    assert summary["indexes"] == ["idx_memories_content_trgm"]
    assert summary["shared_hits_plus_reads"] == 82
    assert not summary["index_requirement_pass"]


def test_missing_nested_plan_is_not_reported_as_a_pass():
    with pytest.raises(ValueError, match="no labelled"):
        parse_plans("ordinary psql output")


def test_exact_comparison_preserves_provenance_and_nan_semantics():
    before = [
        {"memory_id": 1, "score": float("nan"), "capture_origin": "user_explicit"}
    ]
    after = [{"memory_id": 1, "score": float("nan"), "capture_origin": "user_explicit"}]
    assert compare_rows(before, after)["rows_equal"]
    after[0]["capture_origin"] = "tool_output"
    assert not compare_rows(before, after)["rows_equal"]
