"""Project decision mirrors are deterministic, fail closed and stay inside root."""

import json

import pytest

from mcp_server.infrastructure.project_wiki import (
    contained_file,
    register_project_page,
    resolve_wiki_root,
)
from mcp_server.infrastructure.wiki_decision_mirror import (
    check_mirror,
    generate_mirror,
    mirror_bytes,
)


@pytest.fixture
def project(tmp_path):
    tmp_path = tmp_path / "project"
    directory = tmp_path / "wiki" / "adr" / "cortex"
    directory.mkdir(parents=True)
    (directory / "0056-decision.md").write_bytes(
        b"# Decision\r\n\r\nEvidence: caf\xc3\xa9\r\n"
    )
    manifest = {"version": 1, "project": "fixture", "pages": {}}
    (tmp_path / "wiki" / "manifest.json").write_text(json.dumps(manifest))
    register_project_page(tmp_path, "adr/cortex/0056-decision.md", "original-name.md")
    return tmp_path


def edit_manifest(root, edit):
    path = root / "wiki" / "manifest.json"
    manifest = json.loads(path.read_text())
    edit(manifest["pages"])
    path.write_text(json.dumps(manifest))


def test_mirror_bytes_are_deterministic_and_preserve_source_bytes(project):
    source = (project / "wiki" / "adr" / "cortex" / "0056-decision.md").read_bytes()
    first = generate_mirror(project)
    mirror = project / "docs" / "adr" / "original-name.md"
    content = mirror.read_bytes()
    stamp = mirror.stat().st_mtime_ns
    assert content == mirror_bytes("ADR-0056", "adr/cortex/0056-decision.md", source)
    assert content.split(b"\n\n", 1)[1] == source
    assert first["mirror_changed"] == ["original-name.md"]
    assert generate_mirror(project)["mirror_changed"] == []
    assert mirror.stat().st_mtime_ns == stamp
    assert check_mirror(project) == []


def test_manual_edit_and_source_update_both_require_regeneration(project):
    generate_mirror(project)
    mirror = project / "docs" / "adr" / "original-name.md"
    mirror.write_text("forged rationale")
    assert "stale or edited" in check_mirror(project)[0]
    generate_mirror(project)
    source = project / "wiki" / "adr" / "cortex" / "0056-decision.md"
    source.write_text("new measured rationale")
    assert "stale or edited" in check_mirror(project)[0]
    generate_mirror(project)
    assert check_mirror(project) == []


def test_missing_mirror_is_reported(project):
    assert "missing decision mirror" in check_mirror(project)[0]


@pytest.mark.parametrize("change", ["missing", "unregistered", "duplicate"])
def test_canonical_identity_inventory_must_match_manifest(project, change):
    directory = project / "wiki" / "adr" / "cortex"
    if change == "missing":
        (directory / "0056-decision.md").unlink()
    else:
        filename = "0057-new.md" if change == "unregistered" else "0056-duplicate.md"
        (directory / filename).write_text("evidence")
    assert check_mirror(project)
    with pytest.raises(ValueError):
        generate_mirror(project)
    assert not (project / "docs").exists()


def test_duplicate_mirror_names_are_rejected_before_writing(project):
    source = project / "wiki" / "adr" / "cortex" / "0057-other.md"
    source.write_text("another decision")
    edit_manifest(
        project,
        lambda pages: pages.update(
            {
                "ADR-0057": {
                    "path": "adr/cortex/0057-other.md",
                    "mirror": "original-name.md",
                }
            }
        ),
    )
    assert "duplicate mirror filename" in check_mirror(project)[0]
    with pytest.raises(ValueError, match="duplicate mirror filename"):
        generate_mirror(project)
    assert not (project / "docs").exists()


def test_extra_mirror_is_preserved_and_rejected(project):
    generate_mirror(project)
    extra = project / "docs" / "adr" / "rogue.md"
    extra.write_text("unreviewed rationale")
    assert "unexpected mirror file" in check_mirror(project)[0]
    with pytest.raises(ValueError, match="unmanaged mirror"):
        generate_mirror(project)
    assert extra.read_text() == "unreviewed rationale"


@pytest.mark.parametrize(
    "value", ["../outside.md", "/tmp/outside.md", "nested/file.md"]
)
def test_manifest_mirror_paths_cannot_escape(project, value):
    edit_manifest(project, lambda pages: pages["ADR-0056"].update(mirror=value))
    assert "invalid mirror filename" in check_mirror(project)[0]
    with pytest.raises(ValueError):
        generate_mirror(project)
    assert not (project / "docs").exists()


@pytest.mark.parametrize("surface", ["source", "mirror", "temporary", "manifest"])
def test_symlink_escape_cannot_read_or_overwrite_outside(project, tmp_path, surface):
    outside = tmp_path / "outside.txt"
    outside.write_text("outside sentinel")
    if surface == "source":
        target = project / "wiki" / "adr" / "cortex" / "0056-decision.md"
    elif surface == "manifest":
        target = project / "wiki" / "manifest.json"
    else:
        target = project / "docs" / "adr" / "original-name.md"
        if surface == "temporary":
            target = target.with_suffix(".md.tmp")
        target.parent.mkdir(parents=True)
    target.unlink(missing_ok=True)
    target.symlink_to(outside)
    with pytest.raises(ValueError):
        generate_mirror(project)
    assert outside.read_text() == "outside sentinel"


def test_resolve_project_root_requires_manifest_and_preserves_legacy_default(project):
    default = project / "legacy"
    assert resolve_wiki_root(None, default) == default
    assert resolve_wiki_root(str(project), default) == project / "wiki"
    with pytest.raises(OSError):
        resolve_wiki_root(str(project / "absent"), default)
    with pytest.raises(ValueError):
        contained_file(project, "../outside.md")


@pytest.mark.parametrize(
    "name", ["original-name.md", "../escape.md", "nested/file.md", "no-extension"]
)
def test_registration_rejects_invalid_or_duplicate_names_before_persisting(
    project, name
):
    source = project / "wiki" / "adr" / "cortex" / "0057-other.md"
    source.write_text("another decision")
    manifest = project / "wiki" / "manifest.json"
    before = manifest.read_bytes()
    with pytest.raises(ValueError):
        register_project_page(project, "adr/cortex/0057-other.md", name)
    assert manifest.read_bytes() == before


@pytest.mark.parametrize("root", ["", ".", "wiki", "../wiki"])
def test_explicit_project_root_cannot_be_relative(project, root):
    with pytest.raises(ValueError, match="explicit absolute path"):
        resolve_wiki_root(root, project / "legacy")


def test_duplicate_manifest_keys_cannot_hide_a_decision_entry(project):
    manifest = project / "wiki" / "manifest.json"
    manifest.write_text(
        '{"version": 1, "project": "fixture", "pages": '
        '{"ADR-0056": {}, "ADR-0056": {"path": "adr/cortex/0056-decision.md", '
        '"mirror": "original-name.md"}}}'
    )
    assert "duplicate manifest key: ADR-0056" in check_mirror(project)[0]
    with pytest.raises(ValueError, match="duplicate manifest key"):
        generate_mirror(project)
    assert not (project / "docs").exists()
