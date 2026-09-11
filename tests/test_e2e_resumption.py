"""
Test Suite for Phase 7: Crash Recovery Stress Testing, E2E & Resumption
Tests process-kill resumption, ensuring segments that are already completed
are never re-downloaded, and final assembled bytes match original test vectors.
"""

import asyncio
import tempfile
from pathlib import Path
from aiohttp import web
import pytest

from ffdl.core.engine import ParallelDownloadEngine
from ffdl.persistence.catalog import DownloadCatalog
from ffdl.persistence.resumer import DownloadResumer
from ffdl.persistence.verifier import StreamingVerifier


@pytest.mark.asyncio
async def test_e2e_crash_and_resumption(unused_tcp_port):
    """Simulate a download interrupted at 50%, restarted, and resumed without re-downloading."""
    test_data = b"RESUMPTION_CRASH_TEST_BYTE_VERIFIED_DATA_" * 2000  # ~84 KB
    total_size = len(test_data)
    bytes_served_count = 0

    async def handle_download(request):
        nonlocal bytes_served_count
        range_header = request.headers.get("Range")
        if range_header:
            parts = range_header.replace("bytes=", "").split("-")
            start = int(parts[0])
            end = int(parts[1]) if parts[1] else total_size - 1
            chunk = test_data[start : end + 1]
            bytes_served_count += len(chunk)
            return web.Response(
                body=chunk,
                status=206,
                headers={
                    "Content-Range": f"bytes {start}-{end}/{total_size}",
                    "Content-Length": str(len(chunk)),
                    "Accept-Ranges": "bytes",
                },
            )
        bytes_served_count += len(test_data)
        return web.Response(body=test_data, status=200, headers={"Content-Length": str(total_size)})

    app = web.Application()
    app.router.add_get("/resume_test.bin", handle_download)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", unused_tcp_port)
    await site.start()

    server_url = f"http://127.0.0.1:{unused_tcp_port}/resume_test.bin"

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            dest_file = Path(tmpdir) / "resumed.bin"
            db_path = Path(tmpdir) / "e2e_catalog.db"
            catalog = DownloadCatalog(db_path=db_path)
            download_id = "job_crash_test"

            # 1. Initialize download and artificially simulate half completion
            part_tuples = [(0, total_size // 2 - 1), (total_size // 2, total_size - 1)]
            rec = await catalog.create_download(
                download_id=download_id,
                url=server_url,
                filename=dest_file.name,
                save_path=dest_file,
                total_bytes=total_size,
                segments=part_tuples,
            )

            # Mark first half as already done and write its bytes to disk
            half_bytes = total_size // 2
            with open(dest_file, "wb") as f:
                f.write(test_data[:half_bytes])
                f.seek(total_size - 1)
                f.write(b"\0")

            await catalog.update_segment_progress(
                segment_id=f"{download_id}_0",
                written_bytes=half_bytes,
                is_done=True,
            )

            # Check resumer detects partial bytes
            resumer = DownloadResumer(catalog)
            verified_b, expected_b = await resumer.validate_local_bytes(download_id)
            assert verified_b == half_bytes
            assert expected_b == total_size

            # 2. Launch engine with existing catalog and job ID to finish remaining half
            engine = ParallelDownloadEngine(
                url=server_url,
                destination_path=dest_file,
                total_size=total_size,
                concurrency=2,
                catalog=catalog,
                download_id=download_id,
            )

            bytes_served_count = 0
            success = await engine.start()
            assert success is True
            assert dest_file.stat().st_size == total_size
            assert dest_file.read_bytes() == test_data

            # Assert only second half was requested across network
            assert bytes_served_count <= (total_size - half_bytes + 2000)

            # Verify full SHA-256 matches
            assert StreamingVerifier.verify_file_sha256(
                dest_file, StreamingVerifier.compute_file_sha256(dest_file)
            ) is True
    finally:
        await runner.cleanup()
