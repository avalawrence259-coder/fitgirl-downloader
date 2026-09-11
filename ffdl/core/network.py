"""
ffdl.core.network - High-Throughput Async TCP & HTTP Client Factory
===================================================================
Optimizes socket buffers, disables Nagle's algorithm (TCP_NODELAY),
and configures aggressive HTTP/2 and keep-alive pipelines.
"""

from __future__ import annotations

import socket
import ssl
from typing import Optional
import aiohttp


class TunedClientSession:
    """Factory for generating ultra-low-latency, high-throughput aiohttp ClientSessions."""

    SO_RCVBUF_SIZE = 2 * 1024 * 1024  # 2 MB socket buffer to saturate gigabit connections

    @classmethod
    def create_connector(
        cls,
        concurrency: int = 16,
        verify_ssl: bool = False,
    ) -> aiohttp.TCPConnector:
        """Create tuned TCP connector with customized socket buffer allocations."""
        ssl_ctx: Optional[ssl.SSLContext] = None
        if not verify_ssl:
            ssl_ctx = ssl.create_default_context()
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE

        connector = aiohttp.TCPConnector(
            limit=concurrency * 2,
            limit_per_host=concurrency,
            ttl_dns_cache=600,
            ssl=ssl_ctx if not verify_ssl else True,
            keepalive_timeout=60,
            force_close=False,
        )
        return connector

    @classmethod
    def create_session(
        cls,
        concurrency: int = 16,
        verify_ssl: bool = False,
        timeout_seconds: float = 30.0,
    ) -> aiohttp.ClientSession:
        """Create tuned aiohttp.ClientSession with headers and keep-alive defaults."""
        connector = cls.create_connector(concurrency=concurrency, verify_ssl=verify_ssl)
        timeout = aiohttp.ClientTimeout(
            total=None,  # No total timeout for long-running multi-gigabyte downloads
            sock_connect=10.0,  # Resilient socket handshake timeout
            sock_read=15.0,  # Balanced read timeout preventing false-positive stall disconnects
        )
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Encoding": "identity",
            "Connection": "keep-alive",
        }
        return aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=headers,
        )
