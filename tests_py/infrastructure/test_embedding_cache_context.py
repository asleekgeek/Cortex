"""Prevent cache coordination from mixing recorded scalar/batch vector contexts."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from mcp_server.infrastructure.embedding_engine import EmbeddingEngine


@pytest.fixture
def recorded_engine():
    path = Path(__file__).parents[1] / "fixtures/w3_4/cache_context.json"
    data = json.loads(path.read_text())
    texts = data["texts"]
    scalar = [bytes.fromhex(value) for value in data["scalar_hex"]]
    batch = [bytes.fromhex(value) for value in data["batch_hex"]]
    assert scalar != batch
    engine = EmbeddingEngine()
    engine._ensure_model = Mock()
    engine._serve_fallback = Mock(return_value=True)
    engine._fallback_provider.encode = Mock(
        side_effect=dict(zip(texts, scalar, strict=True)).get
    )
    engine._fallback_provider.encode_batch = Mock(return_value=batch)
    return engine, texts, scalar, batch


def test_scalar_cache_does_not_replace_a_batch_context(recorded_engine):
    engine, texts, scalar, batch = recorded_engine
    assert engine.encode(texts[0]) == scalar[0]
    assert engine.encode_batch(texts) == batch
    engine._fallback_provider.encode_batch.assert_called_once_with(texts)


def test_batch_context_does_not_replace_a_scalar_result(recorded_engine):
    engine, texts, scalar, batch = recorded_engine
    assert engine.encode_batch(texts) == batch
    assert engine.encode(texts[0]) == scalar[0]
    engine._fallback_provider.encode.assert_called_once_with(texts[0])


def test_each_batch_keeps_its_original_inputs(recorded_engine):
    engine, texts, scalar, batch = recorded_engine
    assert engine.encode_batch(texts) == batch
    engine._fallback_provider.encode_batch.return_value = [scalar[0]]
    assert engine.encode_batch([texts[0]]) == [scalar[0]]
    assert engine._fallback_provider.encode_batch.call_args_list[-1].args == (
        [texts[0]],
    )


def test_explicit_warm_cache_retains_its_existing_contract(recorded_engine):
    engine, texts, _, batch = recorded_engine
    engine.warm_cache(texts)
    assert engine.encode(texts[0]) == batch[0]
    engine._fallback_provider.encode.assert_not_called()
