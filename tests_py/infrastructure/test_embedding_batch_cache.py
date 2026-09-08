"""Cache/batch contracts with a deterministic NumPy double, never an ML model."""

from __future__ import annotations

import unittest
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
    def test_batch_keeps_all_positions_and_does_not_read_scalar_cache(self):
        engine = make_engine()
        engine.encode("already")
        engine._model.encode.reset_mock()
        texts = ["new", "already", "other", "new"]
        vectors = engine.encode_batch(texts)
        engine._model.encode.assert_called_once_with(texts)
        self.assertEqual(len(vectors), len(texts))
        self.assertEqual(list(engine._cache), [engine._cache_key("already")])

    def test_batch_preserves_raw_spaces_without_populating_scalar_cache(self):
        engine = make_engine()
        texts = ["a", " a ", "a  b", "a b"]
        vectors = engine.encode_batch(texts)
        engine._model.encode.assert_called_once_with(texts)
        self.assertEqual(engine._cache, {})
        self.assertNotEqual(vectors[0], vectors[1])

    def test_fallback_batch_keeps_empty_text_and_duplicate_positions(self):
        engine = make_engine()
        engine._serve_fallback = Mock(return_value=True)
        engine._fallback_provider.encode_batch = Mock(
            return_value=[b"vector", None, b"vector"]
        )
        texts = ["a", "", "a"]
        self.assertEqual(engine.encode_batch(texts), [b"vector", None, b"vector"])
        engine._fallback_provider.encode_batch.assert_called_once_with(texts)
        self.assertEqual(engine._cache, {})
        self.assertIsNone(engine.encode(""))

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

    def test_explicit_warming_and_scalar_lru_keep_existing_eviction_order(self):
        engine = make_engine()
        engine._cache_max = 2  # Tiny test cache, not a production policy.
        engine.warm_cache(["a", "a", "b"])
        engine.encode("a")
        engine.warm_cache(["a", "c"])
        self.assertEqual(
            list(engine._cache), [engine._cache_key(t) for t in ["a", "c"]]
        )

    def test_counters_observe_scalar_lookups_without_redefining_batch_calls(self):
        engine = make_engine()
        engine.encode("already")
        engine.encode("already")
        before = engine.cache_info()
        engine.encode_batch(["new", "already", "new", ""])
        self.assertEqual(engine.cache_info(), before)
        self.assertEqual(before["hits"], 1)
        self.assertEqual(before["misses"], 1)
        self.assertEqual(before["batch_reuses"], 0)
        self.assertEqual(
            set(before), {"hits", "misses", "batch_reuses", "size", "capacity"}
        )

    def test_zero_capacity_is_an_explicit_measurement_control(self):
        engine = make_engine()
        engine._cache_max = 0
        engine.encode("a")
        engine.encode("a")
        engine.encode_batch(["a", "a"])
        self.assertEqual(engine._cache, {})
        self.assertEqual(engine.cache_info()["misses"], 2)
        self.assertEqual(engine._model.encode.call_count, 3)


if __name__ == "__main__":
    unittest.main()
