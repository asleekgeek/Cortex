"""Tests for the write-class classification choke point (M-D2/M-D3, 7.1).

``classify_write_class`` is the single contract 7.4's future explicit
``write_class`` column re-sources from — these tests pin the taxonomy
table from ``scratchpad/memoire-qui-comprend-design.md`` §M-D2.
"""

from __future__ import annotations

from mcp_server.core.write_class import (
    ALL_WRITE_CLASSES,
    AUTO,
    AUTO_SOURCE_VALUES,
    DELIBERATE,
    DERIVED,
    MECHANICAL,
    classify_write_class,
)


class TestAutoClass:
    def test_post_tool_capture_is_auto(self):
        assert classify_write_class({"source": "post_tool_capture"}) == AUTO

    def test_bare_source_string_works(self):
        assert classify_write_class("post_tool_capture") == AUTO


class TestDerivedClass:
    def test_consolidation_is_derived(self):
        # memify_derive's exact source value (handlers/consolidation/
        # memify_derive.py:245).
        assert classify_write_class({"source": "consolidation"}) == DERIVED

    def test_cls_consolidation_is_derived(self):
        # CLS semantic promotion — measured DB source, 59 rows dev DB.
        assert classify_write_class({"source": "cls-consolidation"}) == DERIVED

    def test_cls_prefix_family_is_derived(self):
        assert classify_write_class({"source": "cls-anything-else"}) == DERIVED


class TestMechanicalClass:
    def test_codebase_analyze_is_mechanical(self):
        assert classify_write_class({"source": "codebase_analyze"}) == MECHANICAL

    def test_seed_project_is_mechanical(self):
        assert classify_write_class({"source": "seed_project"}) == MECHANICAL

    def test_ingest_codebase_is_mechanical(self):
        assert classify_write_class({"source": "ingest_codebase"}) == MECHANICAL

    def test_backfill_prefix_family_is_mechanical(self):
        # Measured DB source values: "backfill:-Users-cdeust-Developments-*"
        # (one per scanned directory).
        assert (
            classify_write_class({"source": "backfill:-Users-x-Developments-Cortex"})
            == MECHANICAL
        )


class TestDeliberateClass:
    def test_feature_source_is_deliberate(self):
        assert classify_write_class({"source": "feature"}) == DELIBERATE

    def test_lesson_source_is_deliberate(self):
        assert classify_write_class({"source": "lesson"}) == DELIBERATE

    def test_bug_fix_source_is_deliberate(self):
        assert classify_write_class({"source": "bug-fix"}) == DELIBERATE

    def test_empty_source_defaults_deliberate_not_auto(self):
        """Safe default: unclassified content is never assumed to be
        flood/noise, so it is never subject to fold-style regulation."""
        assert classify_write_class({"source": ""}) == DELIBERATE
        assert classify_write_class({}) == DELIBERATE
        assert classify_write_class(None) == DELIBERATE

    def test_unknown_source_defaults_deliberate(self):
        assert classify_write_class({"source": "some-future-source-kind"}) == DELIBERATE


class TestExplicitColumnForwardCompat:
    def test_explicit_write_class_wins_over_source(self):
        """7.4 forward-compat: an explicit write_class value short-circuits
        source-based inference — the future explicit-column fast path."""
        memory = {"source": "post_tool_capture", "write_class": "deliberate"}
        assert classify_write_class(memory) == DELIBERATE

    def test_invalid_explicit_write_class_falls_back_to_source(self):
        memory = {"source": "post_tool_capture", "write_class": "not-a-real-class"}
        assert classify_write_class(memory) == AUTO


class TestTaxonomyInvariants:
    def test_all_classes_enumerated(self):
        assert set(ALL_WRITE_CLASSES) == {AUTO, DELIBERATE, DERIVED, MECHANICAL}

    def test_auto_source_values_nonempty_and_sorted(self):
        assert AUTO_SOURCE_VALUES == tuple(sorted(AUTO_SOURCE_VALUES))
        assert "post_tool_capture" in AUTO_SOURCE_VALUES

    def test_every_class_reachable(self):
        """Sanity: at least one real source value maps to each class."""
        seen = {
            classify_write_class({"source": s})
            for s in (
                "post_tool_capture",
                "feature",
                "consolidation",
                "codebase_analyze",
            )
        }
        assert seen == {AUTO, DELIBERATE, DERIVED, MECHANICAL}
