"""
ffdl.core.engine - Peak God Parallel Segment Engine & Work-Stealing Coordinator
================================================================================
High-performance asynchronous parallel download coordinator.
Features:
- Non-locking positional seek-writes to pre-allocated disk files.
- Dynamic work-stealing (idle workers split remaining tail of slowest donor).
- Active anti-stall socket watchdog (cuts hung connections in <3.5s).
- Windows thread execution keep-awake assertion.
- SQLite WAL atomic checkpointing per segment.
- Exponential backoff with random jitter.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional

import aiohttp

from ffdl.core.network import TunedClientSession
from ffdl.core.watchdog import SocketWatchdog
from ffdl.core.writer import PositionalFileWriter
from ffdl.os.win_sleep import set_windows_keep_awake
from ffdl.persistence.catalog import DownloadCatalog, DownloadRecord, SegmentRecord


@dataclass
class ActiveChunk:
    chunk_id: int
    segment_id: str
    start_byte: int
    end_byte: int
    current_byte: int
    is_completed: bool = False
    in_progress: bool = False


class ParallelDownloadEngine:
    """Async Multi-Stream Download Accelerator with Work-Stealing and Anti-Stall."""

    def __init__(
        self,
        url: str,
        destination_path: Path | str,
        total_size: int,
        concurrency: int = 16,
        chunk_buffer_kb: int = 256,
        catalog: Optional[DownloadCatalog] = None,
        download_id: Optional[str] = None,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        token_refresh_callback: Optional[Callable[[], Awaitable[str]]] = None,
    ):
        self.url = url
        self.destination_path = Path(destination_path).resolve()
        self.total_size = total_size
        self.concurrency = max(1, min(concurrency, 32))
        self.chunk_buffer_size = chunk_buffer_kb * 1024
        self.catalog = catalog or DownloadCatalog()
        if download_id:
            self.download_id = download_id
        else:
            # Deterministic download ID derived from canonical destination path
            path_hash = hashlib.sha256(str(self.destination_path).encode("utf-8")).hexdigest()[:16]
            self.download_id = f"dl_{path_hash}"

        self.progress_callback = progress_callback
        self.token_refresh_callback = token_refresh_callback

        self.writer = PositionalFileWriter(self.destination_path, self.total_size)
        self.watchdog = SocketWatchdog(stall_timeout=3.5)
        self.chunks: List[ActiveChunk] = []
        self.total_downloaded_bytes = 0
        self.stop_event = asyncio.Event()
        self._lock = asyncio.Lock()
        self.start_time = 0.0
        self.supports_ranges = True

    async def _init_catalog_and_chunks(self):
        """Create or recover download partitions from SQLite WAL catalog."""
        # 1. Try to recover by download_id
        rec = await self.catalog.get_download(self.download_id)
        # 2. Try to recover by canonical save_path if not found
        if not rec:
            rec = await self.catalog.get_download_by_path(self.destination_path)
            if rec:
                self.download_id = rec.id

        if rec and rec.segments and rec.total_bytes == self.total_size:
            # Recover existing segments from database
            for seg in rec.segments:
                ac = ActiveChunk(
                    chunk_id=seg.segment_index,
                    segment_id=seg.id,
                    start_byte=seg.start_byte,
                    end_byte=seg.end_byte,
                    current_byte=seg.start_byte + seg.written_bytes,
                    is_completed=seg.is_done,
                )
                self.chunks.append(ac)
                self.total_downloaded_bytes += seg.written_bytes
        else:
            # Partition file into equal segments
            part_size = self.total_size // self.concurrency
            tuples = []
            for i in range(self.concurrency):
                sb = i * part_size
                eb = (sb + part_size - 1) if i < self.concurrency - 1 else (self.total_size - 1)
                tuples.append((sb, eb))

            rec = await self.catalog.create_download(
                download_id=self.download_id,
                url=self.url,
                filename=self.destination_path.name,
                save_path=self.destination_path,
                total_bytes=self.total_size,
                segments=tuples,
            )
            for seg in rec.segments:
                self.chunks.append(
                    ActiveChunk(
                        chunk_id=seg.segment_index,
                        segment_id=seg.id,
                        start_byte=seg.start_byte,
                        end_byte=seg.end_byte,
                        current_byte=seg.start_byte,
                        is_completed=False,
                    )
                )

    async def _download_chunk_stream(
        self,
        session: aiohttp.ClientSession,
        worker_id: int,
        chunk: ActiveChunk,
    ):
        """Download range stream with watchdog heartbeats and positional seek-writes."""
        retries = 0
        max_retries = 20
        bytes_since_last_db_commit = 0
        db_commit_interval = 4 * 1024 * 1024  # 4 MB checkpoint interval

        while not self.stop_event.is_set() and chunk.current_byte <= chunk.end_byte:
            if chunk.is_completed:
                return

            self.watchdog.heartbeat(worker_id)
            headers = {
                "Range": f"bytes={chunk.current_byte}-{chunk.end_byte}",
            }

            resp = None
            try:
                resp = await session.get(self.url, headers=headers)
                if resp.status in (401, 403, 410, 429) or retries >= 3:
                    # Expired CDN token or rate-limiting: attempt refresh
                    if self.token_refresh_callback:
                        try:
                            new_url = await self.token_refresh_callback()
                            if new_url and new_url != self.url:
                                self.url = new_url
                                retries = 0
                        except Exception:
                            pass

                if resp.status == 200:
                    # Server ignored Range header!
                    if chunk.start_byte > 0:
                        # Sub-range received 200 OK -> server does not support HTTP ranges
                        self.supports_ranges = False
                        # Mark chunk as not doable by this worker
                        resp.close()
                        return
                    # If chunk.start_byte == 0, worker 0 downloads the whole stream sequentially
                    self.supports_ranges = False

                if resp.status in (200, 206):
                    retries = 0
                    content_iter = resp.content.iter_chunked(self.chunk_buffer_size).__aiter__()

                    while not self.stop_event.is_set() and chunk.current_byte <= chunk.end_byte:
                        try:
                            # Enforce active watchdog timeout on socket chunk read
                            data = await asyncio.wait_for(
                                content_iter.__anext__(),
                                timeout=self.watchdog.stall_timeout,
                            )
                        except StopAsyncIteration:
                            break
                        except asyncio.TimeoutError:
                            # Socket stalled for > stall_timeout (15s)! Drop socket and reconnect
                            retries += 1
                            break

                        data_len = len(data)
                        offset = chunk.current_byte
                        chunk.current_byte += data_len
                        self.total_downloaded_bytes += data_len
                        bytes_since_last_db_commit += data_len
                        self.watchdog.heartbeat(worker_id)

                        # Zero-lock positional write directly to file offset
                        self.writer.write_at(offset, data)

                        # Checkpoint written bytes periodically to SQLite WAL catalog
                        if bytes_since_last_db_commit >= db_commit_interval:
                            await self.catalog.update_segment_progress(
                                segment_id=chunk.segment_id,
                                written_bytes=chunk.current_byte - chunk.start_byte,
                                is_done=False,
                            )
                            bytes_since_last_db_commit = 0

                        if chunk.current_byte > chunk.end_byte:
                            chunk.is_completed = True
                            break

                    if chunk.current_byte >= chunk.end_byte:
                        chunk.is_completed = True
                        await self.catalog.update_segment_progress(
                            segment_id=chunk.segment_id,
                            written_bytes=chunk.end_byte - chunk.start_byte + 1,
                            is_done=True,
                        )
                        resp.close()
                        return

                elif resp.status == 416:
                    # Range satisfied
                    chunk.is_completed = True
                    resp.close()
                    return
                else:
                    retries += 1
                    backoff = min(5.0, (0.5 + retries * 0.5 + random.uniform(0, 0.5)))
                    await asyncio.sleep(backoff)

            except asyncio.CancelledError:
                if resp is not None:
                    resp.close()
                raise
            except Exception:
                retries += 1
                if retries > max_retries:
                    break
                backoff = min(5.0, (0.5 + retries * 0.5 + random.uniform(0, 0.5)))
                await asyncio.sleep(backoff)
            finally:
                if resp is not None:
                    resp.close()

            if chunk.current_byte >= chunk.end_byte:
                chunk.is_completed = True
                return

    async def _worker_loop(self, session: aiohttp.ClientSession, worker_id: int):
        """Worker task with work-stealing from slowest donor tasks."""
        while not self.stop_event.is_set():
            target_chunk: Optional[ActiveChunk] = None

            async with self._lock:
                # 1. Look for unassigned chunk
                for c in self.chunks:
                    if not c.is_completed and not c.in_progress:
                        c.in_progress = True
                        target_chunk = c
                        break

                # 2. Work-Stealing: Find donor with at least 2MB remaining
                if not target_chunk:
                    candidates = [
                        c for c in self.chunks
                        if not c.is_completed and (c.end_byte - c.current_byte) > (2 * 1024 * 1024)
                    ]
                    if candidates:
                        donor = max(candidates, key=lambda c: c.end_byte - c.current_byte)
                        remaining = donor.end_byte - donor.current_byte
                        mid = donor.current_byte + (remaining // 2)
                        stolen_chunk = ActiveChunk(
                            chunk_id=len(self.chunks),
                            segment_id=f"{self.download_id}_{len(self.chunks)}",
                            start_byte=mid + 1,
                            end_byte=donor.end_byte,
                            current_byte=mid + 1,
                            is_completed=False,
                            in_progress=True,
                        )
                        donor.end_byte = mid
                        self.chunks.append(stolen_chunk)
                        target_chunk = stolen_chunk

            if not target_chunk:
                if all(c.is_completed for c in self.chunks):
                    break
                await asyncio.sleep(0.1)
                continue

            await self._download_chunk_stream(session, worker_id, target_chunk)
            target_chunk.in_progress = False

    async def start(self) -> bool:
        """Execute parallel download session."""
        set_windows_keep_awake(True)
        self.writer.open()
        await self._init_catalog_and_chunks()
        self.start_time = time.perf_counter()

        await self.catalog.update_download_status(self.download_id, "downloading")

        try:
            async with TunedClientSession.create_session(concurrency=self.concurrency) as session:
                workers = [
                    asyncio.create_task(self._worker_loop(session, i))
                    for i in range(self.concurrency)
                ]

                last_time = self.start_time
                last_bytes = self.total_downloaded_bytes
                last_progress_time = time.monotonic()

                while not all(c.is_completed for c in self.chunks) and not self.stop_event.is_set():
                    await asyncio.sleep(0.2)
                    now = time.perf_counter()
                    dt = now - last_time
                    delta_bytes = self.total_downloaded_bytes - last_bytes

                    if delta_bytes > 0:
                        last_progress_time = time.monotonic()
                    elif (time.monotonic() - last_progress_time) > 25.0:
                        # Stalled for 25 seconds with 0 bytes downloaded across all workers!
                        # Trigger dynamic token refresh to obtain a fresh direct URL
                        if self.token_refresh_callback:
                            try:
                                refreshed_url = await self.token_refresh_callback()
                                if refreshed_url and refreshed_url != self.url:
                                    self.url = refreshed_url
                            except Exception:
                                pass
                        last_progress_time = time.monotonic()

                    instant_mbps = (delta_bytes * 8.0) / (dt * 1_000_000.0) if dt > 0 else 0.0
                    elapsed_total = now - self.start_time
                    avg_mbps = (self.total_downloaded_bytes * 8.0) / (elapsed_total * 1_000_000.0) if elapsed_total > 0 else 0.0

                    remaining_bytes = max(0, self.total_size - self.total_downloaded_bytes)
                    eta_seconds = (remaining_bytes * 8.0) / (avg_mbps * 1_000_000.0) if avg_mbps > 0 else 0.0
                    pct = (self.total_downloaded_bytes / max(1, self.total_size)) * 100.0

                    if self.progress_callback:
                        self.progress_callback({
                            "downloaded_bytes": self.total_downloaded_bytes,
                            "total_bytes": self.total_size,
                            "instant_mbps": instant_mbps,
                            "avg_mbps": avg_mbps,
                            "progress_pct": min(100.0, pct),
                            "eta_seconds": eta_seconds,
                            "elapsed_seconds": elapsed_total,
                            "chunks_completed": sum(1 for c in self.chunks if c.is_completed),
                            "total_chunks": len(self.chunks),
                        })

                    last_time = now
                    last_bytes = self.total_downloaded_bytes

                await asyncio.gather(*workers, return_exceptions=True)

        finally:
            self.writer.close()
            set_windows_keep_awake(False)

        is_success = self.total_downloaded_bytes >= self.total_size or all(c.is_completed for c in self.chunks)
        await self.catalog.update_download_status(
            self.download_id, "completed" if is_success else "paused"
        )
        return is_success
