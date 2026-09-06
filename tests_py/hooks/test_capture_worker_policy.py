"""Envelope derivation and unchanged producer payload, without the handler."""

from __future__ import annotations

import ast
import json
import os
import unittest
from pathlib import Path
from unittest import mock

from mcp_server.hooks import capture_worker_policy as policy
from mcp_server.hooks._capture_mode import HIGH_VALUE_TOOLS
from mcp_server.infrastructure.capture_transport import encode


def payload(content="fixture", directory="/project", tags=None):
    return {
        "content": content,
        "tags": tags or [],
        "directory": directory,
        "source": "post_tool_capture",
        "origin_tool": "NotebookEdit",
        "write_class": "auto",
        "force": False,
    }


class TestCapturePolicy(unittest.TestCase):
    def test_full_envelope_accepts_worst_json_escaping(self):
        value = payload(
            "\x00" * policy.CONTENT_MAX_BYTES,
            "\x00" * policy.DIRECTORY_CHARS,
            ["\x00" * policy.TAG_CHARS] * policy.TAG_COUNT,
        )
        policy.validate_payload(value)
        frame = encode(value, policy.limits().max_bytes)
        self.assertEqual(len(frame) - 4, policy.limits().max_bytes)

    def test_multibyte_content_at_byte_limit_is_preserved(self):
        character = "😀"
        value = payload(
            character * (policy.CONTENT_MAX_BYTES // len(character.encode()))
        )
        policy.validate_payload(value)
        frame = encode(value, policy.limits().max_bytes)
        self.assertEqual(json.loads(frame[4:]), value)

    def test_field_limit_excess_is_an_explicit_error(self):
        variants = [
            payload("x" * (policy.CONTENT_MAX_BYTES + 1)),
            payload(directory="x" * (policy.DIRECTORY_CHARS + 1)),
            payload(tags=["x"] * (policy.TAG_COUNT + 1)),
            payload(tags=["x" * (policy.TAG_CHARS + 1)]),
        ]
        for value in variants:
            with self.assertRaises(ValueError):
                policy.validate_payload(value)

    def test_capture_provenance_cannot_be_overridden(self):
        for key, value in (
            ("force", True),
            ("write_class", "deliberate"),
            ("source", "owner"),
            ("origin_tool", "unknown"),
        ):
            changed = payload()
            changed[key] = value
            with self.assertRaises(ValueError):
                policy.validate_payload(changed)

    def test_idle_default_and_invalid_config(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(policy.limits().idle, 300.0)
        for value in ("0", "-1", "nan", "inf", "invalid"):
            with mock.patch.dict(os.environ, {"CORTEX_CAPTURE_IDLE_SECONDS": value}):
                with self.assertRaises(ValueError):
                    policy.limits()

    def test_tool_vocabulary_and_limits_match_existing_contracts(self):
        root = Path(__file__).resolve().parents[2]
        tree = ast.parse((root / "mcp_server/hooks/post_tool_capture.py").read_text())
        names = {"_LIGHT_VALUE_TOOLS", "_CONDITIONAL_TOOLS"}
        values = [
            ast.literal_eval(node.value)
            for node in tree.body
            if isinstance(node, ast.Assign)
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id in names
        ]
        self.assertEqual(HIGH_VALUE_TOOLS | set.union(*values), policy.CAPTURE_TOOLS)
        self.assertLessEqual(max(map(len, policy.CAPTURE_TOOLS)), len("NotebookEdit"))

    def test_metadata_limits_are_reconciled_with_remember_schema(self):
        root = Path(__file__).resolve().parents[2]
        tree = ast.parse((root / "mcp_server/validation/schemas.py").read_text())
        declaration = next(
            node
            for node in tree.body
            if isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "SCHEMAS"
        )
        properties = ast.literal_eval(declaration.value)["remember"]["properties"]
        self.assertEqual(policy.DIRECTORY_CHARS, properties["directory"]["maxLength"])
        self.assertEqual(policy.TAG_COUNT, properties["tags"]["maxItems"])
        self.assertEqual(policy.TAG_CHARS, properties["tags"]["items"]["maxLength"])
