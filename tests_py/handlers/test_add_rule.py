"""Tests for mcp_server.handlers.add_rule — neuro-symbolic rule persistence.

Contract under test (from add_rule.py). condition/action use the grammar
mcp_server.core.memory_rules parses (the single grammar authority — see
that module's docstring); this is NOT the pre-fix 'matcher:value' /
'exclude' shorthand, which no parser ever implemented (RCA
fix/add-rule-memory-rules-drift).
  POST-1  Success: returns {created: True, rule_id: int, rule_type, scope,
          scope_value, condition, action, priority} — all fields present, all
          values echo the caller's inputs.
  POST-2  rule_id is a positive integer (persisted row id from memory_rules).
  POST-3  Defaults: rule_type defaults to "soft", scope defaults to "global",
          priority defaults to 0, scope_value defaults to None.
  POST-4  domain/directory scope requires scope_value; returns
          {created: False, reason: ...} when scope_value is absent.
  POST-5  Missing condition returns {created: False, reason: ...}.
  POST-6  Missing action returns {created: False, reason: ...}.
  POST-7  Invalid rule_type returns {created: False, reason: ...}.
  POST-8  Invalid scope returns {created: False, reason: ...}.
  POST-9  Hard rule: rule_type="hard", action="filter" round-trips correctly.
  POST-10 Tag rule: rule_type="tag", action="tag:review" round-trips correctly.
  POST-11 Priority bounds: priority integer is preserved in the response.
  POST-12 No-args call (None) treated as empty dict — validated, not crashed.
  POST-13 Grammar-invalid condition/action (parseable structurally but not
          by memory_rules, or mechanism mismatch) is rejected by
          validate_rule at write time: {created: False, reason: ...}.
"""

from __future__ import annotations

import pytest


# ── helpers ───────────────────────────────────────────────────────────────────


def _minimal_args(**overrides) -> dict:
    """Return the minimum valid args, with optional field overrides.

    Uses the default rule_type ("soft"), so action must be a valid soft
    action ('boost:N' / 'penalty:N') under memory_rules.validate_rule.
    """
    base = {"condition": "tag contains deprecated", "action": "boost:0.1"}
    base.update(overrides)
    return base


# ── POST-1 through POST-3: success path, output shape, defaults ───────────────


class TestAddRuleSuccess:
    @pytest.mark.asyncio
    async def test_success_output_shape(self):
        """POST-1: all required keys present on success."""
        from mcp_server.handlers.add_rule import handler

        result = await handler(_minimal_args())

        assert result["created"] is True
        for key in (
            "rule_id",
            "rule_type",
            "scope",
            "scope_value",
            "condition",
            "action",
            "priority",
        ):
            assert key in result, f"missing key in success response: {key}"

    @pytest.mark.asyncio
    async def test_rule_id_is_positive_integer(self):
        """POST-2: rule_id is a positive integer (real persisted row id)."""
        from mcp_server.handlers.add_rule import handler

        result = await handler(_minimal_args())

        assert result["created"] is True
        assert isinstance(result["rule_id"], int)
        assert result["rule_id"] > 0

    @pytest.mark.asyncio
    async def test_defaults_applied(self):
        """POST-3: rule_type, scope, priority, scope_value default correctly."""
        from mcp_server.handlers.add_rule import handler

        result = await handler(_minimal_args())

        assert result["rule_type"] == "soft"
        assert result["scope"] == "global"
        assert result["priority"] == 0
        assert result["scope_value"] is None

    @pytest.mark.asyncio
    async def test_inputs_echoed_in_response(self):
        """POST-1: every caller-supplied field is echoed back verbatim."""
        from mcp_server.handlers.add_rule import handler

        args = {
            "condition": "content contains secret",
            "action": "boost:0.3",
            "rule_type": "soft",
            "scope": "global",
            "priority": 10,
        }
        result = await handler(args)

        assert result["created"] is True
        assert result["condition"] == "content contains secret"
        assert result["action"] == "boost:0.3"
        assert result["rule_type"] == "soft"
        assert result["scope"] == "global"
        assert result["priority"] == 10

    @pytest.mark.asyncio
    async def test_successive_inserts_produce_distinct_ids(self):
        """POST-2: two separate rules get distinct rule_ids — each is persisted."""
        from mcp_server.handlers.add_rule import handler

        r1 = await handler(_minimal_args(condition="tag contains old"))
        r2 = await handler(_minimal_args(condition="tag contains new"))

        assert r1["created"] is True
        assert r2["created"] is True
        assert r1["rule_id"] != r2["rule_id"]


