"""Tests for scripts/launcher_deps.py — issue #97.

Source: issue #97 (reporter mbe14, Windows 11). The prior commit step
in ``_pip_install`` blindly ``rmtree``'d + ``os.replace``'d every
top-level entry pip resolved into a temp dir, including transitive deps
(numpy, pulled in by sentence-transformers) already correctly installed
and locked by a concurrently-running MCP server on Windows. A mid-loop
``PermissionError`` then hit the old ``finally: shutil.rmtree(tmp_dir)``,
destroying the fresh install too — irrecoverable, and re-triggered on
every subsequent hook invocation.

These tests exercise the pure logic cross-platform: the idempotence
guard (never touch an already-satisfied dest), the non-destructive
commit + rollback on a simulated mid-commit failure (monkeypatched
``os.replace``), and the stamp/lock fast path. The actual Windows
file-lock failure mode itself can only be reproduced on Windows — see
the module's docstring and this repo's prior #91-#96 Windows fixes for
the same epistemic position.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DEPS_MODULE_PATH = REPO_ROOT / "scripts" / "launcher_deps.py"


@pytest.fixture
def deps_mod():
    spec = importlib.util.spec_from_file_location(
        "_cortex_launcher_deps", DEPS_MODULE_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _make_dist_info(root: Path, dist_name: str, version: str) -> None:
    d = root / f"{dist_name}-{version}.dist-info"
    d.mkdir(parents=True, exist_ok=True)
    (d / "METADATA").write_text(
        f"Name: {dist_name}\nVersion: {version}\n", encoding="utf-8"
    )


def _make_pkg_dir(root: Path, pkg_name: str, marker: str = "x") -> None:
    d = root / pkg_name
    d.mkdir(parents=True, exist_ok=True)
    (d / "__init__.py").write_text(f"# {marker}\n", encoding="utf-8")


# ---------------------------------------------------------------- helpers ---


def test_normalize_dist_key_folds_separators(deps_mod):
    assert deps_mod._normalize_dist_key("pydantic-settings") == "pydantic_settings"
    assert deps_mod._normalize_dist_key("pydantic_settings") == "pydantic_settings"
    assert deps_mod._normalize_dist_key("PyDantic.Settings") == "pydantic_settings"


def test_parse_pip_spec_strips_extras_and_version(deps_mod):
    assert deps_mod._parse_pip_spec("psycopg[binary]==3.3.3") == ("psycopg", "3.3.3")
    assert deps_mod._parse_pip_spec("numpy==2.4.4") == ("numpy", "2.4.4")


def test_dist_info_versions_scans_only_dist_info_dirs(deps_mod, tmp_path):
    _make_dist_info(tmp_path, "numpy", "2.4.4")
    _make_pkg_dir(tmp_path, "numpy")
    (tmp_path / "not_a_dist_info").mkdir()
    versions = deps_mod._dist_info_versions(str(tmp_path))
    assert versions == {"numpy": "2.4.4"}


def test_dist_info_versions_missing_dir_returns_empty(deps_mod, tmp_path):
    assert deps_mod._dist_info_versions(str(tmp_path / "nope")) == {}


# ------------------------------------------------------- idempotence guard ---


def test_pip_install_never_touches_already_satisfied_entry(
    deps_mod, tmp_path, monkeypatch
):
    """Suggestion 1: dest already has the exact version pip just
    resolved -> the entry must never enter the rmtree/replace path.
    Simulated by monkeypatching subprocess.run (no real pip call) and
    seeding both tmp and dest with the SAME numpy version + a marker
    file inside dest's package dir that would be destroyed by any
    rmtree/replace touch."""
    deps_dir = tmp_path / "deps"
    deps_dir.mkdir()
    _make_pkg_dir(deps_dir, "numpy", marker="ORIGINAL-LOCKED-COPY")
    _make_dist_info(deps_dir, "numpy", "2.4.4")

    def fake_run(cmd, **kwargs):
        # Locate --target value to build the "pip install" result.
        tmp_dir = Path(cmd[cmd.index("--target") + 1])
        _make_pkg_dir(tmp_dir, "numpy", marker="FRESH-DOWNLOAD")
        _make_dist_info(tmp_dir, "numpy", "2.4.4")  # same version as dest

        class _Result:
            returncode = 0
            stdout = ""
            stderr = ""

        return _Result()

    monkeypatch.setattr(deps_mod.subprocess, "run", fake_run)
    ok = deps_mod._pip_install(str(deps_dir), ["numpy==2.4.4"])
    assert ok is True
    # dest's original marker survives untouched -- never replaced.
    marker = (deps_dir / "numpy" / "__init__.py").read_text(encoding="utf-8")
    assert "ORIGINAL-LOCKED-COPY" in marker


def test_pip_install_replaces_entry_when_version_differs(
    deps_mod, tmp_path, monkeypatch
):
    """A genuine version bump DOES commit — idempotence guards only the
    already-satisfied case, it is not a blanket no-op."""
    deps_dir = tmp_path / "deps"
    deps_dir.mkdir()
    _make_pkg_dir(deps_dir, "numpy", marker="OLD")
    _make_dist_info(deps_dir, "numpy", "2.2.6")

    def fake_run(cmd, **kwargs):
        tmp_dir = Path(cmd[cmd.index("--target") + 1])
        _make_pkg_dir(tmp_dir, "numpy", marker="NEW")
        _make_dist_info(tmp_dir, "numpy", "2.4.4")

        class _Result:
            returncode = 0
            stdout = ""
            stderr = ""

        return _Result()

    monkeypatch.setattr(deps_mod.subprocess, "run", fake_run)
    ok = deps_mod._pip_install(str(deps_dir), ["numpy==2.4.4"])
    assert ok is True
    assert "NEW" in (deps_dir / "numpy" / "__init__.py").read_text(encoding="utf-8")
    assert (deps_dir / "numpy-2.4.4.dist-info").is_dir()
    # NOTE: the stale numpy-2.2.6.dist-info is orphaned, not cleaned up —
    # pre-existing behavior (unchanged by this fix): the commit loop only
    # ever touches entries present in tmp_dir's listing, and the OLD
    # dist-info's name isn't one of them. Not this issue's scope (#97 is
    # about not DESTROYING already-correct installs, not about pruning
    # stale dist-info directories).


# ------------------------------------------------- non-destructive commit ---


def test_pip_install_rollback_on_mid_commit_failure(deps_mod, tmp_path, monkeypatch):
    """Suggestion 2: simulate a PermissionError on os.replace for one
    entry (the locked-.pyd shape on Windows). Dest must be restored to
    its pre-call state, and tmp_dir must survive (NOT be deleted) so
    the fresh install isn't lost."""
    deps_dir = tmp_path / "deps"
    deps_dir.mkdir()
    _make_pkg_dir(deps_dir, "numpy", marker="ORIGINAL")
    _make_dist_info(
        deps_dir, "numpy", "2.2.6"
    )  # differs from tmp -> forces commit attempt

    captured_tmp_dir = {}

    def fake_run(cmd, **kwargs):
        tmp_dir = Path(cmd[cmd.index("--target") + 1])
        captured_tmp_dir["path"] = tmp_dir
        _make_pkg_dir(tmp_dir, "numpy", marker="FRESH")
        _make_dist_info(tmp_dir, "numpy", "2.4.4")

        class _Result:
            returncode = 0
            stdout = ""
            stderr = ""

        return _Result()

    monkeypatch.setattr(deps_mod.subprocess, "run", fake_run)

    real_replace = os.replace

    def flaky_replace(src, dst):
        # Fail only the FORWARD move (tmp_dir's fresh copy -> dest).
        # The rollback direction (backup -> dest) must succeed, exactly
        # as it would on a real Windows box once the process holding
        # the lock releases it — this test isolates "the forward commit
        # failed", not "the filesystem is permanently unwritable".
        if str(src).endswith(os.path.join("numpy")) and ".tmp-" in str(src):
            raise PermissionError(
                "[WinError 5] Access is denied (simulated locked .pyd)"
            )
        return real_replace(src, dst)

    monkeypatch.setattr(deps_mod.os, "replace", flaky_replace)

    ok = deps_mod._pip_install(str(deps_dir), ["numpy==2.4.4"])

    assert ok is False
    # Dest restored to its ORIGINAL content -- rollback succeeded.
    assert (deps_dir / "numpy").is_dir()
    assert "ORIGINAL" in (deps_dir / "numpy" / "__init__.py").read_text(
        encoding="utf-8"
    )
    assert (deps_dir / "numpy-2.2.6.dist-info").is_dir()
    # tmp_dir preserved for manual recovery / retry -- the exact bug
    # (old `finally: shutil.rmtree(tmp_dir)`) destroyed this.
    assert captured_tmp_dir["path"].exists()
    assert (captured_tmp_dir["path"] / "numpy" / "__init__.py").exists()


