"""
Test Suite for Phase 2: Positional File Writer & Tuned Socket Factory
Tests concurrent non-locking positional byte writes and tuned network session generation.
"""

import asyncio
import os
import tempfile
from pathlib import Path
import pytest

from ffdl.core.writer import PositionalFileWriter
from ffdl.core.network import TunedClientSession
from ffdl.persistence.verifier import StreamingVerifier


def test_positional_writer_concurrent_blocks():
    with tempfile.TemporaryDirectory() as tmpdir:
        dest_file = Path(tmpdir) / "test_concurrent.bin"
        num_workers = 10
        chunk_size = 50000
        total_size = num_workers * chunk_size

        writer = PositionalFileWriter(dest_file, total_size)
        writer.open()

        # Simulate 10 workers writing to different non-overlapping byte ranges
        for worker_id in range(num_workers):
            offset = worker_id * chunk_size
            data = bytes([worker_id + 65]) * chunk_size  # 'A', 'B', 'C', ...
            written = writer.write_at(offset, data)
            assert written == chunk_size

        writer.close()

        assert dest_file.exists()
        assert dest_file.stat().st_size == total_size

        # Verify each segment content
        with open(dest_file, "rb") as f:
            for worker_id in range(num_workers):
                f.seek(worker_id * chunk_size)
                segment = f.read(chunk_size)
                assert segment == bytes([worker_id + 65]) * chunk_size


@pytest.mark.asyncio
async def test_tuned_client_session():
    async with TunedClientSession.create_session(concurrency=8) as session:
        assert session is not None
        assert not session.closed
        assert "User-Agent" in session.headers


def test_disk_space_preflight_check():
    from ffdl.core.writer import check_disk_space

    with tempfile.TemporaryDirectory() as tmpdir:
        dest_file = Path(tmpdir) / "space_test.bin"
        # 1. Realistic request should pass
        has_space, free_bytes, needed = check_disk_space(dest_file, 1024)
        assert has_space is True
        assert free_bytes > 0

        # 2. Absurdly huge request (10 Exabytes) should fail
        has_space, free_bytes, needed = check_disk_space(dest_file, 10**19)
        assert has_space is False

        # 3. Writer should raise OSError when attempting to preallocate beyond disk space
        writer = PositionalFileWriter(dest_file, 10**19)
        with pytest.raises(OSError) as excinfo:
            writer.preallocate()
        assert "Insufficient disk space" in str(excinfo.value)
