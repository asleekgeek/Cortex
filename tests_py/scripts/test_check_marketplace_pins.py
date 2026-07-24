"""Tests for scripts/check_marketplace_pins.py — the pin-staleness gate (#179)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "check_marketplace_pins",
    Path(__file__).resolve().parents[2] / "scripts" / "check_marketplace_pins.py",
)
cmp_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cmp_mod)


class TestParseSemver:
    def test_v_prefix_and_bare(self):
        assert cmp_mod.parse_semver("v2.34.0") == (2, 34, 0)
        assert cmp_mod.parse_semver("2.7.1") == (2, 7, 1)

    def test_non_semver_returns_none(self):
        assert cmp_mod.parse_semver("release-candidate") is None
        assert cmp_mod.parse_semver("2.34") is None

    def test_numeric_not_lexicographic(self):
        # 2.9.0 < 2.10.0 numerically; lexicographic comparison would invert this.
        assert cmp_mod.parse_semver("2.9.0") < cmp_mod.parse_semver("2.10.0")


class TestPinBehindRelease:
    def test_stale_pin_flagged(self):
        issue = cmp_mod.check_github_pin(
            "p", "o/r", "2.29.0", fetch=lambda repo: "v2.34.0"
        )
        assert issue is not None and "PIN_BEHIND_RELEASE" in issue

    def test_current_pin_passes(self):
        assert (
            cmp_mod.check_github_pin("p", "o/r", "2.34.0", fetch=lambda repo: "v2.34.0")
            is None
        )

    def test_pin_ahead_passes(self):
        # Pin ahead of the latest release (pre-release pin) is not a staleness failure.
        assert (
            cmp_mod.check_github_pin("p", "o/r", "2.35.0", fetch=lambda repo: "v2.34.0")
            is None
        )

    def test_unparseable_tag_reported_not_crashed(self):
        issue = cmp_mod.check_github_pin(
            "p", "o/r", "2.34.0", fetch=lambda repo: "nightly"
        )
        assert issue is not None and "UNPARSEABLE" in issue


class TestSelfPinMismatch:
    def test_mismatch_flagged(self, tmp_path):
        plugin_dir = tmp_path / "plug" / ".claude-plugin"
        plugin_dir.mkdir(parents=True)
        (plugin_dir / "plugin.json").write_text(json.dumps({"version": "4.16.0"}))
        issue = cmp_mod.check_self_pin("plug", "plug", "4.15.0", tmp_path)
        assert issue is not None and "SELF_PIN_MISMATCH" in issue

    def test_match_passes(self, tmp_path):
        plugin_dir = tmp_path / "plug" / ".claude-plugin"
        plugin_dir.mkdir(parents=True)
        (plugin_dir / "plugin.json").write_text(json.dumps({"version": "4.16.0"}))
        assert cmp_mod.check_self_pin("plug", "plug", "4.16.0", tmp_path) is None

    def test_manifestless_local_dir_passes(self, tmp_path):
        (tmp_path / "shim").mkdir()
        assert cmp_mod.check_self_pin("shim", "shim", "4.15.0", tmp_path) is None
