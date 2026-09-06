"""Light W3-5 wiring/isolation tests; real reloptions checks are generated SQL."""

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import Mock

from mcp_server.infrastructure.pg_schema import (
    MEMORIES_STORAGE_OPTIONS_DDL,
    get_all_ddl,
)
from scripts.pg_storage_calibration import (
    MIN_ROWS,
    REPETITIONS,
    generate,
    migration_check,
    main,
    validate,
)


class MemoriesStoragePolicy(unittest.TestCase):
    def test_migration_is_dispatched_after_table_creation(self):
        statements = get_all_ddl()
        policy = MEMORIES_STORAGE_OPTIONS_DDL.strip()
        create = next(
            i
            for i, sql in enumerate(statements)
            if "CREATE TABLE IF NOT EXISTS memories" in sql
        )
        self.assertEqual(statements.count(policy), 1)
        self.assertGreater(statements.index(policy), create)
        cursor = Mock()
        for statement in statements:
            cursor.execute(statement)
        cursor.execute.assert_any_call(policy)

    def test_policy_changes_only_the_plan_vacuum_factor(self):
        sql = MEMORIES_STORAGE_OPTIONS_DDL.lower()
        self.assertIn("autovacuum_vacuum_scale_factor = 0.05", sql)
        self.assertNotIn("fillfactor", sql)
        self.assertNotIn("index", sql)
        self.assertNotIn("vacuum full", sql)

    def test_live_check_uses_exact_migration_twice_and_preserves_other_option(self):
        sql = migration_check("w3_5_test")
        self.assertEqual(sql.count(MEMORIES_STORAGE_OPTIONS_DDL.strip()), 2)
        self.assertIn("pg_class", sql)
        self.assertIn("IS DISTINCT FROM", sql)
        self.assertIn("fillfactor=100", sql)


class StorageCalibrationIsolation(unittest.TestCase):
    def test_migration_only_cli_needs_no_corpus_or_vacuum(self):
        from unittest.mock import patch

        argv = [
            "audit",
            "--schema",
            "w3_5_test",
            "--fillfactors",
            "100",
            "--passes",
            "1",
            "--migration-only",
        ]
        output = io.StringIO()
        with patch("sys.argv", argv), redirect_stdout(output):
            main()
        sql = output.getvalue()
        self.assertIn("IS DISTINCT FROM", sql)
        self.assertNotIn("public.memories", sql)
        self.assertNotIn("VACUUM (", sql)

    def test_guard_precedes_mutations_and_all_workloads_use_clones(self):
        sql = generate("w3_5_test", [100], MIN_ROWS, 1)
        self.assertLess(sql.index("current_database()"), sql.index("CREATE SCHEMA"))
        self.assertIn("current_database() <> 'cortex_w3_5_calibration'", sql)
        self.assertNotIn("UPDATE public.memories", sql)
        self.assertNotIn("VACUUM (VERBOSE, ANALYZE) public.memories", sql)
        self.assertNotIn("DROP ", sql)
        self.assertNotIn("VACUUM FULL", sql)
        self.assertNotIn("# noqa", sql)
        self.assertEqual(
            sql.count("LIKE public.memories INCLUDING ALL"), 2 * REPETITIONS
        )

    def test_trials_set_fillfactor_before_load_and_read_transaction_stats(self):
        sql = generate("w3_5_test", [100], MIN_ROWS, 1)
        self.assertLess(
            sql.index("WITH (fillfactor=100"), sql.index("INSERT INTO w3_5_test.ff")
        )
        self.assertIn("attgenerated=''", sql)
        self.assertIn("OVERRIDING SYSTEM VALUE", sql)
        self.assertIn("pg_stat_xact_user_tables", sql)
        self.assertIn("replay_count has an index dependency", sql)
        self.assertIn("heat_base B-tree control index is missing", sql)
        self.assertIn("pg_total_relation_size", sql)
        self.assertIn("VACUUM (VERBOSE, ANALYZE) w3_5_test.ff100_eligible_r0", sql)

    def test_schema_names_cannot_escape_isolation(self):
        for schema in (
            "public",
            "w3_5_x; DROP DATABASE cortex",
            "w3_5_é",
            "w3_5_" + "x" * 63,
        ):
            with self.assertRaises(ValueError):
                validate(schema, [100], MIN_ROWS, 1)

    def test_no_default_candidate_or_out_of_range_parameters(self):
        for factors in ([], [99], [9, 100], [100, 101], [True, 100]):
            with self.assertRaises(ValueError):
                validate("w3_5_test", factors, MIN_ROWS, 1)
        with self.assertRaises(ValueError):
            validate("w3_5_test", [100], MIN_ROWS - 1, 1)
        with self.assertRaises(ValueError):
            validate("w3_5_test", [100], MIN_ROWS, 0)


if __name__ == "__main__":
    unittest.main()
