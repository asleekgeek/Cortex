"""Consecutive familiarity/Hopfield stages share one request observation."""

from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np
import pytest

from mcp_server.core.pg_recall_context import RecallContext, fetch_and_triage
from mcp_server.core.pg_recall_stages import apply_recollection_pipeline
from mcp_server.core.recall_pipeline import familiarity_triage, hopfield_complete


def _fixture():
    vectors = {i: row.tobytes() for i, row in enumerate(np.eye(3, dtype=np.float32))}
    store = SimpleNamespace(get_embeddings_for_memories=Mock(return_value=vectors))
    candidates = [
        {"memory_id": i, "content": "", "score": 1 / (i + 1)} for i in vectors
    ]
    ctx = RecallContext(
        query="",
        store=store,
        embeddings=SimpleNamespace(encode=lambda _text: vectors[2], dimensions=3),
        domain=None,
        directory=None,
        agent_topic=None,
        min_heat=0,
        wrrf_k=60,
        include_globals=False,
        cross_domain=False,
        sa_mode="off",
        rerank=False,
        rerank_alpha=0.70,
        familiarity_shortcut=False,
        top_k=3,
        momentum_state=None,
    )
    return ctx, candidates


def _disable_unrelated_stages(monkeypatch):
    for name in (
        "HDC",
        "DENDRITIC_CLUSTERS",
        "EMOTIONAL_RETRIEVAL",
        "MOOD_CONGRUENT_RERANK",
        "RECONSOLIDATION",
    ):
        monkeypatch.setenv("CORTEX_ABLATE_" + name, "1")


@pytest.mark.parametrize("disabled", [None, "DUAL_PROCESS", "HOPFIELD"])
def test_same_results_with_one_read_per_request(monkeypatch, disabled):
    _disable_unrelated_stages(monkeypatch)
    if disabled:
        monkeypatch.setenv("CORTEX_ABLATE_" + disabled, "1")
    ctx, candidates = _fixture()
    q_emb = ctx.embeddings.encode(ctx.query)
    expected = familiarity_triage(deepcopy(candidates), q_emb, ctx.store).candidates
    expected = hopfield_complete(expected, q_emb, ctx.store, embedding_dim=3)
    ctx.store.get_embeddings_for_memories.reset_mock()
    with patch(
        "mcp_server.core.pg_recall_context._wrrf_fetch", return_value=candidates
    ):
        triaged, resolved, early = fetch_and_triage(ctx)
    assert not early
    assert apply_recollection_pipeline(triaged, resolved) == expected
    ctx.store.get_embeddings_for_memories.assert_called_once_with([0, 1, 2])
    assert ctx.candidate_embeddings is None
    # A new request observes changed embeddings, never the prior snapshot.
    ctx.store.get_embeddings_for_memories.return_value = {}
    with patch(
        "mcp_server.core.pg_recall_context._wrrf_fetch", return_value=candidates
    ):
        _, next_request, _ = fetch_and_triage(ctx)
    assert next_request.candidate_embeddings.by_id == {}
    assert resolved.candidate_embeddings.by_id


@pytest.mark.parametrize("guard", ["ablated", "no_query_vector", "no_candidates"])
def test_no_embedding_read_when_both_stages_cannot_run(monkeypatch, guard):
    ctx, candidates = _fixture()
    if guard == "ablated":
        monkeypatch.setenv("CORTEX_ABLATE_DUAL_PROCESS", "1")
        monkeypatch.setenv("CORTEX_ABLATE_HOPFIELD", "1")
    elif guard == "no_query_vector":
        ctx = replace(ctx, embeddings=None)
    else:
        candidates = []
    with patch(
        "mcp_server.core.pg_recall_context._wrrf_fetch", return_value=candidates
    ):
        fetch_and_triage(ctx)
    ctx.store.get_embeddings_for_memories.assert_not_called()


def test_embedding_read_failure_is_not_hidden_or_retried():
    ctx, candidates = _fixture()
    ctx.store.get_embeddings_for_memories.side_effect = RuntimeError("read failed")
    with patch(
        "mcp_server.core.pg_recall_context._wrrf_fetch", return_value=candidates
    ):
        with pytest.raises(RuntimeError, match="read failed"):
            fetch_and_triage(ctx)
    ctx.store.get_embeddings_for_memories.assert_called_once()
