"""Tests for shared.domain_mapping's pure-Python git-root / remote-URL logic.

``_git_root`` and ``_get_remote_url`` used to shell out to ``git`` via
``subprocess.check_output(..., timeout=3)``. On Windows, a timeout on that
subprocess triggers CPython's own post-kill ``communicate()`` retry
(subprocess.py:565) with no deadline, which can hang forever if a
concurrently-spawned sibling process inherited the pipe's write handle
(cdeust/Cortex#91). The replacement does zero subprocess I/O — these tests
verify it reproduces ``git rev-parse --show-toplevel`` / ``git remote
get-url origin`` semantics for every shape the domain registry needs
(normal repo, subdirectory, linked worktree, non-repo, nonexistent path)
on the platforms this suite actually runs on (macOS/Linux CI). The
Windows-specific deadlock itself is not reproducible here — no subprocess
means nothing to reproduce; the rapporteur's own live-connection repro is
the remaining verification surface for that half of the claim.
"""

from __future__ import annotations

from pathlib import Path

from mcp_server.shared.domain_mapping import _get_remote_url, _git_root


# ── _git_root ────────────────────────────────────────────────────────────


def test_git_root_of_a_normal_repo(tmp_path):
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    assert _git_root(str(repo)) == str(repo).replace("\\", "/")


def test_git_root_from_a_subdirectory_walks_up(tmp_path):
    repo = tmp_path / "repo"
    subdir = repo / "src" / "nested"
    subdir.mkdir(parents=True)
    (repo / ".git").mkdir()
    assert _git_root(str(subdir)) == str(repo).replace("\\", "/")


def test_git_root_of_a_linked_worktree_is_the_worktree_itself(tmp_path):
    # git-worktree(1): a linked worktree's `.git` is a FILE (not a
    # directory) containing `gitdir: <path-to-main-repo>/.git/worktrees/<n>`.
    # `git rev-parse --show-toplevel` run inside the worktree returns the
    # worktree's own root, not the main repo's root — the pure-Python walk
    # must stop at the worktree's `.git` file, not keep climbing past it.
    main_repo = tmp_path / "main"
    (main_repo / ".git").mkdir(parents=True)
    worktree = tmp_path / "wt-feature"
    worktree.mkdir()
    (worktree / ".git").write_text(f"gitdir: {main_repo}/.git/worktrees/feature\n")
    assert _git_root(str(worktree)) == str(worktree).replace("\\", "/")


def test_git_root_from_inside_a_worktree_subdirectory(tmp_path):
    main_repo = tmp_path / "main"
    (main_repo / ".git").mkdir(parents=True)
    worktree = tmp_path / "wt-feature"
    subdir = worktree / "src"
    subdir.mkdir(parents=True)
    (worktree / ".git").write_text(f"gitdir: {main_repo}/.git/worktrees/feature\n")
    assert _git_root(str(subdir)) == str(worktree).replace("\\", "/")


def test_git_root_returns_none_when_not_in_a_repo(tmp_path):
    plain = tmp_path / "not-a-repo"
    plain.mkdir()
    assert _git_root(str(plain)) is None


def test_git_root_returns_none_for_nonexistent_path(tmp_path):
    missing = tmp_path / "does" / "not" / "exist"
    assert _git_root(str(missing)) is None


def test_git_root_stops_at_the_nearest_git_not_the_outermost(tmp_path):
    # Nested repos (submodule-like layouts without .gitmodules wiring, or
    # accidental nested clones): the nearest ancestor wins, matching git's
    # own behavior of resolving from cwd upward.
    outer = tmp_path / "outer"
    inner = outer / "inner"
    (outer / ".git").mkdir(parents=True)
    (inner / ".git").mkdir(parents=True)
    assert _git_root(str(inner)) == str(inner).replace("\\", "/")


def test_git_root_normalizes_backslashes_to_forward_slashes(tmp_path):
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    root = _git_root(str(repo))
    assert "\\" not in root


# ── _get_remote_url ─────────────────────────────────────────────────────


def test_get_remote_url_reads_origin_from_git_config(tmp_path):
    repo = tmp_path / "repo"
    git_dir = repo / ".git"
    git_dir.mkdir(parents=True)
    (git_dir / "config").write_text(
        '[core]\n'
        '\trepositoryformatversion = 0\n'
        '[remote "origin"]\n'
        '\turl = https://github.com/cdeust/Cortex.git\n'
        '\tfetch = +refs/heads/*:refs/remotes/origin/*\n'
    )
    assert _get_remote_url(repo) == "https://github.com/cdeust/Cortex.git"


def test_get_remote_url_ignores_a_different_remote_section(tmp_path):
    repo = tmp_path / "repo"
    git_dir = repo / ".git"
    git_dir.mkdir(parents=True)
    (git_dir / "config").write_text(
        '[remote "upstream"]\n'
        '\turl = https://github.com/other/other.git\n'
    )
    assert _get_remote_url(repo) == ""


def test_get_remote_url_returns_empty_when_no_config(tmp_path):
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    assert _get_remote_url(repo) == ""


def test_get_remote_url_returns_empty_when_no_remote_section(tmp_path):
    repo = tmp_path / "repo"
    git_dir = repo / ".git"
    git_dir.mkdir(parents=True)
    (git_dir / "config").write_text("[core]\n\trepositoryformatversion = 0\n")
    assert _get_remote_url(repo) == ""


def test_get_remote_url_returns_empty_for_worktree_git_file(tmp_path):
    # _get_remote_url is only ever called by _discover_repos on entries
    # where `(item / ".git").is_dir()` was already True — worktrees are
    # never routed here. Verify the defensive path anyway: a `.git` file
    # (not a directory) means `cfg.is_file()` is False for `.git/config`
    # (config would live at `.git`, a plain file, not `.git/config`), so
    # this returns '' rather than raising.
    repo = tmp_path / "wt"
    repo.mkdir(parents=True)
    (repo / ".git").write_text("gitdir: /somewhere/else\n")
    assert _get_remote_url(repo) == ""


def test_get_remote_url_never_raises_on_unreadable_config(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    git_dir = repo / ".git"
    git_dir.mkdir(parents=True)
    cfg = git_dir / "config"
    cfg.write_text('[remote "origin"]\n\turl = x\n')

    def _boom(*a, **kw):
        raise OSError("simulated read failure")

    monkeypatch.setattr(Path, "read_text", _boom)
    assert _get_remote_url(repo) == ""