# ── POST-9: hard rule ─────────────────────────────────────────────────────────


class TestAddRuleHardType:
    @pytest.mark.asyncio
    async def test_hard_rule_round_trips(self):
        """POST-9: rule_type=hard, action=filter stored and echoed correctly."""
        from mcp_server.handlers.add_rule import handler

        result = await handler(
            {
                "condition": "tag contains deprecated",
                "action": "filter",
                "rule_type": "hard",
            }
        )

        assert result["created"] is True
        assert result["rule_type"] == "hard"
        assert result["action"] == "filter"


# ── POST-10: tag rule ─────────────────────────────────────────────────────────


class TestAddRuleTagType:
    @pytest.mark.asyncio
    async def test_tag_rule_round_trips(self):
        """POST-10: rule_type=tag, action=tag:<name> stored and echoed correctly."""
        from mcp_server.handlers.add_rule import handler

        result = await handler(
            {
                "condition": "content contains TODO",
                "action": "tag:review",
                "rule_type": "tag",
            }
        )

        assert result["created"] is True
        assert result["rule_type"] == "tag"
        assert result["action"] == "tag:review"


# ── POST-11: priority ─────────────────────────────────────────────────────────


class TestAddRulePriority:
    @pytest.mark.asyncio
    async def test_custom_priority_preserved(self):
        """POST-11: supplied priority integer survives round-trip."""
        from mcp_server.handlers.add_rule import handler

        result = await handler(_minimal_args(priority=50))

        assert result["created"] is True
        assert result["priority"] == 50

    @pytest.mark.asyncio
    async def test_negative_priority_preserved(self):
        """POST-11: negative priority (within -100..100) survives round-trip."""
        from mcp_server.handlers.add_rule import handler

        result = await handler(_minimal_args(priority=-10))

        assert result["created"] is True
        assert result["priority"] == -10


# ── POST-3 / scope_value: domain scope ───────────────────────────────────────


class TestAddRuleDomainScope:
    @pytest.mark.asyncio
    async def test_domain_scope_with_scope_value(self):
        """Scope=domain with scope_value stored and echoed."""
        from mcp_server.handlers.add_rule import handler

        result = await handler(
            {
                "condition": "tag contains old",
                "action": "penalty:0.5",
                "rule_type": "soft",
                "scope": "domain",
                "scope_value": "auth-service",
            }
        )

        assert result["created"] is True
        assert result["scope"] == "domain"
        assert result["scope_value"] == "auth-service"

    @pytest.mark.asyncio
    async def test_directory_scope_with_scope_value(self):
        """Scope=directory with scope_value stored and echoed."""
        from mcp_server.handlers.add_rule import handler

        result = await handler(
            {
                "condition": "source == import",
                "action": "filter",
                "rule_type": "hard",
                "scope": "directory",
                "scope_value": "/Users/alice/code/cortex",
            }
        )

        assert result["created"] is True
        assert result["scope"] == "directory"
        assert result["scope_value"] == "/Users/alice/code/cortex"


# ── POST-4 through POST-8: validation / error paths ──────────────────────────


