"""W4-3 gate comparisons: complete rows reused across all three vector signals."""

from __future__ import annotations

import copy
import unittest
from types import SimpleNamespace

from mcp_server.core.capture_template_normalize import capture_template_normalize
from tests_py._memory_read_fakes import (
    Engine,
    SqlSpy,
    gate_functions,
    old_gate_signals,
    rows_fixture,
)


class NeighborReadTests(unittest.TestCase):
    def compare(self, rows, hits=None, content=None):
        content = content or "# Tool: Read\n**Read:** `/new.py`"
        old_store, new_store = SqlSpy(rows, hits), SqlSpy(rows, hits)
        old_engine, new_engine = Engine(), Engine()
        expected = old_gate_signals(
            SimpleNamespace(store=old_store, content=content), old_engine
        )
        request = SimpleNamespace(store=new_store, content=content)
        actual = gate_functions().evaluate_observed_gate(
            request, object(), b"raw", new_engine
        )
        self.assertEqual(actual, expected)
        self.assertEqual(
            new_engine.encode_batch.call_args_list,
            old_engine.encode_batch.call_args_list,
        )
        self.assertEqual(
            new_engine.similarity.call_args_list, old_engine.similarity.call_args_list
        )
        return old_store, new_store, new_engine, actual

    def test_five_neighbors_drop_twelve_statements_to_two(self):
        old, new, engine, _result = self.compare(rows_fixture())
        self.assertEqual((old._execute.call_count, new._execute.call_count), (12, 2))
        self.assertEqual(len(engine.encode_batch.call_args.args[0]), 6)
        self.assertIn("WHERE id = ANY", new._execute.call_args_list[1].args[0])

    def test_duplicates_missing_ids_null_vectors_and_empty_content(self):
        rows = rows_fixture()
        rows[1]["content"] = ""
        rows[2]["embedding"] = None
        rows[3]["content"] = None
        rows[4]["embedding"] = b""
        hits = [
            (3, 0.0),
            (99, 0.0),
            (None, 0.0),
            (2, 0.0),
            (1, 0.0),
            (5, 0.0),
            (5, 0.0),
            (4, 0.0),
        ]
        _old, new, engine, result = self.compare(rows, hits)
        self.assertEqual(new._execute.call_count, 2)
        self.assertEqual(result["vec_hits"], hits)
        texts = engine.encode_batch.call_args.args[0]
        self.assertEqual(texts.count(capture_template_normalize(rows[5]["content"])), 2)

    def test_complete_normalized_content_is_used_and_source_rows_do_not_mutate(self):
        rows = rows_fixture()
        rows[5]["content"] += "\n" + "long detail " * 2000 + " unique suffix"
        original = copy.deepcopy(rows)
        _old, new, engine, _result = self.compare(rows)
        self.assertEqual(new.rows, original)
        self.assertTrue(
            engine.encode_batch.call_args.args[0][-1].endswith("unique suffix")
        )
        # Normalized vectors are separately encoded, never old stored vectors.
        self.assertTrue(
            any(
                call.args[0].startswith(b"normalized:")
                for call in engine.similarity.call_args_list
            )
        )

    def test_non_template_keeps_raw_scoring_without_normalized_encode(self):
        old, new, engine, _result = self.compare(
            rows_fixture(), content="A deliberate fact"
        )
        self.assertEqual((old._execute.call_count, new._execute.call_count), (7, 2))
        engine.encode_batch.assert_not_called()

    def test_missing_raw_embedding_does_not_read_and_retains_normalized_input(self):
        store, engine = SqlSpy(rows_fixture()), Engine()
        request = SimpleNamespace(
            store=store, content="# Tool: Read\n**Read:** `/new.py`"
        )
        result = gate_functions().evaluate_observed_gate(
            request, object(), None, engine
        )
        store._execute.assert_not_called()
        self.assertEqual(result["sims"], [])
        engine.encode_batch.assert_called_once_with(
            [capture_template_normalize(request.content)]
        )

    def test_empty_vector_search_does_not_issue_a_row_query(self):
        store, engine = SqlSpy({}), Engine()
        sims, hits = gate_functions().compute_similarities(b"raw", store, engine)
        self.assertEqual((sims, hits), ([], []))
        self.assertEqual(store._execute.call_count, 1)
        engine.similarity.assert_not_called()

    def test_normalized_none_and_missing_neighbor_vectors_preserve_decisions(self):
        for vectors in (
            [None] * 6,
            [b"input", None, b"neighbor", None, b"other", None],
        ):
            with self.subTest(vectors=vectors):
                old_engine, new_engine = Engine(), Engine()
                old_engine.encode_batch.side_effect = (
                    new_engine.encode_batch.side_effect
                ) = None
                old_engine.encode_batch.return_value = (
                    new_engine.encode_batch.return_value
                ) = vectors
                content = "# Tool: Read\n**Read:** `/new.py`"
                expected = old_gate_signals(
                    SimpleNamespace(store=SqlSpy(rows_fixture()), content=content),
                    old_engine,
                )
                request = SimpleNamespace(store=SqlSpy(rows_fixture()), content=content)
                actual = gate_functions().evaluate_observed_gate(
                    request, object(), b"raw", new_engine
                )
                self.assertEqual(actual, expected)

    def test_store_and_encoder_errors_propagate_without_retry(self):
        for target in ("store", "similarity", "encode_batch"):
            with self.subTest(target=target):
                store, engine = SqlSpy(rows_fixture()), Engine()
                request = SimpleNamespace(
                    store=store, content="# Tool: Read\n**Read:** `/new.py`"
                )
                if target == "store":
                    store._execute.side_effect = OSError("failed")
                else:
                    getattr(engine, target).side_effect = ValueError("failed")
                with self.assertRaisesRegex((OSError, ValueError), "failed"):
                    gate_functions().evaluate_observed_gate(
                        request, object(), b"raw", engine
                    )
                self.assertLessEqual(store._execute.call_count, 2)

    def test_public_similarity_pair_and_no_legacy_store_fallback(self):
        engine, store = Engine(), SqlSpy(rows_fixture())
        result = gate_functions().compute_similarities(b"raw", store, engine)
        self.assertEqual(len(result), 2)
        old_store = SimpleNamespace(
            search_vectors=store.search_vectors, get_memory=store.get_memory
        )
        with self.assertRaises(AttributeError):
            gate_functions().compute_similarities(b"raw", old_store, engine)


if __name__ == "__main__":
    unittest.main()
