"""Cache/batch contracts with a deterministic NumPy double, never an ML model."""

from __future__ import annotations

import unittest
from collections import OrderedDict
from unittest.mock import Mock

import numpy as np

from mcp_server.infrastructure.embedding_engine import EmbeddingEngine


def model_vector(text):
    # Fixture geometry only; float64 exercises the engine's float32 conversion.
    return np.asarray([len(text), sum(map(ord, text)), 1], dtype=np.float64)


def make_engine():
    engine = EmbeddingEngine(dim=3)
    engine._ensure_model = Mock()
    engine._device = "cpu"
    engine._model = Mock()
    engine._model.encode.side_effect = lambda texts: (
        model_vector(texts)
        if isinstance(texts, str)
        else np.asarray([model_vector(text) for text in texts])
    )
    return engine


class BatchCache(unittest.TestCase):
    def test_batch_uses_scalar_cache_and_only_encodes_unique_misses(self):
        engine = make_engine()
        cached = engine.encode("already")
        engine._model.encode.reset_mock()
        texts = ["new", "already", "other", "new"]
        vectors = engine.encode_batch(texts)
        engine._model.encode.assert_called_once_with(["new", "other"])
        self.assertIs(vectors[1], cached)
        self.assertIs(vectors[0], vectors[3])
        self.assertEqual(texts, ["new", "already", "other", "new"])

    def test_batch_populates_scalar_cache_with_the_exact_float32_bytes(self):
        scalar, batch = make_engine(), make_engine()
        texts = ["alpha", "beta", "alpha"]
        expected = [scalar.encode(text) for text in texts]
        actual = batch.encode_batch(texts)
        self.assertEqual(actual, expected)
        for text, vector in zip(texts, actual, strict=True):
            self.assertIs(batch.encode(text), vector)
            self.assertEqual(np.frombuffer(vector, dtype=np.float32).shape, (3,))
        batch._model.encode.assert_called_once_with(["alpha", "beta"])

    def test_raw_spaces_remain_distinct_cache_and_batch_inputs(self):
        engine = make_engine()
        texts = ["a", " a ", "a  b", "a b"]
        vectors = engine.encode_batch(texts)
        engine._model.encode.assert_called_once_with(texts)
        self.assertEqual(len(engine._cache), len(texts))
        self.assertNotEqual(vectors[0], vectors[1])

    def test_none_results_keep_positions_without_entering_cache(self):
        engine = make_engine()
        engine._serve_fallback = Mock(return_value=True)
        engine._fallback_provider.encode_batch = Mock(return_value=[None])
        self.assertEqual(engine.encode_batch(["a", "a"]), [None, None])
        self.assertEqual(engine._cache, {})

    def test_access_order_and_eviction_match_input_order_beyond_capacity(self):
        engine = make_engine()
        engine._cache_max = 2  # small fixture, not a proposed production capacity
        engine.encode_batch(["a", "b"])
        sequence = ["c", "a", "d", "b", "c"]
        expected = OrderedDict((engine._cache_key(text), None) for text in ["a", "b"])
        for text in sequence:
            key = engine._cache_key(text)
            expected[key] = None
            expected.move_to_end(key)
            if len(expected) > engine._cache_max:
                expected.popitem(last=False)
        engine.encode_batch(sequence)
        self.assertEqual(list(engine._cache), list(expected))

    def test_empty_batch_never_initializes_or_calls_the_model(self):
        engine = make_engine()
        self.assertEqual(engine.encode_batch([]), [])
        engine._ensure_model.assert_not_called()
        engine._model.encode.assert_not_called()

    def test_empty_text_keeps_neural_batch_bytes_and_scalar_none(self):
        engine = make_engine()
        actual = engine.encode_batch(["", "a", ""])
        self.assertIsInstance(actual[0], bytes)
        self.assertEqual(actual[0], actual[2])
        self.assertIsNone(engine.encode(""))
        self.assertNotIn(engine._cache_key(""), engine._cache)

    def test_empty_text_keeps_fallback_batch_none(self):
        engine = make_engine()
        engine._serve_fallback = Mock(return_value=True)
        engine._fallback_provider.encode_batch = Mock(return_value=[b"vector", None])
        self.assertEqual(
            engine.encode_batch(["a", "", "a"]), [b"vector", None, b"vector"]
        )
        self.assertIsNone(engine.encode(""))
        self.assertEqual(engine.encode("a"), b"vector")

    def test_malformed_batch_length_does_not_partially_fill_cache(self):
        engine = make_engine()
        engine._model.encode.side_effect = lambda texts: np.asarray([model_vector("a")])
        with self.assertRaises(ValueError):
            engine.encode_batch(["a", "b"])
        self.assertEqual(engine._cache, {})

    def test_cpu_batch_error_is_preserved_and_cache_stays_empty(self):
        engine = make_engine()
        engine._model.encode.side_effect = RuntimeError("fixture CPU failure")
        with self.assertRaisesRegex(RuntimeError, "fixture CPU failure"):
            engine.encode_batch(["a"])
        self.assertEqual(engine._cache, {})

    def test_gpu_failure_keeps_existing_cpu_retry(self):
        engine = make_engine()
        engine._device = "mps"
        engine._fallback_to_cpu = Mock()
        engine._model.encode.side_effect = [RuntimeError("GPU"), [model_vector("a")]]
        vector = engine.encode_batch(["a"])[0]
        engine._fallback_to_cpu.assert_called_once()
        self.assertIsInstance(vector, bytes)
        self.assertEqual(engine._model.encode.call_count, 2)

    def test_warm_cache_does_not_double_insert_and_evict_other_entries(self):
        engine = make_engine()
        engine._cache_max = 2
        engine.warm_cache(["a", "a", "b"])
        engine.encode("a")
        engine.warm_cache(["a", "c"])
        self.assertEqual(
            list(engine._cache), [engine._cache_key(t) for t in ["a", "c"]]
        )

    def test_stats_distinguish_cache_hits_from_duplicates_without_content(self):
        engine = make_engine()
        engine.encode("already")
        engine.encode_batch(["new", "already", "new", ""])
        info = engine.cache_info()
        self.assertEqual(info["hits"], 1)
        self.assertEqual(info["misses"], 3)
        self.assertEqual(info["batch_reuses"], 1)
        self.assertEqual(
            set(info), {"hits", "misses", "batch_reuses", "size", "capacity"}
        )
        self.assertTrue(all(isinstance(value, int) for value in info.values()))

    def test_zero_capacity_is_an_explicit_measurement_control(self):
        engine = make_engine()
        engine._cache_max = 0
        engine.encode("a")
        engine.encode_batch(["a", "a"])
        self.assertEqual(engine._cache, {})
        self.assertEqual(engine.cache_info()["misses"], 3)
        self.assertEqual(engine._model.encode.call_count, 2)


if __name__ == "__main__":
    unittest.main()
