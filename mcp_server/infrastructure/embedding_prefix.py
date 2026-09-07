"""Guarded suffix elision for single-text BERT WordPiece encoding.

BERT normalization preserves ASCII whitespace and WordPiece tokenizes whole
pre-tokenized words independently. A complete-word prefix that already fills
the model budget therefore preserves every model input. Unsupported tokenizer
configurations retain the normal full-input path; tokenizer errors propagate.

Sources: huggingface/tokenizers v0.22.2, normalizers/bert.rs,
pre_tokenizers/bert.rs, models/wordpiece/mod.rs; measured W3-3 fixture below.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any


# source: green-w3-3-guarded-prefix.md: maximum retained token end among the
# 10k fixtures saturating the pinned model budget. A cost probe, NOT a safety
# bound: complete-word and token-budget checks below decide every truncation.
_PROBE_CHARS = 1450
_BOUNDARIES = " \t\r\n"


def _supported(config: dict) -> bool:
    if config.get("model", {}).get("type") != "WordPiece":
        return False
    if config.get("normalizer", {}).get("type") != "BertNormalizer":
        return False
    if config.get("pre_tokenizer", {}).get("type") != "BertPreTokenizer":
        return False
    # Raw, whitespace-free added tokens cannot straddle the chosen boundary.
    if any(
        token["normalized"] or any(char.isspace() for char in token["content"])
        for token in config.get("added_tokens", [])
    ):
        return False
    processor = config.get("post_processor", {})
    single = processor.get("single", [])
    return processor.get("type") == "TemplateProcessing" and single == [
        {"SpecialToken": {"id": "[CLS]", "type_id": 0}},
        {"Sequence": {"id": "A", "type_id": 0}},
        {"SpecialToken": {"id": "[SEP]", "type_id": 0}},
    ]


@dataclass(frozen=True)
class BertPrefix:
    tokenizer: Any
    limit: int

    @classmethod
    def for_model(cls, model: Any) -> BertPrefix | None:
        """Enable only a verified single-input tokenizer without a prompt."""
        if getattr(model, "default_prompt_name", None) is not None:
            return None
        tokenizer = getattr(model, "tokenizer", None)
        if tokenizer is None:
            return None
        backend = getattr(tokenizer, "backend_tokenizer", None)
        limit = getattr(model, "max_seq_length", None)
        if backend is None or type(limit) is not int or limit <= 0:
            return None
        if tokenizer.truncation_side != "right":
            return None
        config = backend.to_str()
        if not isinstance(config, str) or not _supported(json.loads(config)):
            return None
        return cls(tokenizer, limit)

    def shorten(self, text: str) -> str:
        if len(text) <= _PROBE_CHARS:
            return text
        # str.find avoids a regex scan of a long word that cannot be shortened.
        # source: W3-3 boundary probe, same 16 boundaries, 25us -> 1.2us for
        # the 10k unbroken-word fixture (four samples, first discarded).
        positions = [text.find(char, _PROBE_CHARS) for char in _BOUNDARIES]
        positions = [pos for pos in positions if pos >= 0]
        if not positions:
            return text
        end = min(positions) + 1
        if end == len(text):
            return text
        prefix = text[:end]
        # A conservative cost guard for whitespace-heavy fixtures. Keeping the
        # full input is always exact, even if normalization expands characters.
        if len(prefix.strip()) < self.limit:
            return text
        tokens = self.tokenizer.encode(
            prefix, add_special_tokens=True, truncation=True, max_length=self.limit
        )
        return prefix if len(tokens) == self.limit else text
