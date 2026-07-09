"""Tests for mcp_server.core.memory_rules — neuro-symbolic rules engine."""

import pytest

from mcp_server.core.memory_rules import (
    parse_condition,
    parse_action,
    get_field_value,
    evaluate_condition,
    apply_rules,
    validate_rule,
)


class TestParseCondition:
    def test_greater_than(self):
        assert parse_condition("importance > 0.7") == ("importance", ">", "0.7")

    def test_less_than(self):
        assert parse_condition("heat < 0.1") == ("heat", "<", "0.1")

    def test_equals(self):
        assert parse_condition("domain == testing") == ("domain", "==", "testing")

    def test_not_equals(self):
        assert parse_condition("store_type != semantic") == (
            "store_type",
            "!=",
            "semantic",
        )

    def test_contains(self):
        assert parse_condition("tag contains architecture") == (
            "tag",
            "contains",
            "architecture",
        )

    def test_not_contains(self):
        assert parse_condition("content not_contains password") == (
            "content",
            "not_contains",
            "password",
        )

    def test_matches(self):
        assert parse_condition("directory_context matches /project/*") == (
            "directory_context",
            "matches",
            "/project/*",
        )

    def test_gte(self):
        assert parse_condition("confidence >= 0.8") == ("confidence", ">=", "0.8")

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            parse_condition("no operator here")


class TestParseAction:
    def test_filter(self):
        assert parse_action("filter") == ("filter", 0.0)

    def test_boost(self):
        assert parse_action("boost:0.3") == ("boost", 0.3)

    def test_penalty(self):
        assert parse_action("penalty:0.2") == ("penalty", 0.2)

    def test_tag(self):
        assert parse_action("tag:review") == ("tag", "review")

    def test_tag_empty_name_raises(self):
        with pytest.raises(ValueError):
            parse_action("tag:")

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            parse_action("unknown_action")


class TestGetFieldValue:
    def test_direct_field(self):
        mem = {"heat": 0.8, "domain": "testing"}
        assert get_field_value(mem, "heat") == 0.8

    def test_tags_field(self):
        mem = {"tags": ["python", "core"]}
        assert get_field_value(mem, "tag") == ["python", "core"]

    def test_tag_key_value(self):
        mem = {"tags": ["language:python", "priority:high"]}
        assert get_field_value(mem, "language") == "python"

    def test_missing_field(self):
        assert get_field_value({}, "nonexistent") is None


class TestEvaluateCondition:
    def test_numeric_greater(self):
        mem = {"importance": 0.8}
        assert evaluate_condition("importance > 0.5", mem) is True
        assert evaluate_condition("importance > 0.9", mem) is False

    def test_numeric_less(self):
        mem = {"heat": 0.3}
        assert evaluate_condition("heat < 0.5", mem) is True

    def test_equality(self):
        mem = {"domain": "testing"}
        assert evaluate_condition("domain == testing", mem) is True
        assert evaluate_condition("domain == production", mem) is False

    def test_not_equals(self):
        mem = {"store_type": "episodic"}
        assert evaluate_condition("store_type != semantic", mem) is True

    def test_contains_string(self):
        mem = {"content": "Fix the memory leak"}
        assert evaluate_condition("content contains memory", mem) is True
        assert evaluate_condition("content contains database", mem) is False

    def test_contains_list(self):
        mem = {"tags": ["python", "architecture"]}
        assert evaluate_condition("tag contains architecture", mem) is True
        assert evaluate_condition("tag contains java", mem) is False

    def test_not_contains(self):
        mem = {"content": "public information"}
        assert evaluate_condition("content not_contains password", mem) is True
        assert evaluate_condition("content not_contains public", mem) is False

    def test_matches_glob(self):
        mem = {"directory_context": "/project/src/core"}
        assert evaluate_condition("directory_context matches /project/*", mem) is True
        assert evaluate_condition("directory_context matches /other/*", mem) is False

    def test_none_field_numeric(self):
        mem = {}
        assert evaluate_condition("importance > 0.5", mem) is False  # None → 0.0

    def test_unparseable_never_matches(self):
        """Fail-safe read-side default (RCA fix/add-rule-memory-rules-drift):
        an unparseable condition must never match, so a legacy malformed
        hard rule degrades to a no-op instead of excluding every memory."""
        assert evaluate_condition("gibberish", {}) is False