def test_pip_install_no_backup_leaked_on_success(deps_mod, tmp_path, monkeypatch):
    """A successful commit leaves no ``*.bak-<pid>`` residue behind."""
    deps_dir = tmp_path / "deps"
    deps_dir.mkdir()
    _make_pkg_dir(deps_dir, "numpy", marker="OLD")
    _make_dist_info(deps_dir, "numpy", "2.2.6")

    def fake_run(cmd, **kwargs):
        tmp_dir = Path(cmd[cmd.index("--target") + 1])
        _make_pkg_dir(tmp_dir, "numpy", marker="NEW")
        _make_dist_info(tmp_dir, "numpy", "2.4.4")

        class _Result:
            returncode = 0
            stdout = ""
            stderr = ""

        return _Result()

    monkeypatch.setattr(deps_mod.subprocess, "run", fake_run)
    assert deps_mod._pip_install(str(deps_dir), ["numpy==2.4.4"]) is True
    leftovers = [p for p in deps_dir.iterdir() if ".bak-" in p.name]
    assert leftovers == []


def test_pip_install_failure_preserves_tmp_dir_and_returns_false(
    deps_mod, tmp_path, monkeypatch
):
    """pip itself failing (network/proxy/PEP668) is a distinct path from
    a commit failure -- must still surface False and not raise."""
    deps_dir = tmp_path / "deps"
    deps_dir.mkdir()

    def fake_run(cmd, **kwargs):
        class _Result:
            returncode = 1
            stdout = ""
            stderr = "ERROR: Could not find a version that satisfies numpy==2.4.4"

        return _Result()

    monkeypatch.setattr(deps_mod.subprocess, "run", fake_run)
    ok = deps_mod._pip_install(str(deps_dir), ["numpy==2.4.4"])
    assert ok is False


