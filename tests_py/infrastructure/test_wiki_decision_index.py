"""Identity and migration regression evidence for issue #514 / ADR-0056."""

from pathlib import Path

import pytest

from mcp_server.infrastructure.wiki_decision_index import (
    decision_index,
    quarantine_malformed_decisions,
)
from mcp_server.infrastructure.wiki_pages_listing import next_adr_number
from mcp_server.shared.wiki_decision_ids import decision_id, parse_decision_id


@pytest.mark.parametrize(
    "text",
    [
        "ADR-0000",
        "ADR-56",
        "ADR-10000",
        "adr-0056",
        " ADR-0056",
        "ADR-0056: title",
        "ADR-００５６",
    ],
)
def test_token_is_complete_ascii_identity(text):
    assert parse_decision_id(text) is None


def test_canonical_roundtrip():
    for number in range(1, 10000):
        assert parse_decision_id(decision_id(number)) == number


@pytest.mark.parametrize("number", [0, 10000, -1, True, 1.0])
def test_invalid_number_rejected(number):
    with pytest.raises(ValueError):
        decision_id(number)


def _page(root: Path, name: str, body: bytes = b"decision\n"):
    target = root / "adr" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(body)
    return target


def test_index_excludes_timestamps_and_scans_nested_pages(tmp_path):
    _page(tmp_path, "20260826-accidental.md")
    _page(tmp_path, "cortex/0056-decision.md")
    _page(tmp_path, "notes.md")
    assert decision_index(tmp_path) == {"ADR-0056": "adr/cortex/0056-decision.md"}
    assert next_adr_number(tmp_path) == 57


def test_duplicates_rejected(tmp_path):
    _page(tmp_path, "0056-one.md")
    _page(tmp_path, "other/0056-two.md")
    with pytest.raises(ValueError, match="duplicate decision identity"):
        decision_index(tmp_path)
    with pytest.raises(ValueError, match="duplicate decision identity"):
        next_adr_number(tmp_path)


def test_sequence_exhaustion(tmp_path):
    _page(tmp_path, "9999-last.md")
    with pytest.raises(ValueError, match="exhausted"):
        next_adr_number(tmp_path)


def test_escaping_symlink_rejected(tmp_path):
    root = tmp_path / "wiki"
    (root / "adr").mkdir(parents=True)
    outside = tmp_path / "private.md"
    outside.write_text("private")
    (root / "adr/0056-leak.md").symlink_to(outside)
    with pytest.raises(ValueError, match="escapes"):
        decision_index(root)


def test_quarantine_requires_opt_in_and_preserves_bytes(tmp_path):
    original = _page(tmp_path, "nested/20260826-malformed.md", b"raw\r\n\xff")
    _page(tmp_path, "0056-valid.md")
    expected = {
        "adr/nested/20260826-malformed.md": (
            ".quarantine/adr/nested/20260826-malformed.md"
        )
    }
    assert quarantine_malformed_decisions(tmp_path) == expected
    assert original.exists()
    assert quarantine_malformed_decisions(tmp_path, apply=True) == expected
    assert not original.exists()
    assert (tmp_path / next(iter(expected.values()))).read_bytes() == b"raw\r\n\xff"
    assert decision_index(tmp_path) == {"ADR-0056": "adr/0056-valid.md"}


def test_quarantine_does_not_overwrite_existing_record(tmp_path):
    original = _page(tmp_path, "20260826-bad.md")
    target = tmp_path / ".quarantine/adr/20260826-bad.md"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"prior")
    with pytest.raises(ValueError, match="already exists"):
        quarantine_malformed_decisions(tmp_path, apply=True)
    assert original.exists()
    assert target.read_bytes() == b"prior"


def test_persisted_index_reproducible_and_stale_detection(tmp_path):
    from mcp_server.infrastructure.wiki_decision_index import (
        lookup_decision,
        write_decision_index,
    )

    _page(tmp_path, "0056-one.md")
    with pytest.raises(ValueError, match="missing"):
        lookup_decision(tmp_path, "ADR-0056")
    write_decision_index(tmp_path)
    output = tmp_path / ".generated/decision-index.json"
    first = output.read_bytes()
    write_decision_index(tmp_path)
    assert output.read_bytes() == first
    assert lookup_decision(tmp_path, "ADR-0056") == "adr/0056-one.md"
    assert lookup_decision(tmp_path, "ADR-0057") is None
    _page(tmp_path, "0057-new.md")
    with pytest.raises(ValueError, match="stale"):
        lookup_decision(tmp_path, "ADR-0056")
    write_decision_index(tmp_path)
    _page(tmp_path, "nested/0056-duplicate.md")
    with pytest.raises(ValueError, match="stale"):
        lookup_decision(tmp_path, "ADR-0056")


@pytest.mark.parametrize(
    "change", ["duplicate", "new_domain", "delete", "rename", "symlink"]
)
def test_directory_evidence_rejects_identity_changes(tmp_path, change):
    from mcp_server.infrastructure.wiki_decision_index import (
        lookup_decision,
        write_decision_index,
    )

    page = _page(tmp_path, "domain/0056-first.md")
    write_decision_index(tmp_path)
    if change == "duplicate":
        _page(tmp_path, "domain/0056-second.md")
    elif change == "new_domain":
        _page(tmp_path, "new-domain/0056-second.md")
    elif change == "delete":
        page.unlink()
    elif change == "rename":
        page.rename(page.with_name("0056-renamed.md"))
    else:
        page.unlink()
        page.symlink_to(tmp_path / "private.md")
    with pytest.raises(ValueError, match="stale"):
        lookup_decision(tmp_path, "ADR-0056")


def test_body_edit_does_not_invalidate_identity(tmp_path):
    from mcp_server.infrastructure.wiki_decision_index import (
        lookup_decision,
        write_decision_index,
    )

    page = _page(tmp_path, "0056-first.md")
    write_decision_index(tmp_path)
    page.write_text("Updated decision body")
    relative = lookup_decision(tmp_path, "ADR-0056")
    assert relative == "adr/0056-first.md"
    assert (tmp_path / relative).read_text() == "Updated decision body"


def test_lookup_does_not_scan_source_files(tmp_path, monkeypatch):
    from mcp_server.infrastructure import wiki_decision_index as module

    _page(tmp_path, "0056-first.md")
    module.write_decision_index(tmp_path)

    def forbidden(*args):
        raise AssertionError("lookup must use directory evidence, not scan pages")

    monkeypatch.setattr(module, "decision_index", forbidden)
    assert module.lookup_decision(tmp_path, "ADR-0056") == "adr/0056-first.md"


@pytest.mark.parametrize("name", ["decision-index.json", "decision-index-state.json"])
def test_corrupted_index_fails_closed(tmp_path, name):
    from mcp_server.infrastructure.wiki_decision_index import (
        lookup_decision,
        write_decision_index,
    )

    _page(tmp_path, "0056-first.md")
    write_decision_index(tmp_path)
    (tmp_path / ".generated" / name).write_text("{}")
    with pytest.raises(ValueError):
        lookup_decision(tmp_path, "ADR-0056")
