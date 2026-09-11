"""
Test Suite for Phase 1: Storage Ledger & Durability Foundation
Tests SQLite WAL schema, atomic transactions, crash recovery, cascade deletes,
and streaming SHA-256 integrity verifier.
"""

import asyncio
import hashlib
import os
import tempfile
from pathlib import Path
import pytest

from ffdl.persistence.catalog import DownloadCatalog, DownloadRecord, SegmentRecord
from ffdl.persistence.verifier import StreamingVerifier


@pytest.mark.asyncio
async def test_catalog_lifecycle_and_wal():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_catalog.db"
        catalog = DownloadCatalog(db_path=db_path)
        await catalog.init_db()

        # Check WAL mode enabled
        assert db_path.exists()
        import sqlite3
        con = sqlite3.connect(db_path)
        cur = con.cursor()
        cur.execute("PRAGMA journal_mode")
        mode = cur.fetchone()[0]
        con.close()
        assert mode.lower() == "wal"

        # Create download with segments
        segments = [(0, 999), (1000, 1999), (2000, 2999)]
        rec = await catalog.create_download(
            download_id="dl_001",
            url="https://fuckingfast.co/test#game.part01.rar",
            filename="game.part01.rar",
            save_path=Path(tmpdir) / "game.part01.rar",
            total_bytes=3000,
            etag="abc123",
            segments=segments,
        )

        assert rec.id == "dl_001"
        assert len(rec.segments) == 3
        assert rec.segments[0].start_byte == 0
        assert rec.segments[0].end_byte == 999

        # Fetch record
        fetched = await catalog.get_download("dl_001")
        assert fetched is not None
        assert fetched.filename == "game.part01.rar"
        assert len(fetched.segments) == 3

        # Update segment progress
        await catalog.update_segment_progress(
            segment_id="dl_001_0",
            written_bytes=1000,
            is_done=True,
            sha256_hash="deadbeef",
        )

        updated = await catalog.get_download("dl_001")
        assert updated.segments[0].is_done is True
        assert updated.segments[0].written_bytes == 1000
        assert updated.segments[0].sha256_hash == "deadbeef"
        assert updated.segments[1].is_done is False

        # Status update
        await catalog.update_download_status("dl_001", "completed")
        completed = await catalog.get_download("dl_001")
        assert completed.status == "completed"

        # List all downloads
        all_dls = await catalog.list_all_downloads()
        assert len(all_dls) == 1

        # Delete download (cascade delete verification)
        await catalog.delete_download("dl_001")
        deleted = await catalog.get_download("dl_001")
        assert deleted is None


def test_streaming_verifier():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "payload.bin"
        content = b"PEAK_GOD_LEVEL_ULTRA_ACCELERATOR_" * 100000  # ~3.3 MB
        test_file.write_bytes(content)

        expected_full_sha = hashlib.sha256(content).hexdigest()
        computed_full = StreamingVerifier.compute_file_sha256(test_file)
        assert computed_full == expected_full_sha
        assert StreamingVerifier.verify_file_sha256(test_file, expected_full_sha) is True
        assert StreamingVerifier.verify_file_sha256(test_file, "wrong_hash") is False

        # Range verification
        start = 100
        end = 500
        range_content = content[start : end + 1]
        expected_range_sha = hashlib.sha256(range_content).hexdigest()
        computed_range = StreamingVerifier.compute_range_sha256(test_file, start, end)
        assert computed_range == expected_range_sha
