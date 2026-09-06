"""Resident worker lifetime, admission backpressure and failure boundaries."""

from __future__ import annotations

import concurrent.futures
import stat
import threading
from unittest import mock

from mcp_server.infrastructure import capture_socket as endpoint
from mcp_server.infrastructure import capture_client
from mcp_server.infrastructure.capture_client import deliver
from mcp_server.infrastructure.capture_transport import CaptureTransportError, Limits
from tests_py.infrastructure._capture_worker_fixture import WorkerFixture


class TestCaptureLifecycle(WorkerFixture):
    def test_spawn_reuse_and_idle_exit(self):
        self.send({"content": "first"})
        self.send({"content": "second"})
        self.assertEqual(len(self.children), 1)
        path = self.root / ".capture-worker" / "socket"
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(path.parent.stat().st_mode), 0o700)
        records = self.finish()
        self.assertEqual(
            [r["payload"]["content"] for r in records], ["first", "second"]
        )
        self.assertEqual(len({record["pid"] for record in records}), 1)
        self.assertFalse(path.exists())

    def test_burst_waits_during_cold_work_without_drops(self):
        self.send({"content": "cold", "delay": 0.2})
        with concurrent.futures.ThreadPoolExecutor() as pool:
            requests = [
                pool.submit(self.send, {"number": number}) for number in range(4)
            ]
            for request in requests:
                request.result(timeout=3)
        records = self.finish()
        self.assertEqual(len(records), 5)
        self.assertEqual(len(self.children), 1)
        self.assertEqual(
            {r["payload"].get("number") for r in records[1:]}, set(range(4))
        )
        self.assertFalse((self.root / "errors.txt").exists())

    def test_simultaneous_first_captures_spawn_only_one_worker(self):
        with concurrent.futures.ThreadPoolExecutor() as pool:
            list(pool.map(self.send, ({"number": n} for n in range(4))))
        self.assertEqual(len(self.children), 1)
        self.assertEqual(len(self.finish()), 4)

    def test_crash_releases_lease_and_next_capture_relaunches(self):
        self.send({"crash": True, "delay": 0.02})
        crashed = self.children.pop()
        self.assertEqual(crashed.wait(timeout=3), 1)
        self.assertTrue((self.root / ".capture-worker" / "socket").exists())
        self.send({"content": "after crash"})
        records = self.finish()
        self.assertNotEqual(crashed.pid, records[0]["pid"])

    def test_spawn_failure_never_falls_back_and_next_capture_retries(self):
        with self.assertRaisesRegex(OSError, "fixture spawn refused"):
            deliver(
                self.root,
                {"content": "lost"},
                self.limits,
                mock.Mock(side_effect=OSError("fixture spawn refused")),
            )
        self.send({"content": "retry"})
        records = self.finish()
        self.assertEqual([r["payload"]["content"] for r in records], ["retry"])

    def test_processing_failure_is_reported_and_worker_survives(self):
        self.send({"error": True})
        self.send({"content": "after error"})
        self.assertEqual(len(self.finish()), 1)
        self.assertIn(
            "fixture callback failure", (self.root / "errors.txt").read_text()
        )

    def test_admission_deadline_is_explicit_and_not_replayed(self):
        self.send({"delay": 0.4, "content": "blocked"})
        self.send({"content": "pending"})
        limits = Limits(self.limits.max_bytes, timeout=0.02, idle=self.limits.idle)
        with self.assertRaises((TimeoutError, CaptureTransportError)):
            deliver(self.root, {"content": "uncertain"}, limits, self.spawn)
        self.assertEqual(len(self.children), 1)
        self.finish()

    def test_launch_lock_wait_has_deadline_and_no_spawn(self):
        runtime = endpoint.runtime_directory(self.root)
        spawn = mock.Mock()
        limits = Limits(self.limits.max_bytes, timeout=0.02, idle=self.limits.idle)
        with endpoint.lease(runtime / "launch.lock"):
            with self.assertRaisesRegex(TimeoutError, "launch lock deadline"):
                deliver(self.root, {"content": "blocked"}, limits, spawn)
        spawn.assert_not_called()

    def test_live_lease_and_dead_socket_never_starts_duplicate(self):
        runtime = endpoint.runtime_directory(self.root)
        limits = Limits(self.limits.max_bytes, timeout=0.02, idle=self.limits.idle)
        with endpoint.lease(runtime / "worker.lock"):
            with self.assertRaises(TimeoutError):
                deliver(self.root, {}, limits, mock.Mock())

    def test_next_capture_waits_for_previous_worker_store_cleanup(self):
        runtime = endpoint.runtime_directory(self.root)
        entered = threading.Event()
        original = capture_client._start_worker

        def start(*args):
            entered.set()
            return original(*args)

        with concurrent.futures.ThreadPoolExecutor() as pool:
            with mock.patch.object(capture_client, "_start_worker", start):
                with endpoint.lease(runtime / "worker.lock"):
                    request = pool.submit(self.send, {"content": "after cleanup"})
                    self.assertTrue(entered.wait(timeout=2))
            request.result(timeout=3)
        self.assertEqual(self.finish()[0]["payload"], {"content": "after cleanup"})

    def test_empty_object_is_a_real_generic_request(self):
        self.send({})
        self.assertEqual(self.finish()[0]["payload"], {})