class TestAddRuleValidationErrors:
    @pytest.mark.asyncio
    async def test_missing_condition_returns_error(self):
        """POST-5: no condition → created=False with a reason."""
        from mcp_server.handlers.add_rule import handler

        result = await handler({"action": "exclude"})

        assert result["created"] is False
        assert "reason" in result
        assert result["reason"]  # non-empty string

    @pytest.mark.asyncio
    async def test_empty_condition_returns_error(self):
        """POST-5: blank condition string is treated as missing."""
        from mcp_server.handlers.add_rule import handler

        result = await handler({"condition": "   ", "action": "exclude"})

        assert result["created"] is False
        assert "reason" in result

    @pytest.mark.asyncio
    async def test_missing_action_returns_error(self):
        """POST-6: no action → created=False with a reason."""
        from mcp_server.handlers.add_rule import handler

        result = await handler({"condition": "tag:old"})

        assert result["created"] is False
        assert "reason" in result
        assert result["reason"]

    @pytest.mark.asyncio
    async def test_invalid_rule_type_returns_error(self):
        """POST-7: rule_type not in {hard,soft,tag} → created=False."""
        from mcp_server.handlers.add_rule import handler

        result = await handler(
            {
                "condition": "tag:old",
                "action": "exclude",
                "rule_type": "unknown_type",
            }
        )

        assert result["created"] is False
        assert "reason" in result

    @pytest.mark.asyncio
    async def test_invalid_scope_returns_error(self):
        """POST-8: scope not in {global,domain,directory} → created=False."""
        from mcp_server.handlers.add_rule import handler

        result = await handler(
            {
                "condition": "tag:old",
                "action": "exclude",
                "scope": "cluster",
            }
        )

        assert result["created"] is False
        assert "reason" in result

    @pytest.mark.asyncio
    async def test_domain_scope_without_scope_value_returns_error(self):
        """POST-4: scope=domain but no scope_value → created=False."""
        from mcp_server.handlers.add_rule import handler

        result = await handler(
            {
                "condition": "tag:old",
                "action": "exclude",
                "scope": "domain",
            }
        )

        assert result["created"] is False
        assert "reason" in result
        assert (
            "scope_value" in result["reason"].lower()
            or "scope" in result["reason"].lower()
        )

    @pytest.mark.asyncio
    async def test_directory_scope_without_scope_value_returns_error(self):
        """POST-4: scope=directory but no scope_value → created=False."""
        from mcp_server.handlers.add_rule import handler

        result = await handler(
            {
                "condition": "tag:old",
                "action": "exclude",
                "scope": "directory",
            }
        )

        assert result["created"] is False
        assert "reason" in result

    @pytest.mark.asyncio
    async def test_none_args_does_not_crash(self):
        """POST-12: handler(None) treated as empty dict, returns validation error."""
        from mcp_server.handlers.add_rule import handler

        result = await handler(None)

        # Must not raise; must be a well-formed error dict
        assert isinstance(result, dict)
        assert "created" in result
        assert result["created"] is False


# ── Validate validation helper directly ───────────────────────────────────────


class TestValidateRuleArgs:
    """Unit tests for _validate_rule_args — pure function, no I/O."""

    def test_valid_args_returns_none(self):
        from mcp_server.handlers.add_rule import _validate_rule_args

        err = _validate_rule_args(
            {"condition": "tag contains old", "action": "boost:0.1"}
        )
        assert err is None

    def test_missing_condition_returns_dict(self):
        from mcp_server.handlers.add_rule import _validate_rule_args

        err = _validate_rule_args({"action": "exclude"})
        assert err is not None
        assert err["created"] is False

    def test_missing_action_returns_dict(self):
        from mcp_server.handlers.add_rule import _validate_rule_args

        err = _validate_rule_args({"condition": "tag:old"})
        assert err is not None
        assert err["created"] is False

    def test_invalid_rule_type(self):
        from mcp_server.handlers.add_rule import _validate_rule_args

        err = _validate_rule_args(
            {
                "condition": "tag:old",
                "action": "exclude",
                "rule_type": "mega",
            }
        )
        assert err is not None
        assert err["created"] is False

    def test_invalid_scope(self):
        from mcp_server.handlers.add_rule import _validate_rule_args

        err = _validate_rule_args(
            {
                "condition": "tag:old",
                "action": "exclude",
                "scope": "cluster",
            }
        )
        assert err is not None
        assert err["created"] is False

    def test_domain_scope_missing_scope_value(self):
        from mcp_server.handlers.add_rule import _validate_rule_args

        err = _validate_rule_args(
            {
                "condition": "tag:old",
                "action": "exclude",
                "scope": "domain",
            }
        )
        assert err is not None
        assert err["created"] is False

    def test_domain_scope_with_scope_value_ok(self):
        from mcp_server.handlers.add_rule import _validate_rule_args

        err = _validate_rule_args(
            {
                "condition": "tag contains old",
                "action": "boost:0.1",
                "scope": "domain",
                "scope_value": "auth",
            }
        )
        assert err is None


