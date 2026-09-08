"""Unsafe paths and credential refusals precede all inference/spawn."""

from __future__ import annotations

import os
import socket
from unittest import mock

from mcp_server.infrastructure import capture_peer, capture_socket
from tests_py.infrastructure._capture_worker_fixture import WorkerFixture


class TestCaptureSecurity(WorkerFixture):
    def test_real_peer_identity_matches_owner(self):
        left, right = socket.socketpair()
        with left, right:
            self.assertEqual(capture_peer.peer_uid(left), os.geteuid())
            capture_peer.authenticate(right)

    def test_foreign_peer_is_refused(self):
        with mock.patch.object(capture_peer, "peer_uid", return_value=os.geteuid() + 1):
            with self.assertRaises(PermissionError):
                capture_peer.authenticate(mock.Mock())

    def test_windows_is_explicit_and_never_opens_tcp(self):
        with mock.patch.object(capture_peer.sys, "platform", "win32"):
            with mock.patch.object(socket, "socket") as constructor:
                with self.assertRaisesRegex(OSError, "no TCP fallback"):
                    capture_socket.runtime_directory(self.root)
                constructor.assert_not_called()

    def test_runtime_symlink_and_parent_symlink_are_refused(self):
        target = self.root / "target"
        target.mkdir()
        link = self.root / ".capture-worker"
        link.symlink_to(target, target_is_directory=True)
        with self.assertRaises(PermissionError):
            capture_socket.runtime_directory(self.root)
        with self.assertRaises(PermissionError):
            capture_socket.runtime_directory(link / "nested")
        self.assertFalse((target / "nested").exists())

    def test_private_runtime_mode_is_required(self):
        runtime = self.root / ".capture-worker"
        runtime.mkdir(mode=0o755)
        with self.assertRaises(PermissionError):
            capture_socket.runtime_directory(self.root)

    def test_socket_type_mode_and_owner_are_checked(self):
        runtime = capture_socket.runtime_directory(self.root)
        path = runtime / "socket"
        with capture_socket.listen(path):
            path.chmod(0o666)
            with self.assertRaises(PermissionError):
                capture_socket.connect(path, self.limits.timeout)
            path.chmod(0o600)
            with mock.patch.object(os, "geteuid", return_value=os.geteuid() + 1):
                with self.assertRaises(PermissionError):
                    capture_socket.connect(path, self.limits.timeout)
        path.unlink()
        path.symlink_to(self.root / "missing")
        with self.assertRaises(PermissionError):
            capture_socket.remove_socket(path)

    def test_symlink_lock_cannot_redirect_writes(self):
        runtime = capture_socket.runtime_directory(self.root)
        target = self.root / "kept"
        target.write_text("untouched")
        (runtime / "launch.lock").symlink_to(target)
        with self.assertRaises(OSError):
            self.send({})
        self.assertEqual(target.read_text(), "untouched")
