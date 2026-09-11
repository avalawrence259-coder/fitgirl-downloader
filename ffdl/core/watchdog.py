"""
ffdl.core.watchdog - Anti-Stall Throughput Monitor & Socket Reaper
==================================================================
Monitors per-worker socket throughput.
If zero bytes are transferred over stall_timeout (default: 3.5s),
the watchdog drops the dead socket and forces an immediate reconnect.
"""

from __future__ import annotations

import time
from typing import Dict, List


class SocketWatchdog:
    """Tracks byte activity timestamps and identifies stalled worker sockets using time.monotonic()."""

    def __init__(self, stall_timeout: float = 15.0):
        self.stall_timeout = stall_timeout
        self._last_active: Dict[int, float] = {}

    def heartbeat(self, worker_id: int):
        """Record byte activity on a worker socket."""
        self._last_active[worker_id] = time.monotonic()

    def is_stalled(self, worker_id: int) -> bool:
        """Check whether a worker has exceeded the stall threshold."""
        last = self._last_active.get(worker_id)
        if last is None:
            return False
        return (time.monotonic() - last) > self.stall_timeout

    def get_stalled_workers(self) -> List[int]:
        """Return list of all currently stalled worker IDs."""
        now = time.monotonic()
        return [
            w_id for w_id, last_time in self._last_active.items()
            if (now - last_time) > self.stall_timeout
        ]

    def clear(self, worker_id: int):
        """Reset tracking for a worker upon task completion or retry."""
        self._last_active.pop(worker_id, None)
