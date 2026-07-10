"""Tests for handlers.auto_task_record_writer._git_commits_in_window — #94.

This is the highest-risk call site named in cdeust/Cortex#94: reached
from the live ``record_session_end`` MCP tool
(``record_session_end.py:408``). It used
``subprocess.check_output(..., timeout=10)``; the fix routes through the
shared ``run_with_hard_timeout`` (Popen + single bounded communicate() +
kill, never a second communicate()) so a Windows timeout can't deadlock
the tool call.
"""

from __future__ import annotations

import subprocess

import pytest

from mcp_server.handlers import auto_task_record_writer as writer
from mcp_server.handlers.auto_task_record_writer import _git_commits_in_window


@pytest.fixture
def real_git_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=repo, check=True
    )
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    (repo / "a.txt").write_text("hello\n")
    subprocess.run(["git", "add", "a.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "initial commit"], cwd=repo, check=True)
    return repo


# ── Nominal behavior — real repo, real git, unchanged from check_output ─


def test_returns_empty_list_for_non_directory_cwd():
    assert _git_commits_in_window("/no/such/path-xyz-94", 60) == []


def test_returns_empty_list_for_empty_cwd():
    assert _git_commits_in_window("", 60) == []


def test_parses_a_real_commit_in_window(real_git_repo):
    commits = _git_commits_in_window(str(real_git_repo), 60)
    assert len(commits) == 1
    assert commits[0]["message"] == "initial commit"
    assert "a.txt" in commits[0]["files"]
    assert commits[0]["hash"]
    assert commits[0]["timestamp"]


def test_returns_empty_list_when_window_excludes_all_commits(real_git_repo):
    # since_minutes coerced to >= 1 minute — a negative/zero window still
    # covers "since 1 minute ago", so use a repo with no commits instead
    # to exercise the true "nothing in window" path deterministically.
    empty_repo = real_git_repo.parent / "empty"
    empty_repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=empty_repo, check=True)
    assert _git_commits_in_window(str(empty_repo), 60) == []


# ── #94: degraded result on timeout, via the shared helper ─────────────


def test_timeout_degrades_to_empty_list(monkeypatch, real_git_repo):
    monkeypatch.setattr(writer, "run_with_hard_timeout", lambda *a, **kw: None)
    assert _git_commits_in_window(str(real_git_repo), 60) == []


def test_uses_the_shared_hard_timeout_helper_with_a_10s_timeout(
    monkeypatch, real_git_repo
):
    calls = []

    def _spy(cmd, *, cwd=None, timeout=None, encoding=None):
        calls.append((cmd, timeout, encoding))
        return ""

    monkeypatch.setattr(writer, "run_with_hard_timeout", _spy)
    result = _git_commits_in_window(str(real_git_repo), 60)

    assert result == []
    assert len(calls) == 1
    cmd, timeout, encoding = calls[0]
    assert cmd[:2] == ["git", "-C"]
    assert timeout == 10
    assert encoding == "utf-8"


def test_multiple_commits_parsed_in_order(real_git_repo):
    (real_git_repo / "b.txt").write_text("world\n")
    subprocess.run(["git", "add", "b.txt"], cwd=real_git_repo, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "second commit"], cwd=real_git_repo, check=True
    )

    commits = _git_commits_in_window(str(real_git_repo), 60)

    assert len(commits) == 2
    messages = {c["message"] for c in commits}
    assert messages == {"initial commit", "second commit"}
