"""Ensure one worker and admit one capture, without loading inference code."""

from __future__ import annotations

import socket
import time
from collections.abc import Callable
from pathlib import Path

from mcp_server.infrastructure import capture_socket as endpoint
from mcp_server.infrastructure.capture_transport import Limits, encode, remaining, send

Spawn = Callable[[socket.socket, int], None]


def _connect_or_spawn(runtime: Path, deadline: float, spawn: Spawn) -> socket.socket:
    path = runtime / "socket"
    # Serialize inspection with bind/chmod/listen, including warm connections.
    # A socket pathname exists before its owner-only permissions are ready.
    with endpoint.lease(runtime / "launch.lock", deadline):
        try:
            return endpoint.connect(path, remaining(deadline))
        except (FileNotFoundError, ConnectionRefusedError):
            # Absence before sending is the only safe restart point.
            _start_worker(runtime, deadline, spawn)
        return endpoint.connect(path, remaining(deadline))


def _start_worker(runtime: Path, deadline: float, spawn: Spawn) -> None:
    path = runtime / "socket"
    # An exiting worker may already have closed its listener while closing stores.
    # Wait within the same budget so normal teardown does not drop the next capture.
    with endpoint.lease(runtime / "worker.lock", deadline) as descriptor:
        endpoint.remove_socket(path)
        with endpoint.listen(path) as listener:
            spawn(listener, descriptor)


def deliver(
    root: Path, payload: dict[str, object], limits: Limits, spawn: Spawn
) -> None:
    """Return after admission; uncertain delivery raises and is never replayed."""
    frame = encode(payload, limits.max_bytes)
    deadline = time.monotonic() + limits.timeout
    runtime = endpoint.runtime_directory(root)
    with _connect_or_spawn(runtime, deadline, spawn) as connection:
        send(connection, frame, deadline)
