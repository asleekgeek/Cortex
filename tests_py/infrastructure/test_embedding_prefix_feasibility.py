"""W3-3 adversaries: stdlib fixtures plus optional cached-tokenizer tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from scripts.embedding_prefix_fixtures import FIXTURE_CHARS, fixtures
from scripts.measure_embedding_prefix import load_tokenizer, signature, token_report


class PrefixFixtureContract(unittest.TestCase):
    def test_internal_space_counterexample_defeats_every_shorter_raw_prefix(self):
        text = "a" + " " * (FIXTURE_CHARS - len("ab")) + "b"
        self.assertEqual(text.strip(), text)
        self.assertEqual(text.split(), ["a", "b"])
        # All non-empty prefixes shorter than the full text contain only a
        # and whitespace. The tokenizer-specific consequence is tested below.
        self.assertEqual(text[:-1].rstrip(), "a")
        self.assertEqual(len(text), FIXTURE_CHARS)


class CachedTokenizerPrefix(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        snapshot = os.environ.get("CORTEX_PREFIX_AUDIT_SNAPSHOT")
        if not snapshot:
            raise unittest.SkipTest(
                "set CORTEX_PREFIX_AUDIT_SNAPSHOT to run cached-tokenizer audit"
            )
        cls.tokenizer, cls.raw, cls.config = load_tokenizer(Path(snapshot))
        cls.cases = fixtures(cls.raw["model"]["max_input_chars_per_word"])

    def test_every_adversary_has_contract_length(self):
        self.assertTrue(all(len(text) == FIXTURE_CHARS for text in self.cases.values()))

    def test_sequence_limit_comes_from_sentence_transformer_config(self):
        encoded = self.tokenizer.encode(self.cases["ordinary_prose"])
        self.assertEqual(len(encoded.ids), self.config["max_seq_length"])
        self.assertEqual(encoded.tokens[0], "[CLS]")
        self.assertEqual(encoded.tokens[-1], "[SEP]")

    def test_any_shorter_cap_loses_the_second_word(self):
        text = self.cases["internal_spaces"]
        self.assertEqual(
            self.tokenizer.encode(text).tokens, ["[CLS]", "a", "b", "[SEP]"]
        )
        for cap in (1, FIXTURE_CHARS - 1):
            self.assertEqual(
                self.tokenizer.encode(text[:cap]).tokens, ["[CLS]", "a", "[SEP]"]
            )
            self.assertFalse(
                token_report(self.tokenizer, text, cap)["model_inputs_equal"]
            )

    def test_controls_and_accents_can_join_letters_across_unbounded_input(self):
        expected = signature(self.tokenizer.encode("ab"))
        for name in (
            "null_controls",
            "format_controls",
            "replacement_chars",
            "combining_marks",
        ):
            text = self.cases[name]
            self.assertEqual(signature(self.tokenizer.encode(text)), expected)
            self.assertNotEqual(signature(self.tokenizer.encode(text[:-1])), expected)

    def test_cutting_word_changes_unk_into_wordpieces(self):
        limit = self.raw["model"]["max_input_chars_per_word"]
        text = self.cases["word_limit_boundary"]
        self.assertEqual(
            self.tokenizer.encode(text).tokens, ["[CLS]", "[UNK]", "[SEP]"]
        )
        self.assertNotIn("[UNK]", self.tokenizer.encode(text[:limit]).tokens)
        self.assertFalse(
            token_report(self.tokenizer, text, limit)["model_inputs_equal"]
        )

    def test_unknown_word_offset_covers_the_whole_word(self):
        text = self.cases["word_limit_boundary"]
        full = self.tokenizer.encode(text)
        end = full.offsets[1][1]
        self.assertEqual(end, self.raw["model"]["max_input_chars_per_word"] + 1)
        self.assertEqual(signature(full), signature(self.tokenizer.encode(text[:end])))

    def test_token_only_audit_does_not_load_model_packages(self):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "scripts.measure_embedding_prefix",
                "--snapshot",
                os.environ["CORTEX_PREFIX_AUDIT_SNAPSHOT"],
                "--cap",
                str(FIXTURE_CHARS - 1),
                "--case",
                "internal_spaces",
            ],
            cwd=Path(__file__).resolve().parents[2],
            text=True,
            capture_output=True,
            check=True,
        )
        report = json.loads(result.stdout)
        self.assertFalse(report["torch_loaded"])
        self.assertFalse(report["sentence_transformers_loaded"])
        self.assertFalse(report["preserves_fixture_model_inputs"])


if __name__ == "__main__":
    unittest.main()
