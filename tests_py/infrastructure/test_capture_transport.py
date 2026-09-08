"""Bounded decoding must refuse framing errors without reading large bodies."""

from __future__ import annotations

import socket
import struct
import time
import unittest
from unittest import mock

from mcp_server.infrastructure.capture_transport import (
    CaptureTransportError,
    encode,
    receive,
    send,
)


class TestCaptureTransport(unittest.TestCase):
    def test_payload_round_trip_preserves_unicode_and_control(self):
        payload = {"content": "café\n\x00😀", "tags": ["a"], "force": False}
        left, right = socket.socketpair()
        with left, right:
            left.sendall(encode(payload, 4096))
            self.assertEqual(receive(right, 4096, time.monotonic() + 1), payload)

    def test_oversize_header_refused_before_reading_body(self):
        connection = mock.Mock()
        connection.recv.return_value = struct.pack("!I", 4097)
        with self.assertRaisesRegex(CaptureTransportError, "length exceeds"):
            receive(connection, 4096, time.monotonic() + 1)
        connection.recv.assert_called_once_with(struct.calcsize("!I"))

    def test_incomplete_and_malformed_frames_are_refused(self):
        for wire in (
            b"\x00",
            struct.pack("!I", 1) + b"{",
            struct.pack("!I", 2) + b"[]",
        ):
            left, right = socket.socketpair()
            with self.subTest(wire=wire), left, right:
                left.sendall(wire)
                left.shutdown(socket.SHUT_WR)
                with self.assertRaises(CaptureTransportError):
                    receive(right, 4096, time.monotonic() + 1)

    def test_frame_budget_is_total_not_reset_for_each_read(self):
        left, right = socket.socketpair()
        with left, right:
            left.sendall(b"\x00")
            with self.assertRaises(TimeoutError):
                receive(right, 4096, time.monotonic() + 0.01)

    def test_negative_ack_and_eof_do_not_trigger_replay(self):
        for ack in (b"\x00", b""):
            connection = mock.Mock()
            connection.recv.return_value = ack
            with self.assertRaises(CaptureTransportError):
                send(connection, b"frame", time.monotonic() + 1)
            connection.sendall.assert_called_once_with(b"frame")

    def test_encoding_refuses_oversize_instead_of_truncating(self):
        with self.assertRaises(CaptureTransportError):
            encode({"content": "still complete"}, 1)

    def test_deep_json_failure_is_reported_as_a_protocol_error(self):
        connection = mock.Mock()
        connection.recv.side_effect = [struct.pack("!I", 2), b"{}"]
        with mock.patch("json.loads", side_effect=RecursionError):
            with self.assertRaisesRegex(CaptureTransportError, "invalid capture JSON"):
                receive(connection, 4096, time.monotonic() + 1)
