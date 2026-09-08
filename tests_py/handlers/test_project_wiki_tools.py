"""Project authoring isolation and rollback proof. # source: ADR-0056"""

import asyncio
import json

import pytest

from mcp_server.handlers import (
    project_wiki,
    wiki_adr,
    wiki_read,
    wiki_reindex,
    wiki_write,
)
from mcp_server.infrastructure.wiki_decision_index import lookup_decision
from mcp_server.infrastructure.wiki_decision_mirror import check_mirror


@pytest.fixture
def project(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    (root / "wiki").mkdir(parents=True)
    (root / "wiki/manifest.json").write_text(
        json.dumps(
            {
                "version": 1,
                "project": "cortex",
                "pages": {},
            }
        )
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("project mode must not touch global memory or citations")

    monkeypatch.setattr(wiki_write, "write_governed_page", forbidden)
    monkeypatch.setattr(wiki_adr, "_store_pointer_memory", forbidden)
    monkeypatch.setattr(wiki_read, "_cite_page", forbidden)
    return root


def _create(project):
    return asyncio.run(
        wiki_adr.handler(
            {
                "project_root": str(project),
                "title": "Tracked decisions",
                "context": "Reviewers need the source",
                "decision": "Mirror from wiki",
                "consequences": "One canonical authoring path",
            }
        )
    )


def test_project_adr_is_reviewable_and_never_published_to_global_memory(project):
    result = _create(project)
    assert result["number"] == 56
    assert result["path"] == "adr/cortex/0056-tracked-decisions.md"
    assert result["memory_sync"] == "project-files-only"
    assert check_mirror(project) == []
    assert lookup_decision(project / "wiki", "ADR-0056") == result["path"]
    read = asyncio.run(
        wiki_read.handler(
            {
                "project_root": str(project),
                "path": result["path"],
                "offset": 10,
            }
        )
    )
    full = (project / "wiki" / result["path"]).read_text()
    assert read["content"] == full[10:]
    assert read["memory_sync"] == "project-files-only"


def test_project_raw_write_registers_and_updates_mirror(project):
    created = _create(project)
    result = asyncio.run(
        wiki_write.handler(
            {
                "project_root": str(project),
                "path": created["path"],
                "content": "# ADR-0056\nUpdated decision\n",
                "mode": "replace",
            }
        )
    )
    assert result["memory_sync"] == "project-files-only"
    assert check_mirror(project) == []
    index = asyncio.run(wiki_reindex.handler({"project_root": str(project)}))
    assert index["total_pages"] == 1
    assert (project / "wiki/.generated/INDEX.md").exists()
    assert check_mirror(project) == []


def test_project_redirect_stays_in_project_and_can_be_disabled(project):
    created = _create(project)
    stub = project / "wiki/notes/link.md"
    stub.parent.mkdir()
    stub.write_text(f"---\nredirect_to: {created['path']}\n---\n")
    args = {"project_root": str(project), "path": "notes/link.md"}
    followed = asyncio.run(wiki_read.handler(args))
    assert followed["path"] == created["path"]
    assert followed["redirect_chain"] == ["notes/link.md", created["path"]]
    raw = asyncio.run(wiki_read.handler({**args, "follow_redirects": False}))
    assert raw["content"] == stub.read_text()


def test_failed_publication_restores_page_manifest_mirror_and_fresh_index(
    project, monkeypatch
):
    created = _create(project)
    page = project / "wiki" / created["path"]
    before = {
        p: p.read_bytes()
        for p in [
            page,
            project / "wiki/manifest.json",
            *list((project / "docs/adr").glob("*.md")),
        ]
    }
    real_generate = project_wiki.generate_mirror

    def fail_after_mirror(root):
        real_generate(root)
        raise OSError("simulated publication failure")

    monkeypatch.setattr(project_wiki, "generate_mirror", fail_after_mirror)
    result = asyncio.run(
        wiki_write.handler(
            {
                "project_root": str(project),
                "path": created["path"],
                "content": "replacement",
                "mode": "replace",
            }
        )
    )
    assert "simulated publication failure" in result["error"]
    assert all(p.read_bytes() == content for p, content in before.items())
    assert check_mirror(project) == []
    assert lookup_decision(project / "wiki", "ADR-0056") == created["path"]


def test_failed_new_adr_does_not_leave_page_or_manifest_entry(project, monkeypatch):
    def fail(root):
        raise OSError("mirror unavailable")

    monkeypatch.setattr(project_wiki, "generate_mirror", fail)
    result = _create(project)
    assert "mirror unavailable" in result["error"]
    assert not list((project / "wiki/adr").rglob("*.md"))
    assert json.loads((project / "wiki/manifest.json").read_text())["pages"] == {}
    assert lookup_decision(project / "wiki", "ADR-0056") is None


def test_project_path_escape_and_unregistered_root_rejected(project):
    escaped = asyncio.run(
        wiki_write.handler(
            {
                "project_root": str(project),
                "path": "../private.md",
                "content": "bad",
            }
        )
    )
    assert "error" in escaped
    missing = asyncio.run(
        wiki_read.handler(
            {
                "project_root": str(project / "missing"),
                "path": "adr/0056-test.md",
            }
        )
    )
    assert "error" in missing


def test_tool_bindings_expose_project_root_and_read_offset():
    import inspect
    from mcp_server import tool_registry_wiki

    class Registry:
        def __init__(self):
            self.tools = {}

        def tool(self, **kwargs):
            def register(function):
                self.tools[kwargs["name"]] = function
                return function

            return register

    registry = Registry()
    for name in ("write", "read", "adr", "reindex"):
        getattr(tool_registry_wiki, "_register_wiki_" + name)(registry)
        parameters = inspect.signature(registry.tools["wiki_" + name]).parameters
        assert parameters["project_root"].default is None
    assert "offset" in inspect.signature(registry.tools["wiki_read"]).parameters


@pytest.mark.parametrize("operation", ["page", "index"])
def test_predictable_temporary_symlink_cannot_escape_project(project, operation):
    victim = project.parent / "outside.txt"
    victim.write_text("outside sentinel")
    if operation == "page":
        page = project / "wiki/notes/example.md"
        page.parent.mkdir()
        page.write_text("prior page")
        page.with_suffix(".md.tmp").symlink_to(victim)
        result = asyncio.run(
            wiki_write.handler(
                {
                    "project_root": str(project),
                    "path": "notes/example.md",
                    "content": "replacement",
                    "mode": "replace",
                }
            )
        )
    else:
        page = project / "wiki/.generated/INDEX.md"
        page.parent.mkdir()
        page.with_suffix(".md.tmp").symlink_to(victim)
        result = asyncio.run(wiki_reindex.handler({"project_root": str(project)}))
    assert "error" not in result
    assert victim.read_text() == "outside sentinel"
    assert page.is_file() and not page.is_symlink()


def test_project_reindex_rejects_external_index_before_snapshot(project):
    victim = project.parent / "outside.txt"
    victim.write_text("outside sentinel")
    page = project / "wiki/.generated/INDEX.md"
    page.parent.mkdir()
    page.symlink_to(victim)
    result = asyncio.run(wiki_reindex.handler({"project_root": str(project)}))
    assert "error" in result
    assert victim.read_text() == "outside sentinel"


@pytest.mark.parametrize("root", ["", ".", "relative/path"])
@pytest.mark.parametrize("operation", ["write", "adr", "reindex"])
def test_project_mutations_require_explicit_absolute_root(
    project, monkeypatch, root, operation
):
    monkeypatch.chdir(project)
    args = {
        "project_root": root,
        "path": "notes/test.md",
        "content": "test",
        "title": "test",
        "context": "context",
        "decision": "decision",
        "consequences": "consequences",
    }
    handler = {"write": wiki_write, "adr": wiki_adr, "reindex": wiki_reindex}[operation]
    result = asyncio.run(handler.handler(args))
    assert "explicit absolute path" in result["error"]
    assert json.loads((project / "wiki/manifest.json").read_text())["pages"] == {}
