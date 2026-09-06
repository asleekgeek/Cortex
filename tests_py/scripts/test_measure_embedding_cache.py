"""Measurement harness validation only; no model, database or benchmark run."""

from __future__ import annotations

import json
import tempfile
import unittest
from collections import OrderedDict
from pathlib import Path
from unittest.mock import patch

from scripts import measure_embedding_cache as measure


class FakeEngine:
    mode = "neural"

    def __init__(self):
        self._cache = OrderedDict()
        self.hits = 0
        self.misses = 0
        self.batch_calls = []

    def encode(self, text):
        if not text:
            return None
        if text in self._cache:
            self.hits += 1
        else:
            self.misses += 1
            self._cache[text] = text.encode()
        return self._cache[text]

    def encode_batch(self, texts):
        self.batch_calls.append(list(texts))
        return [self.encode(text) for text in texts]

    def cache_info(self):
        return {
            "hits": self.hits,
            "misses": self.misses,
            "batch_reuses": 0,
            "size": len(self._cache),
            "capacity": len(self._cache),
        }


class Harness(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.fixture = Path(temporary.name) / "session.jsonl"

    def write(self, records):
        self.fixture.write_text(
            "".join(json.dumps(record) + "\n" for record in records)
        )

    def test_replay_preserves_operations_and_only_reports_digest(self):
        self.write(
            [
                {"method": "encode", "text": "private text"},
                {"method": "encode_batch", "texts": ["private text", ""]},
            ]
        )
        engine = FakeEngine()
        result = measure.replay(engine, self.fixture)
        self.assertEqual(engine.batch_calls, [["private text", ""]])
        self.assertEqual(result["vectors"], 3)
        self.assertNotIn("private text", json.dumps(result))
        self.assertEqual(result, measure.replay(FakeEngine(), self.fixture))

    def test_rejects_invalid_fixture_without_echoing_content(self):
        for record in (
            {"method": "wrong", "text": "secret"},
            {"method": "encode_batch", "texts": ["secret", None]},
        ):
            self.write([record])
            with self.assertRaises(ValueError) as caught:
                measure.replay(FakeEngine(), self.fixture)
            self.assertNotIn("secret", str(caught.exception))

    def test_warm_and_cold_stats_are_measured_after_separate_primers(self):
        self.write([{"method": "encode", "text": "a"}])
        cold = measure.samples(FakeEngine(), self.fixture, 2, False)
        warm = measure.samples(FakeEngine(), self.fixture, 2, True)
        self.assertEqual([sample["cache"]["misses"] for sample in cold], [1, 1])
        self.assertEqual([sample["cache"]["hits"] for sample in warm], [1, 1])
        self.assertEqual(warm[0]["primer"]["cache"]["misses"], 1)
        self.assertTrue(warm[0]["discarded"])
        self.assertFalse(warm[1]["discarded"])

    def test_model_loader_refuses_before_import_without_download_opt_out(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "downloads are forbidden"):
                measure.load_engine(None)

    def test_measurement_refuses_a_runtime_fallback(self):
        self.write([{"method": "encode", "text": "a"}])
        engine = FakeEngine()
        engine.mode = "fallback"
        with self.assertRaisesRegex(RuntimeError, "changed to fallback"):
            measure.timed_replay(engine, self.fixture)


if __name__ == "__main__":
    unittest.main()
