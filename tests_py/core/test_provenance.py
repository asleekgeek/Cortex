"""Tests for core/provenance.py — pure grading logic (I6-D6).

Contract:
  - extract_* functions are pure regex extraction, no I/O.
  - grade_provenance() takes pre-resolved per-reference outcomes and
    returns the WORST grade among them (unverifiable < verifiable <
    verified), or unverifiable when there is no extractable reference.
"""

from __future__ import annotations

from mcp_server.core.provenance import (
    UNVERIFIABLE,
    VERIFIABLE,
    VERIFIED,
    ProvenanceReport,
    extract_artifact_refs,
    extract_commit_refs,
    extract_url_refs,
    grade_provenance,
    has_citation_ref,
    write_time_hint,
)


# ── Extraction ───────────────────────────────────────────────────────────


class TestExtractCommitRefs:
    def test_extracts_full_sha(self):
        refs = extract_commit_refs("fixed in 8872d565a1b2c3d4e5f60718293a4b5c6d7e8f90")
        assert "8872d565a1b2c3d4e5f60718293a4b5c6d7e8f90" in refs

    def test_extracts_short_sha(self):
        refs = extract_commit_refs("see commit 8872d56 for the fix")
        assert "8872d56" in refs

    def test_excludes_all_digit_tokens(self):
        # A 10-digit run (e.g. a timestamp) is not a plausible commit SHA.
        refs = extract_commit_refs("recorded at 1234567890 in the log")
        assert refs == []

    def test_dedupes(self):
        refs = extract_commit_refs("8872d56 and again 8872d56")
        assert refs.count("8872d56") == 1


class TestExtractUrlRefs:
    def test_extracts_url(self):
        refs = extract_url_refs("see https://example.com/docs for details")
        assert refs == ["https://example.com/docs"]

    def test_strips_trailing_punctuation(self):
        refs = extract_url_refs("see (https://example.com/docs).")
        assert refs == ["https://example.com/docs"]

    def test_dedupes(self):
        refs = extract_url_refs("https://a.com and https://a.com again")
        assert refs.count("https://a.com") == 1


class TestExtractArtifactRefs:
    def test_extracts_path_and_digest(self):
        content = (
            "**Artifact:** `/home/x/.claude/methodology/artifacts/2026-07/"
            "0123456789abcdef.md` (5000 chars full output)"
        )
        refs = extract_artifact_refs(content)
        assert len(refs) == 1
        path, digest = refs[0]
        assert digest == "0123456789abcdef"
        assert path.endswith("0123456789abcdef.md")

    def test_no_artifact_ref_returns_empty(self):
        assert extract_artifact_refs("plain text, no artifact pointer") == []


class TestHasCitationRef:
    def test_doi_detected(self):
        assert has_citation_ref("Johnson (1993), doi:10.1037/0033-2909.114.1.3") is True

    def test_arxiv_detected(self):
        assert has_citation_ref("see arXiv:2301.12345 for details") is True

    def test_plain_text_not_detected(self):
        assert has_citation_ref("no citation here at all") is False


# ── Grading combination ───────────────────────────────────────────────────


def _grade(**kwargs) -> ProvenanceReport:
    defaults = dict(
        memory_id=1,
        file_refs=[],
        existing_paths=set(),
        commit_refs=[],
        commit_verdicts={},
        url_refs=[],
        url_verdicts={},
        artifact_refs=[],
        artifact_verdicts={},
        has_citation=False,
    )
    defaults.update(kwargs)
    return grade_provenance(**defaults)


class TestGradeNoRefs:
    def test_no_extractable_reference_is_unverifiable(self):
        report = _grade()
        assert report.grade == UNVERIFIABLE
        assert report.reason == "no_extractable_reference"


class TestGradeFileRefs:
    def test_all_files_exist_is_verified(self):
        report = _grade(file_refs=["a.py"], existing_paths={"a.py"})
        assert report.grade == VERIFIED

    def test_missing_file_is_unverifiable(self):
        report = _grade(file_refs=["a.py"], existing_paths=set())
        assert report.grade == UNVERIFIABLE
        assert "a.py" in report.dead_refs


class TestGradeCommitRefs:
    def test_found_commit_is_verified(self):
        report = _grade(commit_refs=["8872d56"], commit_verdicts={"8872d56": True})
        assert report.grade == VERIFIED

    def test_unresolvable_commit_is_verifiable_not_unverifiable(self):
        # Per I6-D6: a commit ref never grades UNVERIFIABLE by itself — a
        # stale/shallow local clone is indistinguishable from a dead SHA.
        report = _grade(commit_refs=["deadbee"], commit_verdicts={"deadbee": False})
        assert report.grade == VERIFIABLE
        assert "deadbee" in report.uncheckable_refs


