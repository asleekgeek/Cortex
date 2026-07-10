"""Tests for infrastructure.git_diff_exec — #94 (shared kill-without-
recollect timeout pattern) plus the pre-existing CWE-78 allowlist/
sanitization behavior it must not regress.
"""

from __future__ import annotations

import subprocess

import pytest

from mcp_server.infrastructure import git_diff_exec as gde
from mcp_server.infrastructure.git_diff_exec import get_tracked_files, git_cmd_safe


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
    subprocess.run(["git", "commit", "-q", "-m", "initial"], cwd=repo, check=True)
    return repo


# ── Pre-existing allowlist/sanitization behavior — must not regress ────


def test_disallowed_subcommand_returns_empty(real_git_repo):
    assert git_cmd_safe("push", [], real_git_repo) == ""


def test_dangerous_arg_returns_empty(real_git_repo):
    assert git_cmd_safe("log", ["; rm -rf /"], real_git_repo) == ""


# ── Nominal behavior against a real repo (unchanged from subprocess.run) ─


def test_ls_files_lists_tracked_files(real_git_repo):
    out = git_cmd_safe("ls-files", [], real_git_repo)
    assert "a.txt" in out.splitlines()


def test_get_tracked_files_wraps_ls_files_as_a_set(real_git_repo):
    assert get_tracked_files(real_git_repo) == {"a.txt"}


def test_get_tracked_files_returns_empty_set_for_non_repo(tmp_path):
    not_a_repo = tmp_path / "plain"
    not_a_repo.mkdir()
    assert get_tracked_files(not_a_repo) == set()


def test_show_head_content(real_git_repo):
    out = git_cmd_safe("show", ["HEAD:a.txt"], real_git_repo)
    assert out == "hello"


# ── #94: degraded result on timeout, via the shared helper ─────────────


def test_timeout_from_run_with_hard_timeout_degrades_to_empty_string(
    monkeypatch, real_git_repo
):
    monkeypatch.setattr(gde, "run_with_hard_timeout", lambda *a, **kw: None)
    assert git_cmd_safe("log", [], real_git_repo) == ""


def test_git_cmd_safe_uses_the_shared_hard_timeout_helper(monkeypatch, real_git_repo):
    calls = []

    def _spy(cmd, *, cwd=None, timeout=None, encoding=None):
        calls.append((cmd, cwd, timeout))
        return "spied-output"

    monkeypatch.setattr(gde, "run_with_hard_timeout", _spy)
    out = git_cmd_safe("log", ["-1"], real_git_repo)

    assert out == "spied-output"
    assert len(calls) == 1
    cmd, cwd, timeout = calls[0]
    assert cmd[1:] == ["log", "-1"]
    assert cwd == real_git_repo
    assert timeout == 10
