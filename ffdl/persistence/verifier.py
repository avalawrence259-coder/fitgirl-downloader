"""
ffdl.persistence.verifier - Streaming Cryptographic & Hash Integrity Verifier
=============================================================================
High-performance streaming SHA-256 and checksum verification.
Guarantees byte-level integrity verification for chunks and full archives.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Callable, Optional


class StreamingVerifier:
    """Computes streaming SHA-256 and MD5 without loading large multi-gigabyte files into RAM."""

    BUFFER_SIZE = 1024 * 1024  # 1 MB chunk buffer for optimal OS page read cache

    @classmethod
    def compute_file_sha256(
        cls,
        file_path: Path | str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> str:
        """Compute the full SHA-256 hex digest of a file on disk in streaming mode."""
        p = Path(file_path)
        if not p.exists():
            raise FileNotFoundError(f"Target file not found: {p}")

        total_bytes = p.stat().st_size
        hasher = hashlib.sha256()
        bytes_read = 0

        with open(p, "rb") as f:
            while chunk := f.read(cls.BUFFER_SIZE):
                hasher.update(chunk)
                bytes_read += len(chunk)
                if progress_callback:
                    progress_callback(bytes_read, total_bytes)

        return hasher.hexdigest()

    @classmethod
    def compute_range_sha256(
        cls,
        file_path: Path | str,
        start_byte: int,
        end_byte: int,
    ) -> str:
        """Compute the SHA-256 hex digest for a specific contiguous byte range [start_byte, end_byte]."""
        p = Path(file_path)
        if not p.exists():
            raise FileNotFoundError(f"Target file not found: {p}")

        total_range = end_byte - start_byte + 1
        if total_range <= 0:
            return hashlib.sha256(b"").hexdigest()

        hasher = hashlib.sha256()
        bytes_remaining = total_range

        with open(p, "rb") as f:
            f.seek(start_byte)
            while bytes_remaining > 0:
                to_read = min(cls.BUFFER_SIZE, bytes_remaining)
                chunk = f.read(to_read)
                if not chunk:
                    break
                hasher.update(chunk)
                bytes_remaining -= len(chunk)

        return hasher.hexdigest()

    @classmethod
    def verify_file_sha256(cls, file_path: Path | str, expected_sha256: str) -> bool:
        """Verify whether a file matches an expected SHA-256 hex digest."""
        computed = cls.compute_file_sha256(file_path)
        return computed.strip().lower() == expected_sha256.strip().lower()
