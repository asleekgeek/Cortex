"""Compare normalized batching to the former scalar path using fixed vectors."""

from __future__ import annotations

import unittest
from unittest.mock import Mock

import numpy as np

from mcp_server.core.capture_template_normalize import capture_template_normalize
from mcp_server.handlers import remember_helpers as helpers
from tests_py.handlers._remember_batch_fakes import BatchStore, blob, make_engine


def scalar_reference(content, hits, store, engine):
    """Frozen pre-W3-2 scoring order, independent of the batch implementation."""
    incoming = engine.encode(capture_template_normalize(content))
    if not incoming:
        return None
    result = []
    for memory_id, _distance in hits:
        memory = store.get_memory(memory_id)
        if memory and memory.get("content"):
            neighbor = engine.encode(capture_template_normalize(memory["content"]))
            if neighbor:
                result.append(engine.similarity(incoming, neighbor))
    return result


class NormalizedBatch(unittest.TestCase):
    def setUp(self):
        self.content = "# Tool: Read\n**Read:** `/a.py`"
        texts = [
            self.content,
            "# Tool: Read\n**Read:** `/b.py`",
            "Foo and Bar are strongly linked (depends_on, weight=10.0)",
            "A deliberate fact",
            "# Tool: Bash\n**Command:** `pwd`",
        ]
        vectors = [(1, 2, 3), (3, 2, 1), (1, 0, 1), (0, 1, 0), (1, 1, 0)]
        self.vectors = dict(
            zip(map(capture_template_normalize, texts), vectors, strict=True)
        )
        self.rows = {
            mid: {"content": text, "embedding": blob((1, 0, 0))}
            for mid, text in enumerate(texts, 1)
        }
        self.store = BatchStore(self.content, self.rows)
        self.hits = [(mid, 0.0) for mid in self.rows]

    def test_five_neighbors_keep_order_and_exact_scalar_scores(self):
        old, new = make_engine(self.vectors), make_engine(self.vectors)
        expected = scalar_reference(self.content, self.hits, self.store, old)
        actual = helpers.compute_template_normalized_similarities(
            self.content, self.hits, self.store, new
        )
        self.assertEqual(actual, expected)
        self.assertEqual(len(actual), 5)
        self.assertEqual(old.encode.call_count, 6)
        new.encode.assert_not_called()
        new.encode_batch.assert_called_once_with(
            [capture_template_normalize(self.content)]
            + [capture_template_normalize(row["content"]) for row in self.rows.values()]
        )

    def test_float64_model_outputs_have_identical_float32_bytes(self):
        texts = list(self.vectors)
        scalar, batch = make_engine(self.vectors), make_engine(self.vectors)
        expected = [scalar.encode(text) for text in texts]
        actual = batch.encode_batch(texts)
        self.assertEqual(actual, expected)
        for vector in actual:
            self.assertIsInstance(vector, bytes)
            self.assertEqual(len(vector), 3 * np.dtype(np.float32).itemsize)
            self.assertEqual(np.frombuffer(vector, dtype=np.float32).shape, (3,))

    def test_missing_empty_and_skeleton_only_neighbors_keep_survivors(self):
        self.rows.update({6: {"content": ""}, 7: {"content": "# Tool: Read"}})
        self.vectors["# Tool: Read"] = (1, 1, 1)
        hits = [(99, 0.0), (6, 0.0), (2, 0.0), (7, 0.0), (1, 0.0)]
        old, new = make_engine(self.vectors), make_engine(self.vectors)
        self.assertEqual(
            helpers.compute_template_normalized_similarities(
                self.content, hits, self.store, new
            ),
            scalar_reference(self.content, hits, self.store, old),
        )
        self.assertEqual(len(new.encode_batch.call_args.args[0]), 4)
        self.assertNotIn("", new.encode_batch.call_args.args[0])

    def test_skeleton_only_input_keeps_the_normalizers_raw_fallback(self):
        self.vectors["# Tool: Read"] = (1, 1, 1)
        engine = make_engine(self.vectors)
        result = helpers.compute_template_normalized_similarities(
            "# Tool: Read", self.hits, self.store, engine
        )
        self.assertEqual(len(result), 5)
        self.assertEqual(engine.encode_batch.call_args.args[0][0], "# Tool: Read")
        engine.encode.assert_not_called()

    def test_absent_batch_vectors_preserve_none_and_skip_semantics(self):
        engine = make_engine(self.vectors)
        engine.encode_batch = Mock(return_value=[None, blob((1, 0, 0))])
        self.assertIsNone(
            helpers.compute_template_normalized_similarities(
                self.content, [(1, 0.0)], self.store, engine
            )
        )
        engine.encode_batch.return_value = [blob((1, 0, 0)), None, blob((1, 0, 0))]
        self.assertEqual(
            helpers.compute_template_normalized_similarities(
                self.content, [(2, 0.0), (1, 0.0)], self.store, engine
            ),
            [1.0],
        )

    def test_batch_failure_propagates_without_scalar_retry(self):
        engine = make_engine(self.vectors)
        engine.encode_batch = Mock(side_effect=RuntimeError("fixture encode failure"))
        with self.assertRaisesRegex(RuntimeError, "fixture encode failure"):
            helpers.compute_template_normalized_similarities(
                self.content, self.hits, self.store, engine
            )
        engine.encode.assert_not_called()


class MergeVectorReuse(unittest.TestCase):
    def test_identical_incoming_content_preserves_the_exact_object(self):
        content = "same raw content"
        for vector in (blob((1, 2, 3)), np.asarray([1, 2, 3], dtype=np.float32)):
            with self.subTest(type=type(vector).__name__):
                store, engine = Mock(), Mock()
                helpers._do_merge(
                    {"content": "raw content"}, 1, content, vector, 0.5, store, engine
                )
                stored = store.update_memory_compression.call_args.args[2]
                self.assertIs(stored, vector)
                engine.encode.assert_not_called()

    def test_changed_merge_reencodes_raw_text_including_whitespace(self):
        for existing, incoming in (("same", " same "), ("first", "second")):
            with self.subTest(existing=existing, incoming=incoming):
                store, engine = Mock(), Mock()
                merged = helpers.curation.merge_contents(existing, incoming)
                helpers._do_merge(
                    {"content": existing}, 1, incoming, b"raw", 0.5, store, engine
                )
                engine.encode.assert_called_once_with(merged)
                self.assertIs(
                    store.update_memory_compression.call_args.args[2],
                    engine.encode.return_value,
                )

    def test_unchanged_candidate_does_not_reuse_an_older_vector(self):
        store, engine = Mock(), Mock()
        candidate = {"content": "old and new", "embedding": b"older-model-vector"}
        helpers._do_merge(candidate, 1, "new", b"incoming-vector", 0.5, store, engine)
        engine.encode.assert_called_once_with("old and new")
        self.assertIs(
            store.update_memory_compression.call_args.args[2],
            engine.encode.return_value,
        )


if __name__ == "__main__":
    unittest.main()
