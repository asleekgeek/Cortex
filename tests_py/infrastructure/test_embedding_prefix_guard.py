"""Guarded prefixes preserve token inputs; unsupported configurations opt out."""

from copy import deepcopy
import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from mcp_server.infrastructure.embedding_prefix import BertPrefix
from scripts.embedding_prefix_fixtures import fixtures
from scripts.measure_embedding_prefix import load_tokenizer, signature


def _model():
    config = {
        "model": {"type": "WordPiece"},
        "normalizer": {"type": "BertNormalizer"},
        "pre_tokenizer": {"type": "BertPreTokenizer"},
        "added_tokens": [{"content": "[MASK]", "normalized": False}],
        "post_processor": {
            "type": "TemplateProcessing",
            "single": [
                {"SpecialToken": {"id": "[CLS]", "type_id": 0}},
                {"Sequence": {"id": "A", "type_id": 0}},
                {"SpecialToken": {"id": "[SEP]", "type_id": 0}},
            ],
        },
    }
    tokenizer = SimpleNamespace(
        backend_tokenizer=SimpleNamespace(to_str=lambda: json.dumps(config)),
        truncation_side="right",
        encode=Mock(return_value=[0] * 256),
    )
    return SimpleNamespace(
        default_prompt_name=None, tokenizer=tokenizer, max_seq_length=256
    ), config


@pytest.mark.parametrize(
    "part", ["model", "normalizer", "pre_tokenizer", "post_processor"]
)
def test_unknown_tokenizer_components_are_not_shortened(part):
    model, config = _model()
    config[part]["type"] = "Unverified"
    assert BertPrefix.for_model(model) is None


@pytest.mark.parametrize(
    "content,normalized", [("foo bar", False), ("foo\u00a0bar", False), ("你好", True)]
)
def test_added_tokens_cannot_cross_the_boundary(content, normalized):
    model, config = _model()
    config["added_tokens"] = [{"content": content, "normalized": normalized}]
    assert BertPrefix.for_model(model) is None


def test_left_truncation_and_default_prompts_keep_the_full_model_path():
    model, _ = _model()
    model.tokenizer.truncation_side = "left"
    assert BertPrefix.for_model(model) is None
    model.tokenizer.truncation_side = "right"
    model.default_prompt_name = "query"
    assert BertPrefix.for_model(model) is None


@pytest.mark.parametrize("text", ["small", "a" * 10000, "a" + " " * 9998 + "b"])
def test_short_sparse_and_unbroken_inputs_do_not_tokenize_twice(text):
    model, _ = _model()
    guard = BertPrefix.for_model(model)
    assert guard is not None and guard.shorten(text) == text
    model.tokenizer.encode.assert_not_called()


def test_insufficient_prefix_budget_preserves_the_suffix():
    model, _ = _model()
    model.tokenizer.encode.return_value = [101, 100, 102]
    guard = BertPrefix.for_model(model)
    text = "longword " * 1250
    assert guard is not None and guard.shorten(text) == text
    model.tokenizer.encode.assert_called_once()


def test_tokenizer_failures_are_not_hidden():
    model, _ = _model()
    model.tokenizer.encode.side_effect = ValueError("bad tokenizer")
    guard = BertPrefix.for_model(model)
    assert guard is not None
    with pytest.raises(ValueError, match="bad tokenizer"):
        guard.shorten("complete words " * 1000)


def test_real_cached_tokenizer_preserves_all_adversarial_inputs():
    snapshot = os.environ.get("CORTEX_PREFIX_AUDIT_SNAPSHOT")
    if not snapshot:
        pytest.skip("requires explicit cached tokenizer snapshot")
    tokenizer, raw, config = load_tokenizer(Path(snapshot))
    original = deepcopy(raw)
    adapter = SimpleNamespace(encode=lambda text, **_kwargs: tokenizer.encode(text).ids)
    guard = BertPrefix(adapter, config["max_seq_length"])
    shortened = 0
    for text in fixtures(raw["model"]["max_input_chars_per_word"]).values():
        prefix = guard.shorten(text)
        assert text.startswith(prefix)
        assert signature(tokenizer.encode(prefix)) == signature(tokenizer.encode(text))
        shortened += prefix != text
    assert shortened > 0
    assert raw == original