class TestGradeUrlRefs:
    def test_reachable_url_is_verifiable_not_verified(self):
        # URLs can never raise a memory to VERIFIED (the web fluctuates).
        report = _grade(
            url_refs=["https://a.com"], url_verdicts={"https://a.com": True}
        )
        assert report.grade == VERIFIABLE

    def test_dead_url_is_unverifiable(self):
        report = _grade(
            url_refs=["https://a.com"], url_verdicts={"https://a.com": False}
        )
        assert report.grade == UNVERIFIABLE
        assert report.dead_refs == ["https://a.com"]

    def test_unsampled_url_is_verifiable_not_penalized(self):
        # verdict=None means "not checked this pass" (bounded sample) —
        # must never be treated as dead.
        report = _grade(
            url_refs=["https://a.com"], url_verdicts={"https://a.com": None}
        )
        assert report.grade == VERIFIABLE
        assert report.uncheckable_refs == ["https://a.com"]


class TestGradeArtifactRefs:
    def test_matching_digest_is_verified(self):
        report = _grade(
            artifact_refs=[("art.md", "abc123")],
            artifact_verdicts={"art.md": True},
        )
        assert report.grade == VERIFIED

    def test_missing_or_mismatched_digest_is_unverifiable(self):
        report = _grade(
            artifact_refs=[("art.md", "abc123")],
            artifact_verdicts={"art.md": False},
        )
        assert report.grade == UNVERIFIABLE
        assert "art.md" in report.dead_refs


class TestGradeCitationRefs:
    def test_citation_alone_is_verifiable_at_best(self):
        report = _grade(has_citation=True)
        assert report.grade == VERIFIABLE

    def test_citation_never_reaches_verified(self):
        # Even with an otherwise-verified file ref, a memory that ALSO
        # carries an uncheckable citation caps at verifiable (worst-case
        # combination — citation contributes a VERIFIABLE outcome).
        report = _grade(file_refs=["a.py"], existing_paths={"a.py"}, has_citation=True)
        assert report.grade == VERIFIABLE


class TestGradeCombination:
    def test_mixed_verified_and_verifiable_yields_verifiable(self):
        report = _grade(
            file_refs=["a.py"],
            existing_paths={"a.py"},
            commit_refs=["deadbee"],
            commit_verdicts={"deadbee": False},
        )
        assert report.grade == VERIFIABLE

    def test_any_dead_ref_dominates_to_unverifiable(self):
        report = _grade(
            file_refs=["a.py", "b.py"],
            existing_paths={"a.py"},  # b.py missing
            commit_refs=["8872d56"],
            commit_verdicts={"8872d56": True},
        )
        assert report.grade == UNVERIFIABLE
        assert "b.py" in report.dead_refs

    def test_all_verified_across_types_is_verified(self):
        report = _grade(
            file_refs=["a.py"],
            existing_paths={"a.py"},
            commit_refs=["8872d56"],
            commit_verdicts={"8872d56": True},
            artifact_refs=[("art.md", "abc123")],
            artifact_verdicts={"art.md": True},
        )
        assert report.grade == VERIFIED

    def test_ref_counts_reported(self):
        report = _grade(
            file_refs=["a.py"],
            existing_paths={"a.py"},
            commit_refs=["8872d56"],
            commit_verdicts={"8872d56": True},
            has_citation=True,
        )
        assert report.ref_counts == {
            "file": 1,
            "commit": 1,
            "url": 0,
            "artifact": 0,
            "citation": 1,
        }


# ── write_time_hint (M-D5, 7.5) ─────────────────────────────────────────────


def _report(grade: str) -> ProvenanceReport:
    return ProvenanceReport(memory_id=0, grade=grade, ref_counts={})


class TestWriteTimeHint:
    def test_verified_hint(self):
        assert "verified locally" in write_time_hint(_report(VERIFIED))

    def test_verifiable_hint(self):
        hint = write_time_hint(_report(VERIFIABLE))
        assert "not conclusively checked" in hint

    def test_unverifiable_hint_non_deliberate_is_plain(self):
        hint = write_time_hint(_report(UNVERIFIABLE), write_class="auto")
        assert "No checkable reference" in hint
        assert "durable claim" not in hint

    def test_unverifiable_hint_deliberate_gets_call_to_action(self):
        hint = write_time_hint(_report(UNVERIFIABLE), write_class="deliberate")
        assert "No checkable reference" in hint
        assert "durable claim" in hint

    def test_unverifiable_hint_no_write_class_is_plain(self):
        hint = write_time_hint(_report(UNVERIFIABLE))
        assert "durable claim" not in hint

    def test_hint_never_persisted_is_a_pure_function(self):
        # Same report + write_class always yields the same string -- no
        # hidden state, no I/O (contract: deterministic lookup only).
        r = _report(UNVERIFIABLE)
        assert write_time_hint(r, "deliberate") == write_time_hint(r, "deliberate")
