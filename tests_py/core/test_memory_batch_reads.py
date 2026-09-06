"""W4-3: exact row shaping and recall order with stdlib SQL spies."""

from __future__ import annotations

import copy
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

from tests_py._memory_read_fakes import (
    SQLITE,
    SqlSpy,
    final_stage,
    old_stage_rows,
    old_titans_embeddings,
    rows_fixture,
    stage_retriever,
)


class BulkRows(unittest.TestCase):
    def test_postgres_complete_normalized_rows_equal_single_reads(self):
        rows = rows_fixture(3)
        rows[1]["content"] = "complete " * 2000 + "suffix"
        rows[1]["created_at"] = datetime(2026, 9, 6, tzinfo=timezone.utc)
        rows[2]["embedding"] = None
        store = SqlSpy(rows)
        ids = [3, 1, 3, 99, None, 2]
        expected = {mid: store.get_memory(mid) for mid in ids}
        store._execute.reset_mock()
        actual = store.get_memories_by_ids(ids)
        self.assertEqual(actual, {mid: row for mid, row in expected.items() if row})
        self.assertEqual(store._execute.call_count, 1)
        self.assertIn("WHERE id = ANY(%s::int[])", store._execute.call_args.args[0])
        self.assertEqual(store._execute.call_args.args[1], (ids,))
        self.assertIsInstance(actual[1]["embedding"], bytes)
        self.assertEqual(actual[1]["tags"], ["capture"])
        self.assertEqual(actual[1]["heat"], 0.5)

    def test_empty_ids_do_not_execute_either_backend(self):
        store = SqlSpy(rows_fixture())
        self.assertEqual(store.get_memories_by_ids([]), {})
        self.assertEqual(SQLITE.get_memories_by_ids(store, []), {})
        store._execute.assert_not_called()

    def test_sqlite_bulk_preserves_rows_without_adding_vec_embeddings(self):
        rows = rows_fixture(3)
        for row in rows.values():
            del row["embedding"]
        store = SqlSpy(rows)
        ids = [3, None, 1, 3, 99]
        actual = SQLITE.get_memories_by_ids(store, ids)
        self.assertEqual(set(actual), {1, 3})
        self.assertTrue(all("embedding" not in row for row in actual.values()))
        store._execute.assert_called_once_with(
            "SELECT * FROM memories WHERE id IN (?,?,?,?,?)", ids
        )

    def test_query_and_normalization_errors_propagate(self):
        for fetch in (SqlSpy.get_memories_by_ids, SQLITE.get_memories_by_ids):
            with self.subTest(fetch=fetch):
                store = SqlSpy(rows_fixture())
                store._execute.side_effect = OSError("store failed")
                with self.assertRaisesRegex(OSError, "store failed"):
                    fetch(store, [1])
                store = SqlSpy(rows_fixture())
                store._normalize_memory_row = Mock(
                    side_effect=ValueError("invalid vector")
                )
                with self.assertRaisesRegex(ValueError, "invalid vector"):
                    fetch(store, [1])


class RecallBatchReads(unittest.TestCase):
    def test_titans_ten_statements_become_one_with_identical_vector_order(self):
        rows = rows_fixture(10)
        rows[2]["embedding"], rows[3]["embedding"] = None, b""
        candidates = [
            {"memory_id": mid} for mid in [5, 1, 2, 5, 3, 99, None, 7, 9, 4, 10]
        ]
        old, new = SqlSpy(rows), SqlSpy(rows)
        expected = old_titans_embeddings(candidates, old)
        apply, ctx, titans = final_stage(new)
        self.assertIs(apply(candidates, ctx), candidates)
        titans.update.assert_called_once_with(b"query", expected)
        self.assertEqual(ctx.momentum_state, {"momentum": 0.25})
        self.assertEqual((old._execute.call_count, new._execute.call_count), (10, 1))

    def test_titans_sqlite_rows_remain_empty_and_empty_input_does_not_read(self):
        rows = rows_fixture()
        for row in rows.values():
            del row["embedding"]
        for candidates in ([], [{"memory_id": mid} for mid in rows]):
            store = SqlSpy(rows)
            apply, ctx, titans = final_stage(store)
            apply(candidates, ctx)
            titans.update.assert_called_once_with(b"query", [])
            self.assertEqual(store._execute.call_count, int(bool(candidates)))
        ctx.momentum_state = None
        store._execute.reset_mock()
        apply(candidates, ctx)
        store._execute.assert_not_called()

    def test_array_like_vectors_do_not_use_ambiguous_truth(self):
        class ArrayLike:
            def __bool__(self):
                raise ValueError("ambiguous ndarray truth")

            def __len__(self):
                return 2

        vector = ArrayLike()
        store = SimpleNamespace(
            get_memories_by_ids=lambda ids: {1: {"embedding": vector}}
        )
        apply, ctx, titans = final_stage(store)
        apply([{"memory_id": 1}], ctx)
        self.assertIs(titans.update.call_args.args[1][0], vector)

    def test_assembly_uses_full_content_and_custom_metadata_in_original_order(self):
        rows = rows_fixture(10)
        rows[4]["content"] = "z" * 12000 + " Needle"
        rows[4]["private_stage"] = {"selected": True}
        rows[3]["embedding"] = None
        ids = [8, 99, None, 3, 4, 4, 9, 2, 1, 5]
        candidates = [
            {"memory_id": mid, "content": "truncated", "score": n}
            for n, mid in enumerate(ids)
        ]
        detector = SimpleNamespace(
            stage_of=lambda row: (
                "current" if row.get("private_stage") or row["id"] != 8 else "other"
            )
        )
        original = copy.deepcopy((rows, candidates))
        old, new = SqlSpy(rows), SqlSpy(rows)
        expected = old_stage_rows(candidates, old, detector, 10)
        actual = stage_retriever(new, candidates, detector)("query", "current", 10)
        self.assertEqual(actual, expected)
        self.assertEqual((old._execute.call_count, new._execute.call_count), (10, 1))
        self.assertEqual(
            [row["entity_ids"] for row in actual if row["memory_id"] == 4],
            [["7"], ["7"]],
        )
        self.assertEqual((rows, candidates), original)

    def test_assembly_honors_limit_without_changing_candidates(self):
        rows = rows_fixture()
        candidates = [{"memory_id": mid} for mid in [4, 2, 4, 5]]
        detector = SimpleNamespace(stage_of=lambda row: row["plan_id"])
        old, new = SqlSpy(rows), SqlSpy(rows)
        expected = old_stage_rows(candidates, old, detector, 2)
        self.assertEqual(
            stage_retriever(new, candidates, detector)("q", "current", 2), expected
        )
        self.assertEqual([row["memory_id"] for row in expected], [4, 2])

    def test_read_errors_remain_visible_without_per_id_retry(self):
        store = SqlSpy(rows_fixture())
        store._execute.side_effect = OSError("batch failed")
        apply, ctx, _titans = final_stage(store)
        with self.assertRaisesRegex(OSError, "batch failed"):
            apply([{"memory_id": 1}], ctx)
        self.assertEqual(store._execute.call_count, 1)
        store._execute.reset_mock()
        retrieve = stage_retriever(store, [{"memory_id": 1}], Mock())
        with self.assertRaisesRegex(OSError, "batch failed"):
            retrieve("q", "current", 1)
        self.assertEqual(store._execute.call_count, 1)


if __name__ == "__main__":
    unittest.main()
