"""Hold bind/chmod apart to exercise concurrent first-capture publication."""

from __future__ import annotations

import concurrent.futures
import threading
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

from tests_py.infrastructure._capture_worker_fixture import WorkerFixture


@contextmanager
def _pause_permissions(socket_path):
    bound = threading.Event()
    release = threading.Event()
    chmod = Path.chmod

    def pause(path, mode, **kwargs):
        if path == socket_path:
            # Test-only mode exposes bind/chmod even with an owner-only umask.
            chmod(path, 0o700)
            bound.set()
            if not release.wait(timeout=2):
                raise AssertionError("test did not release socket publication")
        return chmod(path, mode, **kwargs)

    with mock.patch.object(Path, "chmod", pause):
        try:
            yield bound, release
        finally:
            release.set()


class TestSocketPublication(WorkerFixture):
    def test_concurrent_capture_waits_until_socket_permissions_are_ready(self):
        socket_path = self.root / ".capture-worker" / "socket"
        entered = threading.Event()

        def observe():
            entered.set()
            self.send({"content": "observer"})

        with _pause_permissions(socket_path) as (bound, release):
            with concurrent.futures.ThreadPoolExecutor() as pool:
                creator = pool.submit(self.send, {"content": "creator"})
                try:
                    self.assertTrue(bound.wait(timeout=2))
                    observer = pool.submit(observe)
                    self.assertTrue(entered.wait(timeout=2))
                    with self.assertRaises(concurrent.futures.TimeoutError):
                        observer.result(timeout=0.02)
                finally:
                    release.set()
                creator.result(timeout=3)
                observer.result(timeout=3)
        self.assertEqual(len(self.children), 1)
        self.assertEqual(
            {record["payload"]["content"] for record in self.finish()},
            {"creator", "observer"},
        )