class TestApplyRules:
    def test_hard_filter_excludes_matches(self):
        """RCA fix/add-rule-memory-rules-drift: a hard 'filter' rule must
        EXCLUDE memories that satisfy the condition, not keep only them —
        the condition names what you want gone (e.g. 'tag contains
        deprecated'), matching add_rule's documented semantics."""
        memories = [
            {"content": "important", "importance": 0.9, "score": 1.0},
            {"content": "trivial", "importance": 0.2, "score": 0.8},
        ]
        rules = [
            {"rule_type": "hard", "condition": "importance > 0.5", "action": "filter"}
        ]
        result = apply_rules(memories, rules)
        assert len(result) == 1
        assert result[0]["content"] == "trivial"

    def test_hard_filter_excludes_by_tag(self):
        """Canonical use case from add_rule's docstring: never surface
        deprecated memories."""
        memories = [
            {"content": "current", "tags": ["core"], "score": 1.0},
            {"content": "old", "tags": ["deprecated"], "score": 0.9},
        ]
        rules = [
            {
                "rule_type": "hard",
                "condition": "tag contains deprecated",
                "action": "filter",
            }
        ]
        result = apply_rules(memories, rules)
        assert len(result) == 1
        assert result[0]["content"] == "current"

    def test_soft_boost(self):
        memories = [
            {"content": "a", "importance": 0.9, "score": 0.5},
            {"content": "b", "importance": 0.3, "score": 0.8},
        ]
        rules = [
            {
                "rule_type": "soft",
                "condition": "importance > 0.5",
                "action": "boost:0.5",
            }
        ]
        result = apply_rules(memories, rules)
        # "a" should now have score 1.0 and rank first
        assert result[0]["content"] == "a"
        assert result[0]["score"] == 1.0

    def test_soft_penalty(self):
        memories = [
            {"content": "a", "importance": 0.9, "score": 0.8},
            {"content": "b", "importance": 0.3, "score": 0.7},
        ]
        rules = [
            {
                "rule_type": "soft",
                "condition": "importance > 0.5",
                "action": "penalty:0.5",
            }
        ]
        result = apply_rules(memories, rules)
        # "a" penalized to 0.3, "b" stays at 0.7
        assert result[0]["content"] == "b"

    def test_empty_rules(self):
        memories = [{"content": "x", "score": 1.0}]
        assert apply_rules(memories, []) == memories

    def test_multiple_rules(self):
        memories = [
            {"content": "a", "heat": 0.9, "importance": 0.8, "score": 1.0},
            {"content": "b", "heat": 0.1, "importance": 0.2, "score": 0.9},
            {"content": "c", "heat": 0.5, "importance": 0.6, "score": 0.5},
        ]
        rules = [
            # Excludes low-heat (stale) memories: "b" (heat 0.1) is dropped.
            {"rule_type": "hard", "condition": "heat < 0.2", "action": "filter"},
            {
                "rule_type": "soft",
                "condition": "importance > 0.7",
                "action": "boost:0.5",
            },
        ]
        result = apply_rules(memories, rules)
        assert len(result) == 2  # "b" excluded (low heat)
        assert result[0]["content"] == "a"  # Boosted (importance 0.8 > 0.7)

    def test_tag_rule_attaches_tag_to_matches_only(self):
        memories = [
            {"content": "todo item", "score": 1.0},
            {"content": "done item", "score": 0.9},
        ]
        rules = [
            {
                "rule_type": "tag",
                "condition": "content contains todo",
                "action": "tag:review",
            }
        ]
        result = apply_rules(memories, rules)
        assert len(result) == 2  # tag rules never change membership
        todo = next(m for m in result if m["content"] == "todo item")
        done = next(m for m in result if m["content"] == "done item")
        assert todo["tags"] == ["review"]
        assert "tags" not in done or done["tags"] == []

    def test_tag_rule_dedupes(self):
        memories = [{"content": "x", "tags": ["review"], "score": 1.0}]
        rules = [
            {
                "rule_type": "tag",
                "condition": "content contains x",
                "action": "tag:review",
            }
        ]
        result = apply_rules(memories, rules)
        assert result[0]["tags"] == ["review"]  # no duplicate append


class TestValidateRule:
    def test_valid_rule(self):
        errors = validate_rule("soft", "importance > 0.7", "boost:0.3")
        assert errors == []

    def test_invalid_type(self):
        errors = validate_rule("invalid", "importance > 0.7", "boost:0.3")
        assert len(errors) >= 1

    def test_invalid_condition(self):
        errors = validate_rule("soft", "no_operator", "boost:0.3")
        assert len(errors) >= 1

    def test_invalid_action(self):
        errors = validate_rule("soft", "importance > 0.7", "explode")
        assert len(errors) >= 1

    def test_hard_rule_must_filter(self):
        errors = validate_rule("hard", "importance > 0.7", "boost:0.3")
        assert any("filter" in e for e in errors)

    def test_valid_hard_rule(self):
        errors = validate_rule("hard", "tag contains deprecated", "filter")
        assert errors == []

    def test_valid_tag_rule(self):
        errors = validate_rule("tag", "content contains TODO", "tag:review")
        assert errors == []

    def test_tag_rule_must_use_tag_action(self):
        errors = validate_rule("tag", "content contains TODO", "filter")
        assert any("tag:NAME" in e for e in errors)

    def test_soft_rule_must_use_boost_or_penalty(self):
        errors = validate_rule("soft", "importance > 0.7", "filter")
        assert any("boost" in e or "penalty" in e for e in errors)

    def test_legacy_add_rule_shorthand_rejected(self):
        """The pre-fix add_rule docstring advertised 'tag:deprecated' /
        'exclude' as valid syntax; the engine has never parsed it. This
        must now be rejected outright at validate_rule (write-time gate)
        rather than silently stored as an inert rule."""
        errors = validate_rule("hard", "tag:deprecated", "exclude")
        assert len(errors) >= 1
