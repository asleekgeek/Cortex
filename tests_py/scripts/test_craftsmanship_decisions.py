"""Source pointers resolve canonical identities without changing paper citations."""

from pathlib import Path

import pytest

from scripts.craftsmanship_decisions import check_decisions, check_source_ids


@pytest.mark.parametrize(
    "identity", ["ADR-1", "ADR-0000", "adr-0056", "ADR_0056", "ADR-00560"]
)
def test_malformed_decision_pointer_is_rejected(identity):
    assert "malformed" in check_source_ids(f"# source: {identity}\nx = 17\n", {})[0]


def test_existing_decision_is_valid_and_missing_one_fails():
    source = "# source: ADR-0056 because it documents the measured value\nx = 17\n"
    assert check_source_ids(source, {"ADR-0056": "adr/0056-example.md"}) == []
    assert "unknown decision ID ADR-0056" in check_source_ids(source, {})[0]


def test_only_comments_with_explicit_id_intent_are_resolved():
    source = """# source: Vaswani et al. (2017), equation 1.
# source: benchmarks/results/report.json
# source: docs/adr/0056-example.md
text = "# source: ADR-9999"
"""
    assert check_source_ids(source, {}) == []


def test_duplicate_wiki_ids_fail_closed_even_without_source_changes(tmp_path):
    directory = tmp_path / "wiki" / "adr"
    directory.mkdir(parents=True)
    (directory / "0056-one.md").write_text("one")
    (directory / "0056-two.md").write_text("two")
    errors = check_decisions(tmp_path, [])
    assert len(errors) == 1
    assert "duplicate decision identity ADR-0056" in errors[0]


def test_missing_wiki_fails_source_pointer(tmp_path: Path):
    (tmp_path / "module.py").write_text("# source: ADR-0056\nx = 17\n")
    assert "unknown decision ID ADR-0056" in check_decisions(tmp_path, ["module.py"])[0]


def test_docs_only_change_still_checks_complete_mirror(tmp_path, monkeypatch):
    from scripts import craftsmanship_decisions as decisions

    (tmp_path / "wiki").mkdir()
    visited = []

    def edited_mirror(root):
        visited.append(root)
        return ["stale or edited decision mirror: ADR-0056-example.md"]

    monkeypatch.setattr(decisions, "check_mirror", edited_mirror)
    assert "stale or edited" in decisions.check_decisions(tmp_path, [])[0]
    assert visited == [tmp_path]


@pytest.mark.parametrize("identity", ["ADR-56", "ADR-0000", "adr-0056", "ADR_0056"])
def test_docstring_malformed_ids_cannot_bypass_gate(identity):
    source = f'"""Purpose.\n\nsource: {identity}\n"""\nx = 1\n'
    assert "malformed decision ID" in check_source_ids(source, {})[0]


@pytest.mark.parametrize(
    "source",
    [
        '"""Purpose.\nsource: ADR-0056\n"""\nx = 1\n',
        'class Example:\n    """Purpose. source: ADR-0056"""\n',
        'def example():\n    """Purpose.\n\n    source: ADR-0056\n    """\n',
        'async def example():\n    """Purpose. # source: ADR-0056"""\n',
    ],
)
def test_actual_docstring_ids_resolve_canonical_page(source):
    assert "unknown decision ID ADR-0056" in check_source_ids(source, {})[0]
    assert check_source_ids(source, {"ADR-0056": "adr/0056-decision.md"}) == []


def test_runtime_and_non_docstring_literals_remain_excluded():
    source = '''message = "source: ADR-9999"
config = {"description": "source: ADR-9998"}
"""source: ADR-9997"""
def run():
    payload = "source: ADR-9996"
    return payload
'''
    assert check_source_ids(source, {}) == []
