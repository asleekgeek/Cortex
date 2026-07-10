"""Tests for staleness file-reference extraction, incl. Windows paths.

source: RAPPORT_INSTALLATION_CORTEX_WINDOWS.md §5.6
"""

from __future__ import annotations

from mcp_server.core.staleness import assess_staleness, extract_file_references


def test_extracts_unix_relative_path():
    refs = extract_file_references("see src/core/staleness.py for details")
    assert "src/core/staleness.py" in refs


def test_extracts_windows_relative_backslash_path():
    refs = extract_file_references("see src\\core\\staleness.py for details")
    # Normalized to forward slashes regardless of separator used.
    assert "src/core/staleness.py" in refs


def test_extracts_windows_drive_absolute_path():
    refs = extract_file_references(
        "memory references C:\\Users\\me\\proj\\app.py which is gone"
    )
    assert "C:/Users/me/proj/app.py" in refs


def test_backslash_and_forward_slash_dedupe_to_one_ref():
    content = "src/a.py and src\\a.py are the same file"
    refs = extract_file_references(content)
    assert refs.count("src/a.py") == 1
    assert "src\\a.py" not in refs


def test_excludes_urls():
    # A URL must yield no filesystem references at all (stronger than checking
    # for a single host substring, which CodeQL flags as incomplete URL
    # sanitization — py/incomplete-url-substring-sanitization).
    refs = extract_file_references("docs at https://example.com/page.html")
    assert refs == []


def test_zero_score_never_stale_at_threshold_zero():
    # Regression (I6-D6): threshold=0.0 ("flag anything with one missing
    # reference") must not flag a memory whose refs ALL resolve. The naive
    # `score >= threshold` boundary made 0.0 >= 0.0 true, permanently
    # blocking de-stale rehabilitation at this threshold.
    report = assess_staleness(
        memory_id=1,
        content="See real.py",
        existing_paths={"real.py"},
        threshold=0.0,
    )
    assert report.staleness_score == 0.0
    assert report.is_stale is False


def test_any_missing_ref_still_stale_at_threshold_zero():
    report = assess_staleness(
        memory_id=1,
        content="See src/missing.py",
        existing_paths=set(),
        threshold=0.0,
    )
    assert report.staleness_score > 0.0
    assert report.is_stale is True
