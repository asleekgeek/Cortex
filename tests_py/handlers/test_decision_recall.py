"""Exact decision IDs bypass semantic stores; scoped wiki search remains auditable."""

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from mcp_server.handlers import decision_recall, recall, unified_search
from mcp_server.infrastructure.wiki_decision_index import write_decision_index


@pytest.fixture
def project(tmp_path):
    wiki = tmp_path / "wiki"
    (wiki / "adr").mkdir(parents=True)
    (wiki / "manifest.json").write_text(
        json.dumps(
            {
                "version": 1,
                "project": "test",
                "pages": {},
            }
        )
    )
    (wiki / "adr/0056-identity.md").write_text(
        "# ADR-0056\n\nCanonical decision identifiers.\n"
    )
    write_decision_index(wiki)
    return tmp_path


@pytest.fixture
def blocked_backends(monkeypatch):
    embedding = Mock(side_effect=AssertionError("embedding must not run"))
    store = Mock(side_effect=AssertionError("memory DB must not run"))
    ap = Mock(side_effect=AssertionError("AP must not run"))
    monkeypatch.setattr(recall, "get_embedding_engine", embedding)
    monkeypatch.setattr(recall, "_get_store", store)
    monkeypatch.setattr(unified_search, "WorkflowGraphASTSource", ap)
    return embedding, store, ap


@pytest.mark.parametrize(
    "tool,key", [(recall, "memories"), (unified_search, "results")]
)
def test_known_identity_returns_canonical_page_without_backends(
    project, blocked_backends, tool, key
):
    result = asyncio.run(
        tool.handler({"query": "ADR-0056", "project_root": str(project)})
    )
    assert result["status"] == "ok"
    assert result[key][0]["id"] == "wiki:ADR-0056"
    assert result[key][0]["path"] == "adr/0056-identity.md"
    assert (
        result[key][0]["content"] == "# ADR-0056\n\nCanonical decision identifiers.\n"
    )
    assert "memory_id" not in result[key][0]
    for backend in blocked_backends:
        backend.assert_not_called()


@pytest.mark.parametrize(
    "query,status", [("ADR-9999", "not_found"), ("why ADR-0056?", "invalid_id")]
)
@pytest.mark.parametrize(
    "tool,key", [(recall, "memories"), (unified_search, "results")]
)
def test_exact_failure_never_falls_back(
    project, blocked_backends, query, status, tool, key
):
    result = asyncio.run(
        tool.handler({"query": query, "project_root": str(project), "exact_id": True})
    )
    assert result["status"] == status
    assert result[key] == []
    for backend in blocked_backends:
        backend.assert_not_called()


def test_stale_index_does_not_return_ambiguous_identity(project, blocked_backends):
    (project / "wiki/adr/0056-duplicate.md").write_text("# duplicate")
    result = asyncio.run(
        recall.handler({"query": "ADR-0056", "project_root": str(project)})
    )
    assert result["status"] == "error"
    assert "wiki_reindex" in result["reason"]
    assert result["memories"] == []


def test_no_project_root_preserves_global_exact_scope(
    project, monkeypatch, blocked_backends
):
    monkeypatch.setattr(decision_recall, "WIKI_ROOT", project / "wiki")
    result = asyncio.run(recall.handler({"query": "ADR-0056"}))
    assert result["memories"][0]["root"] == str(project / "wiki")


def test_ordinary_unified_query_adds_only_scoped_wiki_lane(project, monkeypatch):
    memory = AsyncMock(return_value={"memories": []})
    monkeypatch.setattr(unified_search, "recall_handler", memory)
    monkeypatch.setattr(unified_search, "is_enabled", lambda: False)
    args = {"query": "canonical identifiers", "project_root": str(project)}
    result = asyncio.run(unified_search.handler(args))
    assert result["sources"] == ["cortex", "wiki"]
    assert result["counts"]["wiki"] == 1
    assert result["results"][0]["source_ranks"] == {"wiki": 1}
    assert result["results"][0]["id"] == "wiki:ADR-0056"
    unscoped = asyncio.run(unified_search.handler({"query": args["query"]}))
    assert unscoped["results"] == []
    assert unscoped["sources"] == ["cortex"]


def test_ordinary_recall_does_not_enter_exact_lookup():
    assert (
        decision_recall.exact_lookup({"query": "why did we choose ADR-0056?"}) is None
    )


def test_bounded_exact_page_can_be_resumed(project, monkeypatch, blocked_backends):
    content = "# ADR-0056\n" + "authored detail " * 1000
    (project / "wiki/adr/0056-identity.md").write_text(content)
    # Test-only small cap exercises the production bound, not a runtime threshold.
    monkeypatch.setattr(
        decision_recall,
        "get_memory_settings",
        lambda: SimpleNamespace(MAX_RESPONSE_CHARS=1000),
    )
    args = {"query": "ADR-0056", "project_root": str(project)}
    first = asyncio.run(recall.handler(args))["memories"][0]
    assert first["truncated"]
    assert first["id"] == "wiki:ADR-0056"
    second = asyncio.run(
        recall.handler({**args, "content_offset": len(first["content"])})
    )["memories"][0]
    assert (
        first["content"] + second["content"]
        == content[: len(first["content"]) + len(second["content"])]
    )


@pytest.mark.parametrize("rooted", [False, True])
@pytest.mark.parametrize("tool_name", ["recall", "unified_search"])
def test_registered_wrappers_preserve_exact_scope(monkeypatch, rooted, tool_name):
    from mcp_server import tool_registry_memory

    captured = {}

    class Registry:
        def tool(self, *, name, **kwargs):
            def register(function):
                captured[name] = function
                return function

            return register

    monkeypatch.setattr(
        tool_registry_memory, "root_agent_topic", lambda: "agent" if rooted else None
    )
    dispatch = AsyncMock(return_value={})
    monkeypatch.setattr(tool_registry_memory, "safe_handler", dispatch)
    tool_registry_memory._register_recall(Registry())
    tool_registry_memory._register_unified_search(Registry())
    asyncio.run(
        captured[tool_name](
            query="ADR-0056", project_root="/selected/project", exact_id=True
        )
    )
    arguments = dispatch.call_args.args[1]
    assert arguments["project_root"] == "/selected/project"
    assert arguments["exact_id"] is True


def test_semantic_forwarding_preserves_existing_options(project, monkeypatch):
    memory = AsyncMock(return_value={"memories": []})
    monkeypatch.setattr(unified_search, "recall_handler", memory)
    monkeypatch.setattr(unified_search, "is_enabled", lambda: False)
    args = {
        "query": "ordinary query",
        "cross_domain": True,
        "sa_mode": "off",
        "max_results": 3,
        "k": 7,
    }
    asyncio.run(unified_search.handler(args))
    assert memory.call_args.args[0] == {
        key: value for key, value in {**args, "max_results": 6}.items() if key != "k"
    }
