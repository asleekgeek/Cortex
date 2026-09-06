"""Protocol/parser fixtures only: no PostgreSQL, Docker, model or timing claims."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory
import unittest

from benchmarks.pg_recall_plans.evidence import REQUIRED_INDEXES, write_summary
from benchmarks.pg_recall_plans.sql import case_labels, experiment_sql


def fixture_artifacts() -> tuple[list[dict], list[dict]]:
    """Deliberately slow first samples demonstrate exclusion, not measured speed."""
    plans = []
    records = [
        {"experiment": {"fixture_rows": 30_000, "snapshot_now": "fixture-clock"}}
    ]
    latencies = [900, 30, 10, 20]
    for label in case_labels("before") + case_labels("after"):
        latency = latencies[int(label[-1]) - 1]
        plans.append(
            {
                "Query Text": f"SELECT json_build_object('case', '{label}')",
                "Plan": {
                    "Actual Total Time": latency,
                    "Shared Hit Blocks": latency * 10,
                    "Shared Read Blocks": 0,
                    "Temp Read Blocks": latency,
                    "Temp Written Blocks": latency * 2,
                    "Plans": [
                        {"Index Name": name} for name in sorted(REQUIRED_INDEXES)
                    ],
                },
            }
        )
        records.append(
            {
                "case": label,
                "rows": [
                    {"memory_id": 1, "score": 1.0, "capture_origin": "user_explicit"},
                    {"memory_id": 2, "score": 0.5, "capture_origin": "tool_output"},
                ],
            }
        )
    return plans, records


class RepetitionEvidenceTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory(prefix="cortex_pg_plan_fixture_")
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.plans, self.records = fixture_artifacts()

    def summarize(self):
        self.directory.joinpath("nested-plans.log").write_text(
            "\n".join(
                "NOTICE: duration: fixture plan:\n" + json.dumps(plan)
                for plan in self.plans
            )
        )
        self.directory.joinpath("results.jsonl").write_text(
            "\n".join(json.dumps(record) for record in self.records)
        )
        passed = write_summary(self.directory)
        return passed, json.loads(self.directory.joinpath("summary.json").read_text())

    def record(self, label):
        return next(record for record in self.records if record.get("case") == label)

    def plan(self, label):
        return next(
            plan["Plan"] for plan in self.plans if f"'{label}'" in plan["Query Text"]
        )

    def test_four_complete_passes_share_fixture_transaction_and_clock(self):
        script = experiment_sql(30_000)
        labels = re.findall(r"'case', '([^']+)'", script)
        self.assertEqual(labels, case_labels("before") + case_labels("after"))
        self.assertEqual(len(labels), 32)
        self.assertEqual(
            labels[:4],
            [
                "before-normal-global-r1",
                "before-normal-scoped-r1",
                "before-normal-global-r2",
                "before-normal-scoped-r2",
            ],
        )
        for case in {label.rpartition("-r")[0] for label in labels}:
            self.assertEqual(
                [f"{case}-r{i}" for i in (1, 2, 3, 4)],
                [label for label in labels if label.startswith(case + "-r")],
            )
        self.assertTrue(script.startswith("BEGIN;") and script.endswith("COMMIT;"))
        self.assertEqual(script.count("FROM generate_series(1, 30000)"), 1)
        self.assertEqual(script.count("'snapshot_now', NOW()"), 1)
        index = script.index(
            "CREATE INDEX IF NOT EXISTS idx_memories_curated_heat_base"
        )
        self.assertLess(script.index("'before-exact-scoped-r4'"), index)
        self.assertLess(index, script.index("'after-normal-global-r1'"))

    def test_first_discarded_only_from_performance_and_all_metrics_aggregated(self):
        passed, report = self.summarize()
        self.assertTrue(passed)
        self.assertFalse(report["plans"]["after-normal-global-r1"]["limits_pass"])
        aggregate = report["aggregates"]["after-normal-global"]
        self.assertEqual(aggregate["sample_count"], 3)
        self.assertEqual(
            aggregate["statistics"]["executor_ms"],
            {
                "median": 20,
                "min": 10,
                "max": 30,
            },
        )
        for metric, factor in (
            ("shared_hits_plus_reads", 10),
            ("temp_read", 1),
            ("temp_written", 2),
        ):
            self.assertEqual(
                aggregate["statistics"][metric],
                {
                    "median": 20 * factor,
                    "min": 10 * factor,
                    "max": 30 * factor,
                },
            )
        self.assertEqual(len(report["comparisons"]), 16)
        self.assertEqual(
            report["measurement"]["retained_performance_repetitions"], [2, 3, 4]
        )
        self.assertEqual(
            report["measurement"]["case_order"],
            case_labels("before") + case_labels("after"),
        )

    def test_every_exact_oracle_including_discarded_performance_pass_is_required(self):
        for repetition in (1, 2, 3, 4):
            with self.subTest(repetition=repetition):
                self.plans, self.records = fixture_artifacts()
                self.record(f"after-exact-global-r{repetition}")["rows"][0]["score"] = (
                    2.0
                )
                passed, report = self.summarize()
                self.assertFalse(passed)
                self.assertFalse(
                    report["comparisons"][f"exact-global-r{repetition}"]["rows_equal"]
                )

    def test_normal_ann_difference_is_reported_without_replacing_exact_oracle(self):
        self.record("after-normal-global-r2")["rows"].pop()
        passed, report = self.summarize()
        self.assertTrue(passed)
        self.assertFalse(report["comparisons"]["normal-global-r2"]["rows_equal"])

    def test_return_order_is_reported_separately_from_identical_rows(self):
        self.record("after-exact-global-r3")["rows"].reverse()
        passed, report = self.summarize()
        self.assertTrue(passed)
        self.assertFalse(report["comparisons"]["exact-global-r3"]["order_equal"])

    def test_retained_outlier_cannot_be_hidden_by_passing_median(self):
        self.plan("after-normal-global-r2")["Actual Total Time"] = 201
        passed, report = self.summarize()
        self.assertFalse(passed)
        stats = report["aggregates"]["after-normal-global"]["statistics"]["executor_ms"]
        self.assertEqual(stats, {"median": 20, "min": 10, "max": 201})

    def test_missing_index_on_one_retained_pass_fails(self):
        self.plan("after-normal-scoped-r4")["Plans"].pop()
        self.assertFalse(self.summarize()[0])

    def test_retained_buffer_outlier_fails_even_with_passing_median(self):
        self.plan("after-normal-global-r3")["Shared Read Blocks"] = 10_000
        passed, report = self.summarize()
        self.assertFalse(passed)
        stats = report["aggregates"]["after-normal-global"]["statistics"]
        self.assertEqual(
            stats["shared_hits_plus_reads"],
            {
                "median": 300,
                "min": 200,
                "max": 10_100,
            },
        )

    def test_incomplete_unexpected_duplicate_or_reordered_cases_are_rejected(self):
        original_plans, original_records = fixture_artifacts()
        for kind in (
            "missing_plan",
            "missing_rows",
            "unknown",
            "order",
            "duplicate_plan",
            "duplicate_rows",
        ):
            with self.subTest(kind=kind):
                self.plans = copy.deepcopy(original_plans)
                self.records = copy.deepcopy(original_records)
                self.damage_cases(kind)
                with self.assertRaisesRegex(ValueError, "cases|duplicate"):
                    self.summarize()

    def damage_cases(self, kind):
        match kind:
            case "missing_plan":
                self.plans.pop()
            case "missing_rows":
                self.records.pop()
            case "unknown":
                self.records[-1]["case"] = "after-exact-scoped-r5"
            case "order":
                self.records[-1], self.records[-2] = self.records[-2], self.records[-1]
            case "duplicate_plan":
                self.plans.append(self.plans[-1])
            case "duplicate_rows":
                self.records.append(self.records[-1])

    def test_observed_corpus_is_recorded_without_claiming_a_larger_envelope(self):
        passed, report = self.summarize()
        self.assertTrue(passed)
        self.assertEqual(report["measurement"]["fixture_rows"], 30_000)
        self.assertIn(
            "larger corpora are unmeasured", report["measurement"]["corpus_scope"]
        )

    def test_missing_duplicate_or_invalid_observed_context_is_rejected(self):
        for context in (
            None,
            {},
            {"fixture_rows": 29_999, "snapshot_now": "clock"},
            {"fixture_rows": True, "snapshot_now": "clock"},
            {"fixture_rows": 30_000, "snapshot_now": ""},
        ):
            with self.subTest(context=context):
                self.plans, self.records = fixture_artifacts()
                if context is None:
                    self.records.pop(0)
                else:
                    self.records[0]["experiment"] = context
                with self.assertRaises(ValueError):
                    self.summarize()
        self.plans, self.records = fixture_artifacts()
        self.records.append(self.records[0])
        with self.assertRaisesRegex(ValueError, "one observed"):
            self.summarize()


if __name__ == "__main__":
    unittest.main()
