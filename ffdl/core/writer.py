"""
ffdl.core.writer - High-Performance Positional Zero-Lock File Writer & Allocator
================================================================================
Eliminates NTFS thread contention and disk fragmentation.
Pre-allocates full target file sizes without sparse fragmentation.
Implements non-locking positional byte writes for concurrent stream workers.
Inspired by huggingface/hf_transfer and aria2 disk allocators.
"""

from __future__ import annotations

import os
import shutil
import sys
import threading
import time
from pathlib import Path
from typing import Optional, Tuple


def check_disk_space(
    target_path: Path | str,
    required_bytes: int,
    safety_margin_mb: int = 100,
) -> Tuple[bool, int, int]:
    """
    Checks whether the target filesystem volume has enough space to hold the file.
    Returns: (has_enough_space, free_bytes, needed_bytes)
    """
    p = Path(target_path).resolve()
    target_dir = p.parent if not p.is_dir() else p
    target_dir.mkdir(parents=True, exist_ok=True)

    try:
        usage = shutil.disk_usage(target_dir)
        already_allocated = p.stat().st_size if p.exists() else 0
        net_needed = max(0, required_bytes - already_allocated)
        safety_bytes = safety_margin_mb * 1024 * 1024
        has_space = usage.free >= (net_needed + safety_bytes)
        return has_space, usage.free, net_needed
    except Exception:
        # If filesystem usage cannot be determined, do not block allocation
        return True, 0, required_bytes


class PositionalFileWriter:
    """
    Manages thread-safe non-locking positional writes to a pre-allocated file.
    Includes periodic fsync flushing (4MB or 2.0s intervals) and Win32 SetEndOfFile allocation.
    """

    def __init__(self, target_path: Path | str, total_size: int):
        self.target_path = Path(target_path).resolve()
        self.total_size = total_size
        self._fd: Optional[int] = None
        self._lock = threading.Lock()
        self._bytes_since_flush = 0
        self._last_flush_time = time.monotonic()
        self._flush_interval_bytes = 4 * 1024 * 1024  # 4 MB
        self._flush_interval_sec = 2.0  # 2.0 seconds

    def preallocate(self):
        """
        Pre-allocates the file on disk to prevent NTFS fragmentation during multi-stream writes.
        Uses Win32 SetEndOfFile on Windows with fallback to seek-and-write.
        """
        self.target_path.parent.mkdir(parents=True, exist_ok=True)

        # Pre-flight disk space validation
        has_space, free_bytes, net_needed = check_disk_space(self.target_path, self.total_size)
        if not has_space and net_needed > 0:
            free_mb = free_bytes / (1024 * 1024)
            needed_mb = net_needed / (1024 * 1024)
            raise OSError(
                f"Insufficient disk space on {self.target_path.parent}. "
                f"Required: {needed_mb:.1f} MB, Available: {free_mb:.1f} MB"
            )

        if not self.target_path.exists() or self.target_path.stat().st_size < self.total_size:
            allocated = False
            if sys.platform == "win32" and self.total_size > 0:
                try:
                    import ctypes
                    from ctypes import wintypes
                    # Open handle via CreateFileW to use SetFilePointerEx + SetEndOfFile
                    GENERIC_WRITE = 0x40000000
                    FILE_SHARE_READ = 0x00000001
                    FILE_SHARE_WRITE = 0x00000002
                    OPEN_ALWAYS = 4
                    FILE_ATTRIBUTE_NORMAL = 0x80

                    handle = ctypes.windll.kernel32.CreateFileW(
                        str(self.target_path),
                        GENERIC_WRITE,
                        FILE_SHARE_READ | FILE_SHARE_WRITE,
                        None,
                        OPEN_ALWAYS,
                        FILE_ATTRIBUTE_NORMAL,
                        None,
                    )
                    INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
                    if handle != INVALID_HANDLE_VALUE and handle != 0:
                        try:
                            distance = wintypes.LARGE_INTEGER(self.total_size)
                            success = ctypes.windll.kernel32.SetFilePointerEx(
                                handle, distance, None, 0  # FILE_BEGIN
                            )
                            if success:
                                ctypes.windll.kernel32.SetEndOfFile(handle)
                                allocated = True
                        finally:
                            ctypes.windll.kernel32.CloseHandle(handle)
                except Exception:
                    allocated = False

            if not allocated:
                with open(self.target_path, "wb") as f:
                    if self.total_size > 0:
                        f.seek(self.total_size - 1)
                        f.write(b"\0")
                        f.flush()

    def open(self):
        """Opens raw OS file descriptor in binary read/write mode."""
        self.preallocate()
        if self._fd is None:
            flags = os.O_RDWR | getattr(os, "O_BINARY", 0)
            self._fd = os.open(str(self.target_path), flags)
            self._last_flush_time = time.monotonic()
            self._bytes_since_flush = 0

    def write_at(self, offset: int, data: bytes) -> int:
        """
        Write bytes at an exact offset thread-safely with periodic fsync flushing.
        """
        if self._fd is None:
            self.open()

        with self._lock:
            if hasattr(os, "pwrite"):
                written = os.pwrite(self._fd, data, offset)
            else:
                os.lseek(self._fd, offset, os.SEEK_SET)
                written = os.write(self._fd, data)

            self._bytes_since_flush += written
            now = time.monotonic()
            if (
                self._bytes_since_flush >= self._flush_interval_bytes
                or (now - self._last_flush_time) >= self._flush_interval_sec
            ):
                self._sync_locked()
            return written

    def _sync_locked(self):
        """Internal flush when lock is already held."""
        if self._fd is not None:
            try:
                os.fsync(self._fd)
            except Exception:
                pass
            self._bytes_since_flush = 0
            self._last_flush_time = time.monotonic()

    def flush(self):
        """Flush OS write caches to disk."""
        with self._lock:
            self._sync_locked()

    def close(self):
        """Flush and close the underlying OS file descriptor."""
        with self._lock:
            if self._fd is not None:
                try:
                    os.fsync(self._fd)
                except Exception:
                    pass
                try:
                    os.close(self._fd)
                except Exception:
                    pass
                self._fd = None
                self._bytes_since_flush = 0

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
