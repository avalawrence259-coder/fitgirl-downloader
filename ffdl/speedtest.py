"""
FF-Downloader Built-In Network & Internet Speed Tester
Measures true downstream bandwidth, latency, jitter, and CDN edge throughput to auto-calibrate optimal worker concurrency.
"""

import time
import asyncio
import httpx
from typing import Dict, Any, Tuple
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, DownloadColumn, TransferSpeedColumn
from rich import box

console = Console(force_terminal=True, legacy_windows=False)

# Fast, reliable CDN speedtest endpoints (Cloudflare Speedtest & CDN Edge)
SPEEDTEST_URLS = [
    "https://speed.cloudflare.com/__down?bytes=50000000",   # 50 MB payload
    "https://speed.cloudflare.com/__down?bytes=25000000",   # 25 MB payload
    "https://speed.cloudflare.com/__down?bytes=10000000",   # 10 MB payload
]

PING_TARGETS = [
    "https://speed.cloudflare.com/__down?bytes=0",
    "https://dl.fuckingfast.co",
    "https://1.1.1.1",
]


async def measure_ping_and_jitter() -> Tuple[float, float]:
    """Measure latency and jitter to edge CDN servers."""
    latencies = []
    headers = {"User-Agent": "Mozilla/5.0"}
    async with httpx.AsyncClient(timeout=5.0, verify=False) as client:
        for _ in range(4):
            for target in PING_TARGETS:
                try:
                    t0 = time.perf_counter()
                    resp = await client.get(target, headers=headers)
                    t1 = time.perf_counter()
                    if resp.status_code < 500:
                        latencies.append((t1 - t0) * 1000.0)
                except Exception:
                    pass

    if not latencies:
        return 50.0, 5.0

    avg_ping = sum(latencies) / len(latencies)
    jitter = sum(abs(l - avg_ping) for l in latencies) / len(latencies)
    return avg_ping, jitter


async def run_bandwidth_test(progress: Progress, task_id) -> Dict[str, float]:
    """Stream high-speed test payload from Cloudflare CDN edge to measure raw ISP downstream speed."""
    url = SPEEDTEST_URLS[0]
    total_bytes = 50 * 1024 * 1024
    received_bytes = 0
    start_time = time.perf_counter()

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    try:
        async with httpx.AsyncClient(timeout=25.0, verify=False) as client:
            async with client.stream("GET", url, headers=headers) as resp:
                if resp.status_code == 200:
                    async for chunk in resp.aiter_bytes(chunk_size=128 * 1024):
                        received_bytes += len(chunk)
                        progress.update(task_id, completed=received_bytes, total=total_bytes)
                        # Sample first 5-8 seconds for instant calibration
                        if (time.perf_counter() - start_time) > 7.0 and received_bytes > 20 * 1024 * 1024:
                            break
    except Exception:
        pass

    elapsed = max(0.001, time.perf_counter() - start_time)
    speed_mbps = (received_bytes * 8.0) / (elapsed * 1_000_000.0)
    speed_mbs = speed_mbps / 8.0

    return {
        "bytes_received": received_bytes,
        "elapsed_seconds": elapsed,
        "speed_mbps": speed_mbps,
        "speed_mbs": speed_mbs,
    }


async def execute_speedtest() -> Dict[str, Any]:
    """Execute complete network diagnostic and benchmark."""
    console.print("\n[bold yellow]⚡ LAUNCHING NETWORK SPEED & CDN DIAGNOSTIC[/bold yellow]\n")

    # 1. Measure Latency
    with Progress(SpinnerColumn(), TextColumn("[bold cyan]Measuring CDN Edge Latency & Jitter..."), console=console) as prog:
        t = prog.add_task("ping", total=None)
        ping, jitter = await measure_ping_and_jitter()
        prog.update(t, completed=True)

    # 2. Measure Download Bandwidth
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]Benchmarking Download Throughput..."),
        BarColumn(bar_width=30, style="cyan", complete_style="bright_green"),
        DownloadColumn(),
        TransferSpeedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("download", total=50 * 1024 * 1024)
        dl_res = await run_bandwidth_test(progress, task)

    speed_mbps = dl_res["speed_mbps"]
    speed_mbs = dl_res["speed_mbs"]

    # Calculate optimal recommended concurrency
    if speed_mbps >= 250:
        recommended_concurrency = 32
        recommended_chunk_kb = 512
        tier = "Gigabit / Ultra-High Speed Fiber"
    elif speed_mbps >= 80:
        recommended_concurrency = 16
        recommended_chunk_kb = 256
        tier = "High Speed Broadband (100 Mbps+)"
    elif speed_mbps >= 25:
        recommended_concurrency = 8
        recommended_chunk_kb = 256
        tier = "Standard Broadband (25-50 Mbps)"
    else:
        recommended_concurrency = 6
        recommended_chunk_kb = 128
        tier = "Moderate / Metered Connection (< 25 Mbps)"

    # Render Report Table
    table = Table(box=box.ROUNDED, border_style="cyan")
    table.add_column("Metric", style="bold white")
    table.add_column("Measured Value", style="bold green")
    table.add_column("Network Assessment", style="dim")

    table.add_row("⚡ Download Speed (MB/s)", f"[bold bright_green]{speed_mbs:.2f} MB/s[/bold bright_green]", f"{speed_mbps:.1f} Mbps throughput")
    table.add_row("🌐 Network Tier", f"[bold cyan]{tier}[/bold cyan]", "Bandwidth classification")
    table.add_row("⏱️ Edge Latency (Ping)", f"{ping:.1f} ms", "Round-trip time to CDN edge")
    table.add_row("📊 Network Jitter", f"{jitter:.1f} ms", "Latency stability variance")
    table.add_row("🚀 Optimal Concurrency", f"[bold yellow]{recommended_concurrency} streams[/bold yellow]", f"Buffer: {recommended_chunk_kb} KB")

    console.print(Panel(table, title="[bold yellow]⚡ SPEED TEST & CALIBRATION RESULTS[/bold yellow]", border_style="bright_green"))

    return {
        "speed_mbps": speed_mbps,
        "speed_mbs": speed_mbs,
        "ping_ms": ping,
        "jitter_ms": jitter,
        "recommended_concurrency": recommended_concurrency,
        "recommended_chunk_kb": recommended_chunk_kb,
        "tier": tier,
    }