# --------------------------------------------------------------- stamp/lock ---


def test_stamp_round_trip(deps_mod, tmp_path):
    deps_dir = tmp_path / "deps"
    deps_dir.mkdir()
    pins = ["fastmcp==3.2.4", "numpy==2.4.4"]
    assert deps_mod._pins_satisfied(str(deps_dir), "base", pins) is False
    deps_mod._write_stamp(str(deps_dir), "base", pins)
    assert deps_mod._pins_satisfied(str(deps_dir), "base", pins) is True


def test_stamp_mismatch_on_pin_change_self_heals(deps_mod, tmp_path):
    """A pin bump (new Cortex release) invalidates the stamp -- 'un
    stamp par version de pin suffit' means exact match required."""
    deps_dir = tmp_path / "deps"
    deps_dir.mkdir()
    deps_mod._write_stamp(str(deps_dir), "base", ["numpy==2.4.4"])
    assert deps_mod._pins_satisfied(str(deps_dir), "base", ["numpy==2.5.0"]) is False


def test_stamp_corrupt_file_treated_as_absent(deps_mod, tmp_path):
    deps_dir = tmp_path / "deps"
    deps_dir.mkdir()
    Path(deps_mod._stamp_path(str(deps_dir), "base")).write_text(
        "not json{", encoding="utf-8"
    )
    assert deps_mod._pins_satisfied(str(deps_dir), "base", ["numpy==2.4.4"]) is False


