"""
Test Suite for Phase 3: High-Speed Segment Engine & Anti-Stall Watchdog
Tests ParallelDownloadEngine, work-stealing, watchdog stall detection, and Windows keep-awake.
"""

import asyncio
import tempfile
import time
from pathlib import Path
from aiohttp import web
import pytest

from ffdl.core.engine import ParallelDownloadEngine
from ffdl.core.watchdog import SocketWatchdog
from ffdl.os.win_sleep import set_windows_keep_awake
from ffdl.persistence.catalog import DownloadCatalog


def test_socket_watchdog():
    wd = SocketWatchdog(stall_timeout=0.2)
    wd.heartbeat(1)
    assert not wd.is_stalled(1)

    time.sleep(0.25)
    assert wd.is_stalled(1)

    wd.heartbeat(1)
    assert not wd.is_stalled(1)

    wd.clear(1)
    assert not wd.is_stalled(1)


def test_windows_keep_awake():
    set_windows_keep_awake(True)
    set_windows_keep_awake(False)


@pytest.mark.asyncio
async def test_engine_download_from_local_server(unused_tcp_port):
    test_data = b"PEAK_GOD_LEVEL_SEGMENT_DOWNLOAD_ENGINE_VERIFIED" * 1000  # ~47 KB
    total_size = len(test_data)

    async def handle_download(request):
        range_header = request.headers.get("Range")
        if range_header:
            parts = range_header.replace("bytes=", "").split("-")
            start = int(parts[0])
            end = int(parts[1]) if parts[1] else total_size - 1
            chunk = test_data[start : end + 1]
            return web.Response(
                body=chunk,
                status=206,
                headers={
                    "Content-Range": f"bytes {start}-{end}/{total_size}",
                    "Content-Length": str(len(chunk)),
                    "Accept-Ranges": "bytes",
                },
            )
        return web.Response(body=test_data, status=200, headers={"Content-Length": str(total_size)})

    app = web.Application()
    app.router.add_get("/file.bin", handle_download)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", unused_tcp_port)
    await site.start()

    server_url = f"http://127.0.0.1:{unused_tcp_port}/file.bin"

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            dest_file = Path(tmpdir) / "output.bin"
            db_path = Path(tmpdir) / "engine_test.db"
            catalog = DownloadCatalog(db_path=db_path)

            engine = ParallelDownloadEngine(
                url=server_url,
                destination_path=dest_file,
                total_size=total_size,
                concurrency=4,
                catalog=catalog,
            )

            success = await engine.start()
            assert success is True
            assert dest_file.exists()
            assert dest_file.stat().st_size == total_size
            assert dest_file.read_bytes() == test_data
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_engine_deterministic_id_and_path_recovery(unused_tcp_port):
    """Test that a new engine instance automatically recovers the existing job via file path."""
    test_data = b"DETERMINISTIC_RESUMPTION_PATH_RECOVERY_TEST_" * 500  # ~22 KB
    total_size = len(test_data)

    async def handle_download(request):
        range_header = request.headers.get("Range")
        if range_header:
            parts = range_header.replace("bytes=", "").split("-")
            start = int(parts[0])
            end = int(parts[1]) if parts[1] else total_size - 1
            chunk = test_data[start : end + 1]
            return web.Response(
                body=chunk,
                status=206,
                headers={
                    "Content-Range": f"bytes {start}-{end}/{total_size}",
                    "Content-Length": str(len(chunk)),
                    "Accept-Ranges": "bytes",
                },
            )
        return web.Response(body=test_data, status=200, headers={"Content-Length": str(total_size)})

    app = web.Application()
    app.router.add_get("/det_test.bin", handle_download)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", unused_tcp_port)
    await site.start()

    server_url = f"http://127.0.0.1:{unused_tcp_port}/det_test.bin"

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            dest_file = Path(tmpdir) / "recovered.bin"
            db_path = Path(tmpdir) / "det_catalog.db"
            catalog = DownloadCatalog(db_path=db_path)

            # Engine 1: Start with automatic deterministic ID (no download_id passed)
            engine1 = ParallelDownloadEngine(
                url=server_url,
                destination_path=dest_file,
                total_size=total_size,
                concurrency=2,
                catalog=catalog,
            )
            await engine1._init_catalog_and_chunks()
            first_id = engine1.download_id

            # Engine 2: New instance on same destination path without download_id
            engine2 = ParallelDownloadEngine(
                url=server_url,
                destination_path=dest_file,
                total_size=total_size,
                concurrency=2,
                catalog=catalog,
            )
            await engine2._init_catalog_and_chunks()
            second_id = engine2.download_id

            # Both instances must resolve to the identical deterministic ID and state
            assert first_id == second_id
            rec = await catalog.get_download_by_path(dest_file)
            assert rec is not None
            assert rec.id == first_id
    finally:
        await runner.cleanup()
