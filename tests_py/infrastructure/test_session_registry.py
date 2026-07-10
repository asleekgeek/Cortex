"""Unit tests for the per-window session registry (T2-handlers H1).

Covers the acceptance criteria named in the T2-handlers design and in
the H1 task brief: atomic writes (no partial file ever observable),
nominal read, dead-pid degradation + purge, pid-reuse (start-time
divergence) degradation, tombstone degradation, corrupt/unknown-version
degradation without exception, and the bounded ancestor walk.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time

import mcp_server.infrastructure.session_registry as sr


def _patch_dir(tmp_path, monkeypatch):
    target = tmp_path / "session-registry"
    monkeypatch.setattr(sr, "registry_dir", lambda: target)
    return target


def _spawn_dummy_process() -> subprocess.Popen:
    """A real, disposable child process this test can kill for a
    known-dead pid — no mocking of os.kill needed for that scenario."""
    return subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"],
    )


# ── atomic write ────────────────────────────────────────────────────────


def test_atomic_write_no_partial_file(tmp_path, monkeypatch):
    d = _patch_dir(tmp_path, monkeypatch)
    path = d / "123.json"
    ok = sr._atomic_write(path, {"v": 1, "a": "b" * 10_000})
    assert ok is True
    assert path.is_file()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["v"] == 1
    # no leftover tmp files
    assert list(d.glob("*.tmp.*")) == []


# ── nominal write + read ────────────────────────────────────────────────


def test_write_and_read_nominal(tmp_path, monkeypatch):
    _patch_dir(tmp_path, monkeypatch)
    monkeypatch.setattr(sr, "_process_start_signature", lambda pid: "sig-1")
    monkeypatch.setattr(sr, "_pid_alive", lambda pid: True)
    monkeypatch.setattr(os, "getppid", lambda: 4242)

    ok = sr.write_session("stem-abc", claude_pid=4242)
    assert ok is True
    assert sr.current_window_session() == "stem-abc"


def test_write_resolves_ancestor_when_pid_not_given(tmp_path, monkeypatch):
    _patch_dir(tmp_path, monkeypatch)
    monkeypatch.setattr(sr, "find_claude_ancestor", lambda: 9001)
    monkeypatch.setattr(sr, "_process_start_signature", lambda pid: "sig-9001")
    monkeypatch.setattr(sr, "_pid_alive", lambda pid: True)
    monkeypatch.setattr(os, "getppid", lambda: 9001)

    assert sr.write_session("stem-x") is True
    assert sr.current_window_session() == "stem-x"


def test_write_no_op_when_ancestor_unresolvable(tmp_path, monkeypatch):
    d = _patch_dir(tmp_path, monkeypatch)
    monkeypatch.setattr(sr, "find_claude_ancestor", lambda: None)
    assert sr.write_session("stem-y") is False
    assert list(d.glob("*.json")) == []


def test_write_no_op_when_start_signature_unresolvable(tmp_path, monkeypatch):
    d = _patch_dir(tmp_path, monkeypatch)
    monkeypatch.setattr(sr, "_process_start_signature", lambda pid: None)
    assert sr.write_session("stem-z", claude_pid=1) is False
    assert list(d.glob("*.json")) == []


# ── dead pid → None + purge ─────────────────────────────────────────────


def test_dead_pid_reads_as_none_and_gets_purged(tmp_path, monkeypatch):
    d = _patch_dir(tmp_path, monkeypatch)
    proc = _spawn_dummy_process()
    pid = proc.pid
    proc.terminate()
    proc.wait(timeout=5)
    # pid is now dead (reaped, so no zombie ambiguity)

    (d).mkdir(parents=True, exist_ok=True)
    (d / f"{pid}.json").write_text(
        json.dumps(
            {
                "v": 1,
                "session_id": "stale-stem",
                "claude_pid": pid,
                "claude_start_time": "sig-dead",
                "updated_at": time.time(),
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(os, "getppid", lambda: pid)
    assert sr.current_window_session() is None

    removed = sr.purge_dead_entries()
    assert removed == 1
    assert not (d / f"{pid}.json").exists()


# ── pid reuse (start-time divergence) → None ────────────────────────────


def test_start_time_divergence_returns_none(tmp_path, monkeypatch):
    d = _patch_dir(tmp_path, monkeypatch)
    d.mkdir(parents=True, exist_ok=True)
    (d / "555.json").write_text(
        json.dumps(
            {
                "v": 1,
                "session_id": "stem-old-lineage",
                "claude_pid": 555,
                "claude_start_time": "sig-old",
                "updated_at": time.time(),
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(os, "getppid", lambda: 555)
    monkeypatch.setattr(sr, "_pid_alive", lambda pid: True)
    # simulates pid 555 recycled by a new process with a different start
    monkeypatch.setattr(sr, "_process_start_signature", lambda pid: "sig-new")

    assert sr.current_window_session() is None


# ── tombstone → None ─────────────────────────────────────────────────────


def test_tombstone_reads_as_none(tmp_path, monkeypatch):
    _patch_dir(tmp_path, monkeypatch)
    monkeypatch.setattr(sr, "_process_start_signature", lambda pid: "sig-t")
    monkeypatch.setattr(sr, "_pid_alive", lambda pid: True)
    monkeypatch.setattr(os, "getppid", lambda: 777)

    assert sr.write_session("stem-live", claude_pid=777) is True
    assert sr.current_window_session() == "stem-live"

    assert sr.tombstone(777) is True
    assert sr.current_window_session() is None


# ── corrupted file / unknown version → None, no exception ──────────────


def test_corrupted_json_returns_none(tmp_path, monkeypatch):
    d = _patch_dir(tmp_path, monkeypatch)
    d.mkdir(parents=True, exist_ok=True)
    (d / "888.json").write_text("{not valid json", encoding="utf-8")
    monkeypatch.setattr(os, "getppid", lambda: 888)
    assert sr.current_window_session() is None  # no exception raised


def test_unknown_schema_version_returns_none(tmp_path, monkeypatch):
    d = _patch_dir(tmp_path, monkeypatch)
    d.mkdir(parents=True, exist_ok=True)
    (d / "999.json").write_text(
        json.dumps({"v": 99, "session_id": "x", "claude_pid": 999}),
        encoding="utf-8",
    )
    monkeypatch.setattr(os, "getppid", lambda: 999)
    assert sr.current_window_session() is None


def test_missing_file_returns_none(tmp_path, monkeypatch):
    _patch_dir(tmp_path, monkeypatch)
    monkeypatch.setattr(os, "getppid", lambda: 111111)
    assert sr.current_window_session() is None


def test_pid_mismatch_returns_none(tmp_path, monkeypatch):
    d = _patch_dir(tmp_path, monkeypatch)
    d.mkdir(parents=True, exist_ok=True)
    (d / "222.json").write_text(
        json.dumps(
            {
                "v": 1,
                "session_id": "stem",
                "claude_pid": 333,  # mismatched key vs recorded value
                "claude_start_time": "sig",
                "updated_at": time.time(),
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(os, "getppid", lambda: 222)
    assert sr.current_window_session() is None


# ── bounded ancestor walk ────────────────────────────────────────────────


def test_ancestor_walk_finds_claude(monkeypatch):
    # simulated tree: hook(getppid=200) -> bash(200) -> claude(100)
    chain = {200: (100, "bash"), 100: (1, "claude")}

    def fake_probe(pid):
        return chain.get(pid)

    monkeypatch.setattr(os, "getppid", lambda: 200)
    monkeypatch.setattr(sr, "_ppid_and_comm", fake_probe)
    assert sr.find_claude_ancestor() == 100


def test_ancestor_walk_no_match_returns_none(monkeypatch):
    chain = {200: (100, "bash"), 100: (50, "systemd"), 50: (1, "init")}

    def fake_probe(pid):
        return chain.get(pid)

    monkeypatch.setattr(os, "getppid", lambda: 200)
    monkeypatch.setattr(sr, "_ppid_and_comm", fake_probe)
    assert sr.find_claude_ancestor() is None


def test_ancestor_walk_respects_depth_bound(monkeypatch):
    # a chain with 20 hops and NO claude anywhere in it — must stop at
    # max_depth rather than walking forever / raising.
    chain = {i: (i + 1, "wrapper") for i in range(200, 220)}
    chain[220] = (1, "init")

    def fake_probe(pid):
        return chain.get(pid)

    monkeypatch.setattr(os, "getppid", lambda: 200)
    monkeypatch.setattr(sr, "_ppid_and_comm", fake_probe)
    assert sr.find_claude_ancestor(max_depth=5) is None


def test_ancestor_walk_probe_failure_returns_none(monkeypatch):
    monkeypatch.setattr(os, "getppid", lambda: 300)
    monkeypatch.setattr(sr, "_ppid_and_comm", lambda pid: None)
    assert sr.find_claude_ancestor() is None


# ── purge skips non-json / malformed stems, never raises ────────────────


def test_purge_skips_non_numeric_stems(tmp_path, monkeypatch):
    d = _patch_dir(tmp_path, monkeypatch)
    d.mkdir(parents=True, exist_ok=True)
    (d / "not-a-pid.json").write_text("{}", encoding="utf-8")
    (d / "notes.txt").write_text("irrelevant", encoding="utf-8")
    assert sr.purge_dead_entries() == 0
    assert (d / "not-a-pid.json").exists()


def test_purge_empty_dir_returns_zero(tmp_path, monkeypatch):
    _patch_dir(tmp_path, monkeypatch)  # dir does not even exist yet
    assert sr.purge_dead_entries() == 0
