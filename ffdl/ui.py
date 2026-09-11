"""
ffdl.ui - Cyberpunk Visual Terminal Dashboard & Live Progress Maps
===================================================================
Renders real-time throughput metrics, instant vs average MB/s, ETA,
multi-part queue status, and active stream block maps.
"""

from __future__ import annotations

import sys
from typing import Any, Dict, List, Optional
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console(force_terminal=True, legacy_windows=False)


def format_bytes(num_bytes: int) -> str:
    """Format integer bytes to clean human-readable notation (B, KB, MB, GB, TB)."""
    if num_bytes >= 1024 * 1024 * 1024 * 1024:
        return f"{num_bytes / (1024 * 1024 * 1024 * 1024):.2f} TB"
    elif num_bytes >= 1024 * 1024 * 1024:
        return f"{num_bytes / (1024 * 1024 * 1024):.2f} GB"
    elif num_bytes >= 1024 * 1024:
        return f"{num_bytes / (1024 * 1024):.1f} MB"
    elif num_bytes >= 1024:
        return f"{num_bytes / 1024:.1f} KB"
    return f"{num_bytes} B"


def format_time(seconds: float) -> str:
    """Format seconds into HH:MM:SS or MM:SS notation."""
    seconds = int(max(0, seconds))
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def render_chunk_map(chunk_progress: List[float]) -> str:
    """Render a visual Unicode block map representing stream activity."""
    if not chunk_progress:
        return "[dim]No active streams[/dim]"

    blocks = []
    for p in chunk_progress:
        if p >= 0.99:
            blocks.append("[bold bright_green]█[/bold bright_green]")
        elif p >= 0.70:
            blocks.append("[bold green]▆[/bold green]")
        elif p >= 0.40:
            blocks.append("[bold yellow]▄[/bold yellow]")
        elif p > 0.05:
            blocks.append("[bold cyan]▂[/bold cyan]")
        else:
            blocks.append("[dim white]░[/dim white]")
    return "".join(blocks)


def create_download_panel(
    filename: str,
    stats: Dict[str, Any],
    item_index: Optional[int] = None,
    total_items: Optional[int] = None,
) -> Panel:
    """Generate a formatted Rich UI dashboard panel representing the current download state."""
    downloaded_str = format_bytes(stats.get("downloaded_bytes", 0))
    total_str = format_bytes(stats.get("total_bytes", 0))
    inst_mbps = stats.get("instant_mbps", 0.0)
    inst_mbs = inst_mbps / 8.0
    avg_mbps = stats.get("avg_mbps", 0.0)
    avg_mbs = avg_mbps / 8.0
    pct = stats.get("progress_pct", 0.0)
    eta_str = format_time(stats.get("eta_seconds", 0.0))
    elapsed_str = format_time(stats.get("elapsed_seconds", 0.0))

    bar_width = 30
    filled = int((pct / 100.0) * bar_width)
    bar_str = "█" * filled + "░" * (bar_width - filled)

    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold white", justify="left")
    table.add_column(style="bold cyan", justify="left")

    if item_index is not None and total_items is not None and total_items > 1:
        table.add_row("📦 Queue Progress:", f"[bold magenta]Part {item_index} of {total_items}[/bold magenta]")

    table.add_row("📁 Target Archive:", f"[bold bright_green]{filename}[/bold bright_green]")
    table.add_row(
        "📊 Progress:",
        f"[bold cyan][{bar_str}][/bold cyan] [bold white]{pct:>5.1f}%[/bold white] ({downloaded_str} / {total_str})",
    )
    table.add_row(
        "⚡ Transfer Rate:",
        f"[bold bright_green]{inst_mbs:>6.2f} MB/s[/bold bright_green] ([dim]{inst_mbps:.1f} Mbps[/dim]) | Avg: [cyan]{avg_mbs:.2f} MB/s[/cyan]",
    )
    table.add_row(
        "⏱️ Timing:",
        f"ETA: [bold yellow]{eta_str}[/bold yellow] | Elapsed: [dim]{elapsed_str}[/dim]",
    )
    table.add_row(
        "🧩 Stream Chunks:",
        f"[cyan]{stats.get('chunks_completed', 0)}/{stats.get('total_chunks', 16)}[/cyan] completed",
    )

    return Panel(
        table,
        title="[bold yellow]⚡ FFDL: PEAK GOD ULTRA ACCELERATOR[/bold yellow]",
        border_style="bright_cyan",
        box=box.ROUNDED,
    )