def test_ensure_deps_skips_pip_entirely_when_stamp_matches(
    deps_mod, tmp_path, monkeypatch
):
    """The hot-path fast path: a valid stamp means zero _pip_install
    calls and zero _importable calls (issue #97 suggestion 4 — no
    torch/numpy import just to answer 'is it installed')."""
    deps_dir = tmp_path / "deps"
    deps_dir.mkdir()
    pins = [spec for _name, spec in deps_mod._BASE_PACKAGES]
    deps_mod._write_stamp(str(deps_dir), "base", pins)

    calls = {"pip_install": 0, "importable": 0}
    monkeypatch.setattr(
        deps_mod,
        "_pip_install",
        lambda *a, **k: calls.__setitem__("pip_install", 1) or True,
    )
    monkeypatch.setattr(
        deps_mod,
        "_importable",
        lambda *a, **k: (
            calls.__setitem__("importable", calls["importable"] + 1) or True
        ),
    )
    deps_mod.ensure_deps(str(deps_dir))
    assert calls == {"pip_install": 0, "importable": 0}


def test_ensure_deps_installs_and_stamps_when_missing(deps_mod, tmp_path, monkeypatch):
    deps_dir = tmp_path / "deps"
    deps_dir.mkdir()

    installed = {"called": False}

    def fake_importable(name, _deps_dir):
        return installed["called"]  # False before install, True after

    def fake_pip_install(_deps_dir, _packages):
        installed["called"] = True
        return True

    monkeypatch.setattr(deps_mod, "_importable", fake_importable)
    monkeypatch.setattr(deps_mod, "_pip_install", fake_pip_install)
    deps_mod.ensure_deps(str(deps_dir))
    pins = [spec for _name, spec in deps_mod._BASE_PACKAGES]
    assert deps_mod._pins_satisfied(str(deps_dir), "base", pins) is True


def test_deps_lock_mutual_exclusion(deps_mod, tmp_path):
    deps_dir = str(tmp_path / "deps")
    os.makedirs(deps_dir, exist_ok=True)
    with deps_mod._deps_lock(deps_dir) as acquired_outer:
        assert acquired_outer is True
        assert os.path.isdir(f"{deps_dir}.lock")
    # Released after the context exits.
    assert not os.path.isdir(f"{deps_dir}.lock")


def test_deps_lock_steals_stale_lock(deps_mod, tmp_path, monkeypatch):
    deps_dir = str(tmp_path / "deps")
    os.makedirs(deps_dir, exist_ok=True)
    lock_dir = f"{deps_dir}.lock"
    os.makedirs(lock_dir)
    holder = os.path.join(lock_dir, "holder")
    with open(holder, "w", encoding="utf-8") as fh:
        fh.write("99999 0")
    # Force the age computation to look ancient without a real sleep.
    monkeypatch.setattr(deps_mod.os.path, "getmtime", lambda _p: 0.0)
    monkeypatch.setattr(deps_mod.time, "time", lambda: 10_000.0)
    with deps_mod._deps_lock(deps_dir) as acquired:
        assert acquired is True


def test_entry_dist_key_strips_dist_info_suffix(deps_mod):
    assert deps_mod._entry_dist_key("numpy-2.4.4.dist-info") == "numpy"
    assert deps_mod._entry_dist_key("numpy") == "numpy"
    assert (
        deps_mod._entry_dist_key("pydantic_settings-2.14.0.dist-info")
        == "pydantic_settings"
    )
