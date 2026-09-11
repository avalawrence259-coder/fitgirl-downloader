"""
ffdl.interactive - Visual Interactive Terminal Wizard & Mirror Selector
========================================================================
Interactive terminal wizard for:
- Inputting FitGirl game posts or direct download lists
- Parsing and choosing mirror hosters (FuckingFast, DataNodes, FileKeeper, Torrents)
- Selecting selective parts (e.g. download main game, omit optional languages)
- Running network speedtests and calibrating stream concurrency.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import IntPrompt, Prompt
from rich.table import Table

from ffdl.resolvers.dispatcher import URLDispatcher
from ffdl.resolvers.fitgirl_scraper import FitGirlPageScraper
from ffdl.speedtest import execute_speedtest
from ffdl.ui import format_bytes

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        # Enable ENABLE_VIRTUAL_TERMINAL_PROCESSING (0x0004)
        hOut = kernel32.GetStdHandle(-11)
        mode = ctypes.c_ulong()
        kernel32.GetConsoleMode(hOut, ctypes.byref(mode))
        kernel32.SetConsoleMode(hOut, mode.value | 0x0004)
    except Exception:
        pass

console = Console(force_terminal=True, legacy_windows=False)


def display_banner():
    header_text = (
        "[bold yellow]███████╗███████╗██████╗ ██╗     \n"
        "██╔════╝██╔════╝██╔══██╗██║     \n"
        "█████╗  █████╗  ██║  ██║██║     \n"
        "██╔══╝  ██╔══╝  ██║  ██║██║     \n"
        "██║     ██║     ██████╔╝███████╗\n"
        "╚═╝     ╚═╝     ╚═════╝ ╚══════╝[/bold yellow]\n"
        "[dim bold white]⚡ PEAK GOD ACCELERATOR — FitGirl Repacks & Multi-Part Engine[/dim bold white]"
    )
    console.print(Panel(header_text, border_style="bright_cyan", box=box.ROUNDED))


def select_repack_components(
    links: List[str],
    title: str = "",
    main_only: bool = False,
    all_parts: bool = False,
    select_optionals: Optional[str] = None,
) -> List[str]:
    """
    Intelligently partitions repack files into Required Main Game Parts and Optional Addons.
    Allows user to choose:
    1. Main parts only (saves bandwidth & skips unused languages/bonuses)
    2. Complete package (all parts)
    3. Custom selection (pick specific optionals by index or keyword)
    4. Full manual part-by-part range picker
    """
    from ffdl.resolvers.fitgirl_scraper import partition_links, get_filename_from_url
    import re

    main_links, optional_items = partition_links(links)
    if not optional_items:
        return links

    if main_only:
        console.print(f"[bold cyan]⚡ --main-only: Selected {len(main_links)} required main parts (skipping {len(optional_items)} optional addons).[/bold cyan]")
        return main_links

    if all_parts:
        console.print(f"[bold cyan]📦 --all-parts: Selected all {len(links)} parts (main + all optionals).[/bold cyan]")
        return main_links + [item["url"] for item in optional_items]

    if select_optionals:
        selected_opt_urls = []
        queries = [q.strip().lower() for q in select_optionals.split(",") if q.strip()]
        for idx, item in enumerate(optional_items, 1):
            match = False
            if str(idx) in queries:
                match = True
            else:
                for q in queries:
                    if q in item["filename"].lower() or q in item["label"].lower() or q in item["type"]:
                        match = True
                        break
            if match:
                selected_opt_urls.append(item["url"])
        console.print(f"[bold cyan]🎯 Filtered: {len(main_links)} main parts + {len(selected_opt_urls)} selected optional addons.[/bold cyan]")
        return main_links + selected_opt_urls

    # Interactive prompt
    opt_table = Table(title="OPTIONAL & SELECTIVE ADDONS DETECTED", box=box.ROUNDED)
    opt_table.add_column("#", style="bold cyan", width=4)
    opt_table.add_column("Component / Voiceover / Bonus", style="bold white")
    opt_table.add_column("Filename", style="dim cyan")
    opt_table.add_column("Category", style="yellow")

    for idx, item in enumerate(optional_items, 1):
        opt_table.add_row(str(idx), item["label"], item["filename"], item["type"].replace("_", " ").title())

    console.print(f"\n[bold green]📦 Repack Archive Structure:[/bold green]")
    console.print(f" • [bold white]Required Main Game Parts:[/bold white] [bold cyan]{len(main_links)} parts[/bold cyan] (Essential to install & run)")
    console.print(f" • [bold white]Optional / Selective Addons:[/bold white] [bold yellow]{len(optional_items)} files[/bold yellow] (Voiceovers, OST, bonus media)")
    console.print(opt_table)

    has_english = any(item.get("type") == "english_vo" or "english" in item.get("filename", "").lower() for item in optional_items)

    eng_count = len([item for item in optional_items if item.get("type") == "english_vo" or "english" in item.get("filename", "").lower()])
    menu_lines = [
        f"[bold white][1][/bold white] ⚡ [bold cyan]Main Game Only[/bold cyan] [green](Recommended)[/green] — [white]{len(main_links)} parts[/white] (Essential files to play; skips extra languages & bonus files)",
    ]
    if has_english:
        menu_lines.append(
            f"[bold white][E][/bold white] 🌟 [bold cyan]Main Game + English Voiceover[/bold cyan] — [white]{len(main_links) + eng_count} parts[/white] (Core game files + English speech pack)"
        )
    menu_lines.extend([
        f"[bold white][2][/bold white] 📦 [bold cyan]Full Complete Package[/bold cyan] — [white]{len(links)} parts[/white] (All main parts + all languages + soundtracks + bonus media)",
        f"[bold white][3][/bold white] 🎯 [bold cyan]Custom Language & Bonus Picker[/bold cyan] (Core game + choose specific voiceovers or OST by number)",
        f"[bold white][4][/bold white] 📋 [bold cyan]Manual Part Range Picker[/bold cyan] (Select specific part numbers or ranges, e.g. 1-10 or 42)",
    ])

    console.print(Panel("\n".join(menu_lines), title="[bold yellow]CHOOSE DOWNLOAD PACKAGE[/bold yellow]", box=box.ROUNDED))

    valid_choices = ["1", "2", "3", "4"]
    if has_english:
        valid_choices.append("e")

    mode = Prompt.ask("[bold yellow]Choose an option[/bold yellow]", choices=valid_choices, default="1").lower()

    if mode == "1":
        console.print(f"[bold green]✔ Selected {len(main_links)} main game parts.[/bold green]")
        return main_links
    elif mode == "e":
        eng_urls = [item["url"] for item in optional_items if item["type"] == "english_vo" or "english" in item.get("filename", "").lower()]
        chosen = main_links + eng_urls
        console.print(f"[bold green]✔ Selected {len(main_links)} main parts + English VO ({len(chosen)} parts total).[/bold green]")
        return chosen
    elif mode == "2":
        console.print(f"[bold green]✔ Selected all {len(links)} parts.[/bold green]")
        return main_links + [item["url"] for item in optional_items]
    elif mode == "3":
        raw_selection = Prompt.ask(
            "[bold yellow]Enter optional numbers to include (e.g. 1, 3 or 'all' or 'none')[/bold yellow]",
            default="none"
        ).strip()
        if raw_selection.lower() in ("none", "0", ""):
            return main_links
        if raw_selection.lower() == "all":
            return main_links + [item["url"] for item in optional_items]

        chosen_opt_urls = []
        tokens = re.split(r"[, ]+", raw_selection)
        for t in tokens:
            if t.isdigit():
                num = int(t)
                if 1 <= num <= len(optional_items):
                    chosen_opt_urls.append(optional_items[num - 1]["url"])

        console.print(f"[bold green]✔ Selected {len(main_links)} main parts + {len(chosen_opt_urls)} optional addons ({len(main_links) + len(chosen_opt_urls)} total).[/bold green]")
        return main_links + chosen_opt_urls
    elif mode == "4":
        from natsort import natsorted
        sorted_main = natsorted(main_links, key=lambda u: get_filename_from_url(u))
        sorted_opt = natsorted(optional_items, key=lambda x: x["filename"])
        all_ordered_files = [(u, get_filename_from_url(u)) for u in sorted_main] + [(item["url"], item["filename"]) for item in sorted_opt]
        part_table = Table(title="ALL AVAILABLE PARTS", box=box.ROUNDED)
        part_table.add_column("#", style="bold cyan", width=4)
        part_table.add_column("Filename", style="bold white")
        for pidx, (u, fn) in enumerate(all_ordered_files, 1):
            part_table.add_row(str(pidx), fn)
        console.print(part_table)
        range_input = Prompt.ask(
            f"[bold yellow]Enter part numbers/ranges (e.g. 1-{len(main_links)}, '1-9, 12, 13', or 'all')[/bold yellow]",
            default=f"1-{len(main_links)}"
        ).strip()

        selected_indices = parse_range_selection(range_input, len(all_ordered_files))
        if not selected_indices:
            console.print("[yellow]No valid parts parsed, defaulting to main parts.[/yellow]")
            return sorted_main

        final_urls = [all_ordered_files[i - 1][0] for i in selected_indices]
        console.print(f"[bold green]✔ Selected {len(final_urls)} custom parts.[/bold green]")
        return final_urls

    return links


def parse_range_selection(raw_input: str, max_count: int) -> List[int]:
    """
    Parses complex user range and list selections into sorted unique 1-indexed integers.
    Supports:
      - 'all' -> all 1 to max_count
      - '1-9' or '1 - 9'
      - '1,2,2,3,4'
      - '1-9, 12, 13' or '1-9 and 12, 13' or '1-9, 12-14'
      - separates on commas, spaces, tabs, and handles 'and', '+', '&'
    """
    import re

    clean = raw_input.strip().lower()
    if clean == "all":
        return list(range(1, max_count + 1))

    # Replace words and symbols like 'and', '&', '+', ';' with commas
    clean = re.sub(r"\b(and|to|through)\b", ",", clean)
    clean = re.sub(r"[;&+]+", ",", clean)

    # Normalize spaces around hyphens: '1 - 9' -> '1-9'
    clean = re.sub(r"(\d+)\s*-\s*(\d+)", r"\1-\2", clean)

    # Tokens can be separated by comma or whitespace
    tokens = [t.strip() for t in re.split(r"[, \t]+", clean) if t.strip()]

    selected: set[int] = set()
    for tok in tokens:
        if "-" in tok:
            sub = tok.split("-")
            if len(sub) == 2 and sub[0].isdigit() and sub[1].isdigit():
                start, end = int(sub[0]), int(sub[1])
                if start > end:
                    start, end = end, start
                for i in range(start, end + 1):
                    if 1 <= i <= max_count:
                        selected.add(i)
        elif tok.isdigit():
            val = int(tok)
            if 1 <= val <= max_count:
                selected.add(val)

    return sorted(selected)


def interactive_choose_mirror(
    mirrors: Dict[str, Any],
    main_only: bool = False,
    all_parts: bool = False,
    select_optionals: Optional[str] = None,
    preferred_hoster: Optional[str] = None,
) -> List[str]:
    """Present interactive mirror choice to user based on FitGirl parsed options."""
    title = mirrors.get("title", "FitGirl Repack")
    console.print(f"\n[bold green]🎮 Found Repack:[/bold green] [bold white]{title}[/bold white]\n")

    table = Table(title="AVAILABLE DOWNLOAD MIRRORS", box=box.ROUNDED)
    table.add_column("Option", style="bold cyan", width=8)
    table.add_column("Mirror Hoster", style="bold yellow")
    table.add_column("Parts Count", justify="center", style="white")

    options = []
    opt_num = 1

    releases = mirrors.get("releases", [])
    if len(releases) > 1:
        for rel in releases:
            rname = rel.get("name", "Release")
            tag = " [bold green](Primary)[/bold green]" if rel.get("is_primary") else ""
            if rel.get("fuckingfast"):
                table.add_row(str(opt_num), f"Filehoster: FuckingFast [{rname}]{tag}", f"{len(rel['fuckingfast'])} parts")
                options.append((f"fuckingfast_{rname}", rel["fuckingfast"]))
                opt_num += 1
            if rel.get("datanodes"):
                table.add_row(str(opt_num), f"Filehoster: DataNodes [{rname}]{tag}", f"{len(rel['datanodes'])} parts")
                options.append((f"datanodes_{rname}", rel["datanodes"]))
                opt_num += 1
            if rel.get("filekeeper"):
                table.add_row(str(opt_num), f"Filehoster: FileKeeper [{rname}]{tag}", f"{len(rel['filekeeper'])} parts")
                options.append((f"filekeeper_{rname}", rel["filekeeper"]))
                opt_num += 1
    else:
        if mirrors.get("fuckingfast"):
            table.add_row(str(opt_num), "Filehoster: FuckingFast (HTMX Fast-Path + Turnstile)", f"{len(mirrors['fuckingfast'])} parts")
            options.append(("fuckingfast", mirrors["fuckingfast"]))
            opt_num += 1

        if mirrors.get("datanodes"):
            table.add_row(str(opt_num), "Filehoster: DataNodes (Direct / IDM Compatible)", f"{len(mirrors['datanodes'])} parts")
            options.append(("datanodes", mirrors["datanodes"]))
            opt_num += 1

        if mirrors.get("filekeeper"):
            table.add_row(str(opt_num), "Filehoster: FileKeeper", f"{len(mirrors['filekeeper'])} parts")
            options.append(("filekeeper", mirrors["filekeeper"]))
            opt_num += 1

    if mirrors.get("magnets"):
        table.add_row(str(opt_num), "Torrent Mirror (Magnet URIs)", f"{len(mirrors['magnets'])} magnet(s)")
        options.append(("magnets", mirrors["magnets"]))
        opt_num += 1

    if not options:
        console.print("[bold red]❌ No supported direct download mirrors or magnets found on this page.[/bold red]")
        return []

    # Auto-select if a preferred hoster was passed via CLI or extension deep-link
    if preferred_hoster:
        pref = preferred_hoster.lower()
        matched_idx = None
        for idx, (opt_type, opt_links) in enumerate(options, 1):
            if pref in opt_type.lower():
                matched_idx = idx
                break
        if matched_idx:
            choice = matched_idx
            console.print(f"[bold cyan]🎯 Auto-selected mirror: {options[choice - 1][0]}[/bold cyan]")
            chosen_type, chosen_links = options[choice - 1]
            if chosen_type == "magnets":
                return chosen_links
            return select_repack_components(
                chosen_links,
                title=title,
                main_only=main_only,
                all_parts=all_parts,
                select_optionals=select_optionals,
            )

    # If all_parts or main_only is requested, auto-select Option 1 without prompting
    if all_parts or main_only:
        choice = 1
        console.print(f"[bold cyan]🎯 Auto-selected primary mirror: {options[0][0]}[/bold cyan]")
        chosen_type, chosen_links = options[0]
        if chosen_type == "magnets":
            return chosen_links
        return select_repack_components(
            chosen_links,
            title=title,
            main_only=main_only,
            all_parts=all_parts,
            select_optionals=select_optionals,
        )

    console.print(table)
    choice = 1
    try:
        choice = IntPrompt.ask(
            "\n[bold yellow]Select a mirror to download[/bold yellow]",
            choices=[str(i) for i in range(1, len(options) + 1)],
            default=1,
        )
    except Exception:
        choice = 1

    chosen_type, chosen_links = options[choice - 1]
    if chosen_type == "magnets":
        return chosen_links

    return select_repack_components(
        chosen_links,
        title=title,
        main_only=main_only,
        all_parts=all_parts,
        select_optionals=select_optionals,
    )


def choose_downloader_engine(
    preferred: Optional[str] = None,
    interactive_prompt: bool = True,
) -> str:
    """
    Scans the system for installed downloaders (IDM, FDM, Aria2, JDownloader, FFDL)
    and prompts the user to select their desired download engine.
    """
    from ffdl.downloaders.detector import DownloaderDetector

    available = DownloaderDetector.get_available()

    if preferred:
        pref_clean = preferred.lower().strip()
        if pref_clean in available:
            return pref_clean
        all_detected = DownloaderDetector.detect_all()
        if pref_clean in all_detected and not all_detected[pref_clean].is_available:
            console.print(f"[yellow]⚠️ Preferred downloader '{preferred}' was not found on your system. Falling back to FFDL.[/yellow]")
            return "ffdl"

    # If only 1 engine is available (FFDL), return it directly
    if len(available) <= 1 or not interactive_prompt:
        return "ffdl"

    # Multiple engines detected! Render visual choice table
    table = Table(title="🚀 DETECTED DOWNLOAD ENGINES ON YOUR SYSTEM", box=box.ROUNDED)
    table.add_column("Option", style="bold cyan", width=8)
    table.add_column("Engine", style="bold white", width=36)
    table.add_column("Details / Executable Path", style="dim white")

    engine_keys = list(available.keys())
    for idx, key in enumerate(engine_keys, 1):
        info = available[key]
        tag = " [Default]" if key == "ffdl" else ""
        table.add_row(
            str(idx),
            f"{info.name}{tag}",
            info.executable_path or info.description,
        )

    console.print(table)
    choice = 1
    try:
        raw_choice = Prompt.ask(
            f"[bold yellow]Select download engine [1-{len(engine_keys)}][/bold yellow]",
            choices=[str(i) for i in range(1, len(engine_keys) + 1)],
            default="1",
        )
        choice = int(raw_choice)
    except Exception:
        choice = 1

    selected_key = engine_keys[choice - 1]
    console.print(f"[bold green]✔ Selected Engine: {available[selected_key].name}[/bold green]\n")
    return selected_key


def run_interactive_wizard(download_fn: Callable):
    """Main interactive menu loop with full feature set."""
    from ffdl.cli import resolve_output_directory

    display_banner()
    menu_text = (
        "[bold white][1][/bold white] 🎮 [bold cyan]Enter FitGirl Game Post URL[/bold cyan] (Auto-extracts all mirrors & parts)\n"
        "[bold white][2][/bold white] 🌐 [bold cyan]Enter Pastebin, Magnet, or Direct Download Links[/bold cyan]\n"
        "[bold white][3][/bold white] 📁 [bold cyan]Load Links from Local File (.txt, .html, .md)[/bold cyan]\n"
        "[bold white][4][/bold white] 🔥 [bold bright_red]Scrape Web Page with Firecrawl AI[/bold bright_red]\n"
        "[bold white][5][/bold white] ⚡ [bold bright_green]Run Internet Speed Test & Calibrate Concurrency[/bold bright_green]\n"
        "[bold white][6][/bold white] ⚙️  [bold yellow]Storage & Drive Manager[/bold yellow] (View disk space & set default folder)\n"
        "[bold white][0][/bold white] 🚪 [bold red]Exit[/bold red]"
    )
    console.print(Panel(menu_text, title="[bold green]MAIN MENU[/bold green]", box=box.ROUNDED))
    choice = Prompt.ask("[bold yellow]Choose an option[/bold yellow]", choices=["1", "2", "3", "4", "5", "6", "0"], default="1")

    if choice == "0":
        sys.exit(0)
    elif choice == "6":
        from ffdl.persistence.resumer import load_user_config, save_user_config
        import os, shutil
        cfg = load_user_config()
        current_out = cfg.get("output_dir", str(Path.home() / "Downloads" / "FFDL"))

        drive_table = Table(title="💻 DETECTED STORAGE DRIVES & SPACE", box=box.ROUNDED)
        drive_table.add_column("Drive", style="bold cyan", width=8)
        drive_table.add_column("Free Space", style="bold green", width=16)
        drive_table.add_column("Total Capacity", style="white", width=16)
        drive_table.add_column("Status / Recommendation", style="yellow")

        drives = os.listdrives() if hasattr(os, "listdrives") else ["C:\\"]
        for d in drives:
            try:
                u = shutil.disk_usage(d)
                free_gb = u.free / (1024**3)
                total_gb = u.total / (1024**3)
                rec = "Ready for games" if free_gb > 50 else ("Low Space" if free_gb < 15 else "Adequate")
                drive_table.add_row(d, f"{free_gb:.1f} GB Free", f"{total_gb:.1f} GB Total", rec)
            except Exception:
                pass

        console.print(drive_table)
        console.print(f"\n📂 [bold white]Current Base Download Path:[/bold white] [bold cyan]{current_out}[/bold cyan]")
        console.print("[dim]Every downloaded game automatically creates its own clean subfolder inside this path.[/dim]\n")

        new_path = Prompt.ask("[bold yellow]Enter new default base directory (or press Enter to keep)[/bold yellow]", default=current_out).strip()
        if new_path and new_path != current_out:
            p = Path(new_path).expanduser()
            p.mkdir(parents=True, exist_ok=True)
            cfg["output_dir"] = str(p)
            save_user_config(cfg)
            console.print(f"[bold green]✔ Saved new default download directory: {p}[/bold green]\n")
        Prompt.ask("Press Enter to return...")
        return
    elif choice == "5":
        asyncio.run(execute_speedtest())
        Prompt.ask("\nPress Enter to return...")
        return
    elif choice == "1":
        url = Prompt.ask("\n[bold cyan]Enter FitGirl Game Post URL[/bold cyan]").strip()
        if not url:
            return
        result = asyncio.run(URLDispatcher.resolve_target(url))
        if result.get("type") == "fitgirl_page":
            chosen_links = interactive_choose_mirror(result["data"])
            if not chosen_links:
                return
            g_title = result["data"].get("title", "")
            default_out = resolve_output_directory(game_title=g_title)
            user_dir = Prompt.ask("[bold cyan]Destination Directory[/bold cyan]", default=str(default_out))
            out_dir = Path(user_dir).expanduser()
            out_dir.mkdir(parents=True, exist_ok=True)
            for idx, link in enumerate(chosen_links, 1):
                download_fn(link, out_dir, idx, len(chosen_links))
    elif choice == "2":
        url = Prompt.ask("\n[bold cyan]Enter URL, Magnet, or Pastebin Link[/bold cyan]").strip()
        if not url:
            return
        default_out = resolve_output_directory()
        user_dir = Prompt.ask("[bold cyan]Destination Directory[/bold cyan]", default=str(default_out))
        out_dir = Path(user_dir).expanduser()
        out_dir.mkdir(parents=True, exist_ok=True)
        download_fn(url, out_dir, 1, 1)
    elif choice == "3":
        file_p = Prompt.ask("\n[bold cyan]Enter Path to Links File (.txt, .html, .md)[/bold cyan]").strip()
        from ffdl.batch import parse_urls_from_file
        path_obj = Path(file_p)
        if not path_obj.exists():
            console.print(f"[bold red]❌ File not found: {file_p}[/bold red]")
            return
        urls = parse_urls_from_file(path_obj)
        if not urls:
            console.print("[bold red]❌ No valid URLs extracted from file.[/bold red]")
            return
        default_out = resolve_output_directory()
        user_dir = Prompt.ask("[bold cyan]Destination Directory[/bold cyan]", default=str(default_out))
        out_dir = Path(user_dir).expanduser()
        out_dir.mkdir(parents=True, exist_ok=True)
        for idx, u in enumerate(urls, 1):
            download_fn(u, out_dir, idx, len(urls))
    elif choice == "4":
        scrape_url = Prompt.ask("\n[bold cyan]Enter Web Page URL to Scrape via Firecrawl[/bold cyan]").strip()
        if not scrape_url:
            return
        from ffdl.resolvers.cloud_fallback import FirecrawlClient
        from ffdl.batch import extract_urls_from_text
        console.print("[dim cyan]Scraping page via Firecrawl Cloud API...[/dim cyan]")
        fc_data = asyncio.run(FirecrawlClient.scrape_page(scrape_url))
        scraped_urls = []
        for link in fc_data.get("links", []):
            scraped_urls.extend(extract_urls_from_text(link))
        if not scraped_urls and fc_data.get("markdown"):
            scraped_urls.extend(extract_urls_from_text(fc_data["markdown"]))
        if not scraped_urls:
            console.print("[bold red]❌ No direct download mirrors found on this page.[/bold red]")
            return
        console.print(f"[bold green]✔ Discovered {len(scraped_urls)} link(s)![/bold green]")
        default_out = resolve_output_directory()
        user_dir = Prompt.ask("[bold cyan]Destination Directory[/bold cyan]", default=str(default_out))
        out_dir = Path(user_dir).expanduser()
        out_dir.mkdir(parents=True, exist_ok=True)
        for idx, u in enumerate(scraped_urls, 1):
            download_fn(u, out_dir, idx, len(scraped_urls))
