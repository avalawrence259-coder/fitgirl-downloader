"""
ffdl.cli - Master Command-Line Interface (Peak God Edition)
===========================================================
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import List, Optional
import click
import urllib.parse

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from rich.console import Console
from rich.live import Live
from rich.panel import Panel

from ffdl.batch import extract_urls_from_text, parse_urls_from_file, parse_urls_from_stdin
from ffdl.core.engine import ParallelDownloadEngine
from ffdl.interactive import display_banner, interactive_choose_mirror, run_interactive_wizard
from ffdl.persistence.catalog import DownloadCatalog
from ffdl.persistence.resumer import DownloadResumer
from ffdl.resolvers.cloud_fallback import FirecrawlClient
from ffdl.resolvers.datanodes import DirectHostResolver
from ffdl.resolvers.dispatcher import URLDispatcher
from ffdl.resolvers.fitgirl_scraper import FitGirlPageScraper
from ffdl.speedtest import execute_speedtest
from ffdl.ui import create_download_panel, format_bytes, format_time

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        import ctypes
        kernel32 = ctypes.windll.kernel32
        h_out = kernel32.GetStdHandle(-11)
        mode = ctypes.c_ulong()
        if kernel32.GetConsoleMode(h_out, ctypes.byref(mode)):
            kernel32.SetConsoleMode(h_out, mode.value | 0x0004)
    except Exception:
        pass

console = Console()


def resolve_output_directory(output_dir: Optional[str] = None) -> Path:
    """
    Safely resolves the download destination directory.
    Guarantees write permissions: if output_dir is default/relative and cwd
    is system32 or non-writable, automatically routes to ~/Downloads.
    """
    from ffdl.persistence.resumer import load_user_config
    cfg = load_user_config()
    cfg_out = cfg.get("output_dir")

    candidate: Path
    if output_dir and output_dir != "./downloads":
        candidate = Path(output_dir).expanduser()
    elif cfg_out:
        candidate = Path(cfg_out).expanduser()
    else:
        candidate = Path.home() / "Downloads"

    # Block dangerous system paths
    cand_resolved = str(candidate.resolve()).lower()
    if any(p in cand_resolved for p in ("system32", "syswow64", "windows\\system")):
        candidate = Path.home() / "Downloads"

    try:
        candidate.mkdir(parents=True, exist_ok=True)
        return candidate
    except (PermissionError, OSError):
        fallback = Path.home() / "Downloads"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


async def execute_download_job(
    url: str,
    output_dir: Path,
    concurrency: int = 16,
    chunk_kb: int = 256,
    overwrite: bool = False,
    info_only: bool = False,
    links_only: bool = False,
    item_index: Optional[int] = None,
    total_items: Optional[int] = None,
) -> bool:
    """Resolve direct link, preallocate, and run accelerated parallel streams."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Fast Smart Memory check before resolving network/browser challenges
    if not overwrite and "#" in url:
        early_name = url.split("#")[-1]
        early_path = output_dir / early_name
        if early_path.exists() and early_path.stat().st_size > 0:
            resumer = DownloadResumer()
            if await resumer.is_download_complete(early_path, early_path.stat().st_size):
                sz = early_path.stat().st_size
                console.print(
                    f"[bold green]⚡ Smart Memory: [bold white]{early_name}[/bold white] already complete on disk "
                    f"({format_bytes(sz)}). Skipped in 0.001s![/bold green]"
                )
                return True

    resolved = await URLDispatcher.resolve_target(url)

    # 1. Magnet URI handling
    if resolved.get("type") == "magnet":
        data = resolved.get("data", {})
        console.print(f"\n[bold magenta]🧲 Torrent Magnet URI Detected[/bold magenta]")
        console.print(f" • [bold white]Name:[/bold white] {data.get('name', 'Unknown')}")
        console.print(f" • [bold white]Hash:[/bold white] {data.get('hash', 'N/A')}")
        console.print(f" • [bold white]Trackers:[/bold white] {len(data.get('trackers', []))} tracker(s)")
        console.print(f" • [dim]Magnet: {url}[/dim]\n")
        return True

    target_url = url
    filename = "download.bin"
    total_size = 0

    if resolved.get("type") == "fuckingfast":
        target_url = resolved["direct_url"]
        probe = resolved.get("probe", {})
        if probe.get("size_bytes", 0) > 0:
            total_size = probe["size_bytes"]
        if probe.get("direct_url"):
            target_url = probe["direct_url"]
    elif resolved.get("type") in ("datanodes", "filekeeper", "generic_direct"):
        probe = resolved.get("probe", {})
        target_url = probe.get("direct_url", url)
        filename = probe.get("filename", "download.bin")
        total_size = probe.get("size_bytes", 0)

    if "#" in url:
        filename = url.split("#")[-1]
    elif filename == "download.bin" or "." not in filename:
        orig_cand = url.split("#")[0].split("?")[0].split("/")[-1]
        if orig_cand and "." in orig_cand:
            filename = orig_cand
        elif "/" in target_url:
            cand = target_url.split("?")[0].split("/")[-1]
            if cand and len(cand) > 3:
                filename = cand

    dest_path = output_dir / filename

    # 2. Links-Only Mode (instant output)
    if links_only:
        console.print(target_url)
        return True

    # Probe size if not resolved yet
    if total_size <= 0:
        probe = await DirectHostResolver.probe_direct_url(target_url)
        total_size = probe.get("size_bytes", 0)
        if probe.get("direct_url"):
            target_url = probe["direct_url"]
        if probe.get("filename") and filename == "download.bin":
            filename = probe["filename"]
            dest_path = output_dir / filename

    # 3. Info-Only Mode
    if info_only:
        console.print(f"\n[bold cyan]ℹ️ TARGET METADATA[/bold cyan]")
        console.print(f" • [bold white]Filename:[/bold white] {filename}")
        console.print(f" • [bold white]Size:[/bold white] {format_bytes(total_size)} ({total_size:,} bytes)")
        console.print(f" • [bold white]Target URL:[/bold white] {target_url}")
        console.print(f" • [bold white]Destination:[/bold white] {dest_path}\n")
        return True

    if total_size <= 0:
        console.print(f"[bold red]❌ Failed to resolve content size for: {url}[/bold red]")
        return False

    # 4. Smart Memory 0.01s Skip
    if not overwrite:
        resumer = DownloadResumer()
        if await resumer.is_download_complete(dest_path, total_size):
            console.print(
                f"[bold green]⚡ Smart Memory: [bold white]{filename}[/bold white] already complete on disk "
                f"({format_bytes(total_size)}). Skipped in 0.01s![/bold green]"
            )
            return True

    console.print(f"\n[bold green]✔ Target File:[/bold green] [bold white]{filename}[/bold white] ({format_bytes(total_size)})")
    console.print(f" • [dim]Direct CDN URL: {target_url[:75]}...[/dim]")

    stats = {
        "downloaded_bytes": 0,
        "total_bytes": total_size,
        "instant_mbps": 0.0,
        "avg_mbps": 0.0,
        "progress_pct": 0.0,
        "eta_seconds": 0.0,
        "elapsed_seconds": 0.0,
        "chunks_completed": 0,
        "total_chunks": concurrency,
    }

    async def token_refresher() -> str:
        """Dynamic token auto-refresher if CDN link expires mid-download."""
        try:
            res = await URLDispatcher.resolve_target(url)
            if res.get("direct_url"):
                return res["direct_url"]
        except Exception:
            pass
        return url

    engine = ParallelDownloadEngine(
        url=target_url,
        destination_path=dest_path,
        total_size=total_size,
        concurrency=concurrency,
        chunk_buffer_kb=chunk_kb,
        progress_callback=lambda s: stats.update(s),
        token_refresh_callback=token_refresher,
    )

    if console.is_terminal:
        with Live(
            create_download_panel(filename, stats, item_index, total_items),
            console=console,
            refresh_per_second=4,
            transient=True,
        ) as live:
            async def ui_updater():
                while not engine.stop_event.is_set() and stats["progress_pct"] < 100.0:
                    live.update(create_download_panel(filename, stats, item_index, total_items))
                    await asyncio.sleep(0.25)
                live.update(create_download_panel(filename, stats, item_index, total_items))

            ui_task = asyncio.create_task(ui_updater())
            success = await engine.start()
            engine.stop_event.set()
            await ui_task
    else:
        # Clean progress logging when output is redirected or piped
        async def ui_updater_simple():
            last_pct = -5.0
            while not engine.stop_event.is_set() and stats["progress_pct"] < 100.0:
                pct = stats["progress_pct"]
                if pct - last_pct >= 5.0:
                    last_pct = pct
                    console.print(
                        f" • [{item_index}/{total_items}] {filename} — {pct:>5.1f}% "
                        f"({format_bytes(stats['downloaded_bytes'])}/{format_bytes(total_size)}) "
                        f"| {stats['instant_mbps']/8:>5.2f} MB/s | ETA: {format_time(int(stats['eta_seconds']))}"
                    )
                await asyncio.sleep(0.5)

        ui_task = asyncio.create_task(ui_updater_simple())
        success = await engine.start()
        engine.stop_event.set()
        await ui_task

    if success:
        console.print(f"[bold green]🎉 Download Complete: {dest_path}[/bold green]\n")
        return True
    return False


