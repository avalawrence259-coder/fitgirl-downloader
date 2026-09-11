"""
ffdl.engine - Deprecated Root Engine Module
===========================================
This module is deprecated and will be removed in a future major version.
Please import from `ffdl.core.engine` instead.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "ffdl.engine is deprecated; use ffdl.core.engine instead.",
    DeprecationWarning,
    stacklevel=2,
)

from ffdl.core.engine import (
    ParallelDownloadEngine,
    ActiveChunk,
)
from ffdl.core.writer import check_disk_space
from ffdl.os.win_sleep import set_windows_keep_awake

# Backwards compatibility aliases
FFDownloadEngine = ParallelDownloadEngine
ChunkTask = ActiveChunk


def check_available_disk_space(target_dir, required_bytes):
    has_space, free_bytes, _ = check_disk_space(target_dir, required_bytes)
    return has_space, free_bytes


__all__ = [
    "ParallelDownloadEngine",
    "FFDownloadEngine",
    "ActiveChunk",
    "ChunkTask",
    "check_disk_space",
    "check_available_disk_space",
    "set_windows_keep_awake",
]
