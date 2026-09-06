"""Deadline-bound launch-lock wait without polling or a busy spin.

The daemon waiter owns a duplicate descriptor: timeout never closes a descriptor
under a blocked flock call. Cancellation makes it release any later acquisition.
Source: Python concurrent.futures.Future cancellation contract; flock(2).
"""

from __future__ import annotations

import os
import sys
import threading
from concurrent.futures import Future

from mcp_server.infrastructure.capture_transport import remaining

if sys.platform != "win32":
    import fcntl


def _acquire(descriptor: int, result: Future[None]) -> None:
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
    except OSError as exc:
        if result.set_running_or_notify_cancel():
            result.set_exception(exc)
    else:
        if result.set_running_or_notify_cancel():
            result.set_result(None)
    finally:
        os.close(descriptor)


def wait_for_lock(descriptor: int, deadline: float) -> None:
    result: Future[None] = Future()
    duplicate = os.dup(descriptor)
    waiter = threading.Thread(target=_acquire, args=(duplicate, result), daemon=True)
    try:
        waiter.start()
    except RuntimeError:
        os.close(duplicate)
        raise
    try:
        result.result(timeout=remaining(deadline))
    except TimeoutError:
        if result.cancel():
            raise TimeoutError("capture launch lock deadline exceeded") from None
        # RUNNING means flock already returned: only publication remains.
        result.result()