def sync_download_wrapper(
    url: str,
    output_dir: Path,
    idx: int = 1,
    total: int = 1,
    concurrency: int = 16,
    chunk_kb: int = 256,
    overwrite: bool = False,
    info_only: bool = False,
    links_only: bool = False,
):
    asyncio.run(
        execute_download_job(
            url,
            output_dir,
            concurrency=concurrency,
            chunk_kb=chunk_kb,
            overwrite=overwrite,
            info_only=info_only,
            links_only=links_only,
            item_index=idx,
            total_items=total,
        )
    )


@click.command()
@click.argument("targets", nargs=-1)
@click.option("-i", "--interactive", is_flag=True, help="Launch interactive visual wizard")
@click.option("-o", "--output", "output_dir", default="./downloads", help="Destination folder (default: ./downloads)")
@click.option("-c", "--concurrency", default=16, help="Worker concurrency streams (default: 16)")
@click.option("--chunk-kb", default=256, help="Buffer chunk size in KB (default: 256)")
@click.option("-f", "--file", "url_file", type=click.Path(exists=True), help="Read links from text/html/bbcode file")
@click.option("-p", "--paste", "paste_text", help="Raw HTML snippet or pasted text containing links")
@click.option("-w", "--overwrite", is_flag=True, help="Force re-download and overwrite existing files")
@click.option("-s", "--scrape", is_flag=True, help="Use Firecrawl to scrape links from web pages")
@click.option("--speedtest", is_flag=True, help="Run network bandwidth test & calibration")
@click.option("--info", "info_only", is_flag=True, help="Probe file size and metadata without downloading")
@click.option("--links-only", is_flag=True, help="Resolve and print direct CDN download URLs only")
@click.option("--main-only", is_flag=True, help="Download only required main parts (skips optional addons/languages)")
@click.option("--all-parts", "--all", "all_parts", is_flag=True, help="Download all parts including all optional addons")
@click.option("--select", "select_optionals", help="Comma-separated optional indices or keywords to include (e.g. 'french,ost' or '1,3')")
@click.option("--hoster", default="", help="Pre-select specific mirror hoster (e.g. fuckingfast, datanodes, filekeeper, magnet)")
@click.option("--downloader", default="", help="Downloader engine to use (ffdl, idm, fdm, aria2)")
@click.option("--idm", is_flag=True, help="Dispatch downloads directly to Internet Download Manager (IDM)")
@click.option("--fdm", is_flag=True, help="Dispatch downloads directly to Free Download Manager (FDM)")
@click.option("--aria2", is_flag=True, help="Dispatch downloads directly to Aria2c CLI")
@click.option("--auto", is_flag=True, help="Auto-download all parted files sequentially without manual confirmation prompts")
@click.option("--register-protocol", is_flag=True, help="Register ffdl:// deep-link protocol in Windows Registry")
@click.option("--unregister-protocol", is_flag=True, help="Unregister ffdl:// protocol from Windows Registry")
@click.option("--daemon", "--serve", "run_daemon", is_flag=True, help="Run background micro HTTP daemon on port 45732 for browser extension")
@click.option("--bridge", "run_bridge", is_flag=True, help="Run authenticated Native Messaging / RPC daemon on port 41194")
@click.option("--install-bridge", "install_bridge_flag", is_flag=True, help="Install Native Messaging Host and Registry keys for Chrome/Edge/Firefox")
@click.option("--extension-id", default="", help="Chrome/Edge/Firefox extension ID to authorize in Native Messaging")
def main(
    targets,
    interactive,
    output_dir,
    concurrency,
    chunk_kb,
    url_file,
    paste_text,
    overwrite,
    scrape,
    speedtest,
    info_only,
    links_only,
    main_only,
    all_parts,
    select_optionals,
    hoster,
    downloader,
    idm,
    fdm,
    aria2,
    auto,
    register_protocol,
    unregister_protocol,
    run_daemon,
    run_bridge,
    install_bridge_flag,
    extension_id,
):
    """⚡ FFDL: Peak God Level Multi-Part Download Accelerator for FitGirl Repacks"""
    if install_bridge_flag:
        from ffdl.bridge.installer import install_bridge
        display_banner()
        res = install_bridge(extension_id=extension_id)
        console.print("[bold green]✔ Successfully installed FFDL Native Messaging Bridge![/bold green]")
        console.print(f" • [bold white]Launcher:[/bold white] {res['launcher']}")
        console.print(f" • [bold white]Chrome/Edge Registry:[/bold white] {'Installed' if res['chrome_installed'] else 'Skipped'}")
        console.print(f" • [bold white]Firefox Registry:[/bold white] {'Installed' if res['firefox_installed'] else 'Skipped'}")
        console.print(f" • [bold white]Bearer Token:[/bold white] [cyan]{res['auth_token']}[/cyan]\n")
        return

    if run_bridge:
        from ffdl.bridge.server import BridgeServer
        from ffdl.bridge.auth import get_or_create_auth_token
        display_banner()
        out_path = resolve_output_directory(output_dir)
        token = get_or_create_auth_token()
        console.print(f"\n[bold green]⚡ FFDL Bridge Daemon listening on http://127.0.0.1:41194[/bold green]")
        console.print(f"🔑 [bold white]Auth Bearer Token:[/bold white] [cyan]{token}[/cyan]")
        console.print("📡 Ready to receive download jobs from Browser Companion Extension...\n")

        def bridge_job_callback(job_data):
            target_u = job_data.get("url", "")
            pref_h = job_data.get("hoster", "")
            m_only = job_data.get("main_only", False)
            a_parts = job_data.get("all", False)
            console.print(f"\n[bold green]📥 Received job from Browser Extension:[/bold green] [bold white]{target_u}[/bold white] [cyan][{pref_h}][/cyan]")
            resolved = asyncio.run(URLDispatcher.resolve_target(target_u, preferred_hoster=pref_h))
            if resolved.get("type") == "fitgirl_page":
                to_dl = interactive_choose_mirror(
                    resolved["data"],
                    main_only=m_only,
                    all_parts=a_parts,
                    preferred_hoster=pref_h,
                )
                for idx, u in enumerate(to_dl, 1):
                    sync_download_wrapper(u, out_path, idx=idx, total=len(to_dl), concurrency=concurrency, chunk_kb=chunk_kb)
            else:
                sync_download_wrapper(target_u, out_path, 1, 1, concurrency=concurrency, chunk_kb=chunk_kb)
            return {"status": "dispatched"}

        srv = BridgeServer(port=41194, callback=bridge_job_callback)
        try:
            srv.start()
        except KeyboardInterrupt:
            pass
        finally:
            srv.shutdown()
        return
    if register_protocol:
        from ffdl.protocol import register_windows_protocol
        display_banner()
        if register_windows_protocol():
            console.print("[bold green]✔ Successfully registered ffdl:// deep-link protocol in Windows Registry![/bold green]")
            console.print("[dim]Clicking download buttons in your browser will now launch FFDL automatically.[/dim]\n")
        else:
            console.print("[bold red]❌ Failed to register protocol (Windows required).[/bold red]\n")
        return

    if unregister_protocol:
        from ffdl.protocol import unregister_windows_protocol
        display_banner()
        if unregister_windows_protocol():
            console.print("[bold green]✔ Successfully unregistered ffdl:// protocol from Windows Registry.[/bold green]\n")
        else:
            console.print("[bold red]❌ Failed to unregister protocol.[/bold red]\n")
        return

    if run_daemon:
        from ffdl.daemon import run_daemon_server
        display_banner()
        out_path = resolve_output_directory(output_dir)

        def daemon_job_callback(job_data):
            target_u = job_data.get("url", "")
            pref_h = job_data.get("hoster", "")
            m_only = job_data.get("main_only", False)
            a_parts = job_data.get("all", False)
            console.print(f"\n[bold green]📥 Received job from Browser Extension:[/bold green] [bold white]{target_u}[/bold white] [cyan][{pref_h}][/cyan]")
            resolved = asyncio.run(URLDispatcher.resolve_target(target_u, preferred_hoster=pref_h))
            if resolved.get("type") == "fitgirl_page":
                to_dl = interactive_choose_mirror(
                    resolved["data"],
                    main_only=m_only,
                    all_parts=a_parts,
                    preferred_hoster=pref_h,
                )
                for idx, u in enumerate(to_dl, 1):
                    sync_download_wrapper(u, out_path, idx=idx, total=len(to_dl), concurrency=concurrency, chunk_kb=chunk_kb)
            else:
                sync_download_wrapper(target_u, out_path, 1, 1, concurrency=concurrency, chunk_kb=chunk_kb)

        run_daemon_server(callback=daemon_job_callback)
        return

    if speedtest:
        display_banner()
        asyncio.run(execute_speedtest())
        return

    # Check for ffdl:// protocol deep link targets
    is_protocol_invocation = any(t.lower().startswith("ffdl://") or t.lower().startswith("ffdl:") for t in targets)
    expanded_targets = []
    for t in targets:
        if t.lower().startswith("ffdl://") or t.lower().startswith("ffdl:"):
            from ffdl.protocol import parse_protocol_url
            p_info = parse_protocol_url(t)
            if p_info.get("url"):
                expanded_targets.append(p_info["url"])
            if p_info.get("hoster"):
                hoster = p_info["hoster"]
            if p_info.get("main_only"):
                main_only = True
            if p_info.get("all_parts"):
                all_parts = True
            if p_info.get("select"):
                select_optionals = p_info["select"]
            if p_info.get("out_dir"):
                output_dir = p_info["out_dir"]
            if p_info.get("downloader"):
                downloader = p_info["downloader"]
            if p_info.get("auto"):
                auto = True
        else:
            expanded_targets.append(t)
    targets = tuple(expanded_targets)

    if auto:
        if not all_parts and not select_optionals:
            main_only = True

    if interactive or (not targets and not url_file and not paste_text and sys.stdin.isatty()):
        run_interactive_wizard(
            lambda u, out, i, tot: sync_download_wrapper(
                u, out, i, tot, concurrency=concurrency, chunk_kb=chunk_kb, overwrite=overwrite
            )
        )
        return

    if not links_only:
        display_banner()

    out_path = resolve_output_directory(output_dir)

    urls_to_download: List[str] = []

    for t in targets:
        if scrape:
            fc_data = asyncio.run(FirecrawlClient.scrape_page(t))
            for link in fc_data.get("links", []):
                urls_to_download.extend(extract_urls_from_text(link))
            if not urls_to_download and fc_data.get("markdown"):
                urls_to_download.extend(extract_urls_from_text(fc_data["markdown"]))
        elif "fitgirl-repacks.site" in (urllib.parse.urlparse(t).netloc or "").lower() and not "paste." in (urllib.parse.urlparse(t).netloc or "").lower():
            # Game post page
            resolved = asyncio.run(URLDispatcher.resolve_target(t, preferred_hoster=hoster))
            if resolved.get("type") == "fitgirl_page":
                chosen = interactive_choose_mirror(
                    resolved["data"],
                    main_only=main_only,
                    all_parts=all_parts,
                    select_optionals=select_optionals,
                    preferred_hoster=hoster,
                )
                urls_to_download.extend(chosen)
        else:
            urls_to_download.extend(extract_urls_from_text(t) or [t])

    if paste_text:
        urls_to_download.extend(extract_urls_from_text(paste_text))

    if url_file:
        urls_to_download.extend(parse_urls_from_file(Path(url_file)))

    if not urls_to_download and not sys.stdin.isatty():
        urls_to_download.extend(parse_urls_from_stdin())

    if not urls_to_download:
        console.print("[bold red]❌ No targets provided. Run 'ffdl -i' for interactive wizard.[/bold red]")
        sys.exit(1)

    if not links_only:
        console.print(f"\n[bold green]🚀 Queueing {len(urls_to_download)} Item(s) for Processing...[/bold green]")

    # Downloader Selection & Dispatch
    selected_downloader = "ffdl"
    if idm:
        selected_downloader = "idm"
    elif fdm:
        selected_downloader = "fdm"
    elif aria2:
        selected_downloader = "aria2"
    elif downloader:
        selected_downloader = downloader.lower()
    elif not links_only and not info_only:
        from ffdl.interactive import choose_downloader_engine
        selected_downloader = choose_downloader_engine(preferred=downloader)

    if selected_downloader == "idm":
        from ffdl.downloaders.detector import DownloaderDetector
        from ffdl.downloaders.dispatcher import DownloaderDispatcher
        idm_exe = DownloaderDetector.find_idm_path()
        if idm_exe:
            asyncio.run(DownloaderDispatcher.dispatch_to_idm(idm_exe, urls_to_download, out_path, start_queue=True))
            if is_protocol_invocation:
                console.print("\n[bold green]✔ All download tasks queued in IDM![/bold green]")
                console.print("[dim]Window will remain open. Press Enter to close this window...[/dim]\n")
                try:
                    input()
                except (KeyboardInterrupt, EOFError):
                    pass
            return
        else:
            console.print("[bold red]❌ IDM not found on your system! Falling back to FFDL.[/bold red]")
            selected_downloader = "ffdl"
    elif selected_downloader == "fdm":
        from ffdl.downloaders.detector import DownloaderDetector
        from ffdl.downloaders.dispatcher import DownloaderDispatcher
        fdm_exe = DownloaderDetector.find_fdm_path()
        if fdm_exe:
            asyncio.run(DownloaderDispatcher.dispatch_to_fdm(fdm_exe, urls_to_download, out_path))
            return
        else:
            console.print("[bold red]❌ FDM not found on your system! Falling back to FFDL.[/bold red]")
            selected_downloader = "ffdl"
    elif selected_downloader == "aria2":
        from ffdl.downloaders.detector import DownloaderDetector
        from ffdl.downloaders.dispatcher import DownloaderDispatcher
        aria2_exe = DownloaderDetector.find_aria2_path()
        if aria2_exe:
            asyncio.run(DownloaderDispatcher.dispatch_to_aria2(aria2_exe, urls_to_download, out_path, concurrency=concurrency))
            return
        else:
            console.print("[bold red]❌ Aria2 not found on your system! Falling back to FFDL.[/bold red]")
            selected_downloader = "ffdl"

    for idx, u in enumerate(urls_to_download, 1):
        sync_download_wrapper(
            u,
            out_path,
            idx=idx,
            total=len(urls_to_download),
            concurrency=concurrency,
            chunk_kb=chunk_kb,
            overwrite=overwrite,
            info_only=info_only,
            links_only=links_only,
        )

    if is_protocol_invocation:
        console.print("\n[bold green]✔ All download tasks completed![/bold green]")
        console.print("[dim]Window will remain open. Press Enter to close this window...[/dim]\n")
        try:
            input()
        except (KeyboardInterrupt, EOFError):
            pass
