from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional

from rich import box
from rich.console import Console
from rich.table import Table

from ffdl.downloaders.detector import DownloaderDetector, DownloaderInfo
from ffdl.resolvers.dispatcher import URLDispatcher
from ffdl.ui import format_bytes

console = Console()


class DownloaderDispatcher:
    """
    Unified Dispatch Bridge: Dispatches parsed / parted download items
    to the user's chosen download engine (IDM, FDM, Aria2, or FFDL Built-in).
    """

    @classmethod
    async def resolve_url_info(cls, url: str) -> Dict[str, str]:
        """Resolves target to direct CDN URL and true filename."""
        try:
            res = await URLDispatcher.resolve_target(url)
            direct_url = res.get("direct_url") or url
            filename = res.get("filename")
            if not filename or filename == "archive.bin":
                from ffdl.resolvers.fitgirl_scraper import get_filename_from_url
                filename = get_filename_from_url(url)
            total_size = res.get("total_size", 0)
            return {
                "direct_url": direct_url,
                "filename": filename,
                "total_size": total_size,
            }
        except Exception:
            from ffdl.resolvers.fitgirl_scraper import get_filename_from_url
            return {
                "direct_url": url,
                "filename": get_filename_from_url(url),
                "total_size": 0,
            }

    @classmethod
    async def dispatch_to_idm(
        cls,
        idm_exe: str,
        urls: List[str],
        output_dir: Path,
        start_queue: bool = True,
    ) -> bool:
        """
        Injects all parted files separately and automatically into IDM's download queue.
        Uses /d URL /p PATH /f FILENAME /n /a, then /s to start scheduler.
        """
        output_dir = Path(output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        console.print(f"\n[bold cyan]⚡ Connecting to Internet Download Manager (IDM)...[/bold cyan]")
        console.print(f" • [dim]Executable: {idm_exe}[/dim]")
        console.print(f" • [dim]Destination: {output_dir}[/dim]")
        console.print(f" • [bold green]Auto-Queueing {len(urls)} parted file(s) separately...[/bold green]\n")

        table = Table(title="IDM DOWNLOAD QUEUE INJECTION", box=box.ROUNDED)
        table.add_column("#", style="bold cyan", width=4)
        table.add_column("Filename", style="bold white")
        table.add_column("Status", style="bold green")

        for idx, url in enumerate(urls, 1):
            info = await cls.resolve_url_info(url)
            direct_url = info["direct_url"]
            filename = info["filename"]

            # Command syntax: IDMan.exe /d "<url>" /p "<path>" /f "<filename>" /n /a
            # /n = silent mode (no dialogs)
            # /a = add to queue without immediate download dialog
            cmd = [
                idm_exe,
                "/d", direct_url,
                "/p", str(output_dir),
                "/f", filename,
                "/n",
                "/a",
            ]
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
            try:
                subprocess.run(cmd, check=True, timeout=10, creationflags=flags)
                table.add_row(str(idx), filename, "✔ Queued in IDM")
            except Exception as e:
                table.add_row(str(idx), filename, f"[red]Failed: {e}[/red]")

        console.print(table)

        if start_queue:
            # /s = start executing the active download queue
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
            try:
                subprocess.run([idm_exe, "/s"], check=False, timeout=5, creationflags=flags)
                console.print("\n[bold green]🚀 IDM Queue Started Successfully! All parts are downloading silently in IDM background.[/bold green]\n")
            except Exception as e:
                console.print(f"\n[yellow]Could not automatically trigger queue start: {e}. Open IDM and click 'Start Queue'.[/yellow]\n")

        return True

    @classmethod
    async def dispatch_to_fdm(
        cls,
        fdm_exe: str,
        urls: List[str],
        output_dir: Path,
    ) -> bool:
        """Injects all parted files into Free Download Manager."""
        output_dir = Path(output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        console.print(f"\n[bold cyan]🌐 Dispatching {len(urls)} file(s) to Free Download Manager...[/bold cyan]")
        console.print(f" • [dim]Target Folder: {output_dir}[/dim]")
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
        for idx, url in enumerate(urls, 1):
            info = await cls.resolve_url_info(url)
            cmd = [fdm_exe, info["direct_url"]]
            try:
                subprocess.Popen(cmd, creationflags=flags)
                console.print(f" • [{idx}/{len(urls)}] ✔ Sent to FDM: {info['filename']}")
            except Exception as e:
                console.print(f" • [{idx}/{len(urls)}] [red]Failed to send {info['filename']}: {e}[/red]")
        console.print("\n[bold green]✔ All items dispatched to Free Download Manager![/bold green]")
        console.print("[dim]💡 Tip: In FDM, click 'Download' to start downloading. Or use Engine [1] (FFDL Built-in) for 100% automated, zero-click background downloading.[/dim]\n")
        return True

    @classmethod
    async def dispatch_to_aria2(
        cls,
        aria2_exe: str,
        urls: List[str],
        output_dir: Path,
        concurrency: int = 16,
    ) -> bool:
        """Runs Aria2c multi-connection CLI on parted files."""
        output_dir = Path(output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        console.print(f"\n[bold cyan]🦅 Dispatching {len(urls)} file(s) to Aria2c CLI...[/bold cyan]")
        for idx, url in enumerate(urls, 1):
            info = await cls.resolve_url_info(url)
            cmd = [
                aria2_exe,
                "-x", str(concurrency),
                "-s", str(concurrency),
                "-k", "1M",
                "--dir", str(output_dir),
                "--out", info["filename"],
                info["direct_url"],
            ]
            console.print(f"\n[bold cyan]Downloading Part [{idx}/{len(urls)}]: {info['filename']}[/bold cyan]")
            proc = await asyncio.create_subprocess_exec(*cmd)
            await proc.wait()

        console.print("\n[bold green]✔ All items completed via Aria2![/bold green]\n")
        return True