# ── POST-13: grammar validation wired via validate_rule ───────────────────────


class TestAddRuleGrammarValidation:
    """RCA fix/add-rule-memory-rules-drift: add_rule must call
    memory_rules.validate_rule and reject rules whose condition/action do
    not parse under the engine's grammar, instead of silently persisting an
    inert rule."""

    @pytest.mark.asyncio
    async def test_unparseable_condition_rejected(self):
        from mcp_server.handlers.add_rule import handler

        result = await handler({"condition": "no_operator_here", "action": "boost:0.3"})

        assert result["created"] is False
        assert "reason" in result

    @pytest.mark.asyncio
    async def test_legacy_matcher_value_syntax_rejected(self):
        """The pre-fix docstring's 'tag:deprecated' / 'exclude' shorthand
        must now be rejected — it was never parseable by the engine."""
        from mcp_server.handlers.add_rule import handler

        result = await handler(
            {"condition": "tag:deprecated", "action": "exclude", "rule_type": "hard"}
        )

        assert result["created"] is False
        assert "reason" in result

    @pytest.mark.asyncio
    async def test_hard_rule_with_boost_action_rejected(self):
        """Mechanism mismatch: hard rules must use 'filter', not 'boost:N'."""
        from mcp_server.handlers.add_rule import handler

        result = await handler(
            {
                "condition": "tag contains deprecated",
                "action": "boost:0.3",
                "rule_type": "hard",
            }
        )

        assert result["created"] is False
        assert "reason" in result

    @pytest.mark.asyncio
    async def test_tag_rule_with_filter_action_rejected(self):
        """Mechanism mismatch: tag rules must use 'tag:NAME', not 'filter'."""
        from mcp_server.handlers.add_rule import handler

        result = await handler(
            {
                "condition": "content contains TODO",
                "action": "filter",
                "rule_type": "tag",
            }
        )

        assert result["created"] is False
        assert "reason" in result


# ── source_memory_id (M-D6, 7.6 lesson-promotion traceability) ────────────────


class TestAddRuleSourceMemoryId:
    @pytest.mark.asyncio
    async def test_source_memory_id_round_trips(self):
        from mcp_server.handlers.add_rule import handler

        result = await handler(_minimal_args(source_memory_id=4198018))

        assert result["created"] is True
        assert result["source_memory_id"] == 4198018

    @pytest.mark.asyncio
    async def test_source_memory_id_defaults_to_none(self):
        from mcp_server.handlers.add_rule import handler

        result = await handler(_minimal_args())

        assert result["created"] is True
        assert result["source_memory_id"] is None

    @pytest.mark.asyncio
    async def test_persisted_source_memory_id_readable_via_get_all_active_rules(self):
        from mcp_server.handlers.add_rule import _get_store, handler

        result = await handler(_minimal_args(source_memory_id=777))
        assert result["created"] is True

        store = _get_store()
        rules = store.get_all_active_rules()
        row = next(r for r in rules if r["id"] == result["rule_id"])
        assert row["source_memory_id"] == 777


# ── Schema introspection ───────────────────────────────────────────────────────


class TestAddRuleSchema:
    def test_schema_exists_and_has_required_fields(self):
        from mcp_server.handlers.add_rule import schema

        assert "description" in schema
        assert "inputSchema" in schema
        required = schema["inputSchema"].get("required", [])
        assert "condition" in required
        assert "action" in required

    def test_rule_type_enum_in_schema(self):
        from mcp_server.handlers.add_rule import schema

        props = schema["inputSchema"]["properties"]
        assert "rule_type" in props
        assert set(props["rule_type"]["enum"]) == {"hard", "soft", "tag"}

    def test_scope_enum_in_schema(self):
        from mcp_server.handlers.add_rule import schema

        props = schema["inputSchema"]["properties"]
        assert "scope" in props
        assert set(props["scope"]["enum"]) == {"global", "domain", "directory"}
