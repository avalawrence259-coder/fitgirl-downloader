"""
ffdl.os.win_sleep - Windows Thread Execution State Standby & Sleep Blocker
==========================================================================
Prevents Windows from entering sleep or powering down network cards during active downloads.
"""

from __future__ import annotations

import sys


def set_windows_keep_awake(enabled: bool):
    """Acquire or release Windows thread execution keep-awake lock."""
    if sys.platform == "win32":
        try:
            import ctypes
            ES_CONTINUOUS = 0x80000000
            ES_SYSTEM_REQUIRED = 0x00000001
            ES_AWAYMODE_REQUIRED = 0x00000040

            if enabled:
                ctypes.windll.kernel32.SetThreadExecutionState(
                    ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED
                )
            else:
                ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
        except Exception:
            pass
