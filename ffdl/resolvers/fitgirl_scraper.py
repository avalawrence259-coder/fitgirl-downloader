"""
ffdl.resolvers.fitgirl_scraper - FitGirl Repacks Multi-Mirror Aggregator & Scraper
=================================================================================
Automates parsing of FitGirl game post pages (e.g. https://fitgirl-repacks.site/game-title/).
Features:
- Expands and parses collapsible JavaScript accordions ("[+ Click to show direct links]").
- Categorizes mirrors into FuckingFast, DataNodes, FileKeeper, and Torrents.
- Extracts full part archives in natural order.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any, Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
import httpx
from natsort import natsorted

from ffdl.resolvers.cloud_fallback import FirecrawlClient
from ffdl.resolvers.privatebin import PrivateBinDecryptor
from ffdl.resolvers.torrent import TorrentResolver


from urllib.parse import urlparse, unquote

def get_filename_from_url(url: str) -> str:
    """Extract decoded filename from URL fragment or path."""
    parsed = urlparse(url)
    target = parsed.fragment or parsed.path.split("/")[-1]
    return unquote(target)

def extract_archive_prefix(filename: str) -> str:
    """Extract clean base archive prefix (e.g. Game_Name_CRACKED_)."""
    f_lower = filename.lower()
    if f_lower.startswith("fg-optional") or f_lower.startswith("fg-selective"):
        return "__optional__"
    m = re.match(r"^(.*?)(?:\.part\d+|\.rar|\.bin|\.zip|\.7z|$)", filename, re.IGNORECASE)
    if m:
        base = m.group(1).strip("._- ")
        if base:
            return base
    return "__main__"


def classify_file_component(filename: str) -> Dict[str, Any]:
    """Classifies repack file component into required main vs optional/selective addon."""
    f_clean = filename.lower()
    is_optional = False
    opt_type = "main"
    label = ""

    if (
        "fg-optional" in f_clean
        or "fg-selective" in f_clean
        or f_clean.startswith("optional-")
        or f_clean.startswith("selective-")
        or "-selective-" in f_clean
        or ("selective" in f_clean and "part" not in f_clean)
        or ("optional" in f_clean and "part" not in f_clean)
    ):
        is_optional = True
        if "english" in f_clean:
            opt_type = "english_vo"
            label = "English Voiceovers / Speech"
        elif "french" in f_clean or "francais" in f_clean:
            opt_type = "french_vo"
            label = "French Voiceovers (VO)"
        elif "german" in f_clean or "deutsch" in f_clean:
            opt_type = "german_vo"
            label = "German Voiceovers (VO)"
        elif "spanish" in f_clean or "espanol" in f_clean:
            opt_type = "spanish_vo"
            label = "Spanish Voiceovers (VO)"
        elif "japanese" in f_clean or "jap" in f_clean:
            opt_type = "japanese_vo"
            label = "Japanese Voiceovers (VO)"
        elif "russian" in f_clean:
            opt_type = "russian_vo"
            label = "Russian Voiceovers (VO)"
        elif "chinese" in f_clean:
            opt_type = "chinese_vo"
            label = "Chinese Voiceovers (VO)"
        elif "farsi" in f_clean or "persian" in f_clean:
            opt_type = "persian_vo"
            label = "Persian / Farsi Voiceovers (VO)"
        elif "brazilian" in f_clean or "portuguese" in f_clean:
            opt_type = "portuguese_vo"
            label = "Portuguese-Brazil Voiceovers (VO)"
        elif "italian" in f_clean:
            opt_type = "italian_vo"
            label = "Italian Voiceovers (VO)"
        elif "polish" in f_clean:
            opt_type = "polish_vo"
            label = "Polish Voiceovers (VO)"
        elif "soundtrack" in f_clean or "ost" in f_clean:
            opt_type = "bonus_ost"
            label = "Original Soundtracks (OST)"
        elif "bonus" in f_clean or "artbook" in f_clean or "wallpapers" in f_clean:
            opt_type = "bonus_content"
            label = "Bonus Content / Digital Goodies"
        elif "credits" in f_clean:
            opt_type = "bonus_credits"
            label = "End Credits Video"
        elif "4k" in f_clean or "videos" in f_clean:
            opt_type = "4k_videos"
            label = "Ultra-HD 4K Cutscenes & Videos"
        else:
            opt_type = "optional_addon"
            label = f"Optional Addon ({filename})"

    return {
        "filename": filename,
        "is_optional": is_optional,
        "type": opt_type,
        "label": label or filename,
    }


def partition_links(urls: List[str]) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Partitions URLs into required main archive parts and optional/selective files."""
    main_urls: List[str] = []
    opt_items: List[Dict[str, Any]] = []
    for u in dict.fromkeys(urls):
        fn = get_filename_from_url(u)
        info = classify_file_component(fn)
        if info["is_optional"]:
            opt_items.append({"url": u, "filename": fn, "label": info["label"], "type": info["type"]})
        else:
            main_urls.append(u)
    return natsorted(main_urls, key=lambda u: get_filename_from_url(u)), natsorted(opt_items, key=lambda x: x["filename"])


class FitGirlPageScraper:
    """Scrapes FitGirl repack game posts, expands accordions, and groups download mirrors."""

    @classmethod
    async def fetch_html(cls, page_url: str, timeout: float = 20.0) -> str:
        """Fetch game post HTML with desktop User-Agent, with Firecrawl & Playwright fallback."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        # 1. Direct fast HTTP fetch
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=timeout, verify=False) as client:
                resp = await client.get(page_url, headers=headers)
                if resp.status_code == 200 and len(resp.text) > 500:
                    low = resp.text.lower()
                    # Check for bot challenge pages
                    if "just a moment..." not in low and "cf-turnstile" not in low and "attention required" not in low:
                        return resp.text
        except Exception:
            pass

        # 2. Firecrawl Cloud Scraper (bypasses ISP blocks, Cloudflare, geoblocks)
        try:
            fc_data = await FirecrawlClient.scrape_page(page_url)
            html = fc_data.get("html", "")
            if html and len(html) > 500:
                return html
        except Exception:
            pass

        # 3. Local Stealth Playwright fallback
        try:
            import asyncio
            def _playwright_fetch(u: str) -> str:
                from playwright.sync_api import sync_playwright
                with sync_playwright() as p:
                    try:
                        browser = p.chromium.launch(
                            channel="chrome",
                            headless=False,
                            args=["--disable-blink-features=AutomationControlled", "--window-position=-2400,-2400", "--mute-audio"],
                        )
                    except Exception:
                        browser = p.chromium.launch(
                            headless=False,
                            args=["--disable-blink-features=AutomationControlled", "--window-position=-2400,-2400", "--mute-audio"],
                        )
                    page = browser.new_page()
                    page.goto(u, wait_until="domcontentloaded", timeout=25000)
                    content = page.content()
                    browser.close()
                    return content
            pw_html = await asyncio.to_thread(_playwright_fetch, page_url)
            if pw_html and len(pw_html) > 500:
                return pw_html
        except Exception:
            pass

        return ""

    @classmethod
    def parse_mirrors(cls, html: str) -> Dict[str, Any]:
        """
        Parses game title, magnets, and initial mirrors from FitGirl repack HTML.
        Detects collapsible secondary spoilers (e.g. Hypervisor, Old version) to isolate releases.
        """
        soup = BeautifulSoup(html, "html.parser")

        # 1. Game Title
        title = "FitGirl Repack"
        h1 = soup.find("h1", class_="entry-title")
        if h1:
            title = h1.get_text().strip()

        # 2. Torrents (1337x, RuTor, Tapochek, Magnets)
        magnets = TorrentResolver.extract_magnets_from_html(html)

        # 3. Direct Filehosters & Paste Links categorized by section
        fuckingfast_links: List[str] = []
        datanodes_links: List[str] = []
        filekeeper_links: List[str] = []
        paste_items: List[Dict[str, str]] = [] # list of {"url": ..., "spoiler_title": ...}

        # Check for secondary release spoilers
        sec_keywords = ["hypervisor", "previous", "older", "old", "archive", "archived", "v1.", "original"]

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            href_lower = href.lower()

            # Identify if anchor is enclosed in a secondary/archived release spoiler
            sp = a.find_parent("div", class_="su-spoiler")
            sp_title = ""
            if sp:
                t_div = sp.find("div", class_="su-spoiler-title")
                if t_div:
                    cand_title = t_div.get_text().strip()
                    if any(k in cand_title.lower() for k in sec_keywords):
                        sp_title = cand_title

            if "paste.fitgirl-repacks.site" in href_lower:
                li = a.find_parent("li")
                li_text = (li.get_text().strip() if li else "")
                anchor_text = a.get_text().strip()
                ctx = (anchor_text + " " + li_text).lower()
                hint = ""
                if "datanodes" in ctx:
                    hint = "datanodes"
                elif "fuckingfast" in ctx:
                    hint = "fuckingfast"
                elif "filekeeper" in ctx:
                    hint = "filekeeper"
                elif "torrent" in ctx:
                    hint = "torrent"
                paste_items.append({"url": href, "spoiler_title": sp_title, "hoster": hint, "text": anchor_text})
            elif not sp_title:
                # Direct links from primary section
                if "fuckingfast.co" in href_lower:
                    fuckingfast_links.append(href)
                elif "datanodes.to" in href_lower:
                    datanodes_links.append(href)
                elif "filekeeper.net" in href_lower:
                    filekeeper_links.append(href)

        # Deduplicate and sort naturally
        paste_urls = list(dict.fromkeys(p["url"] for p in paste_items))
        return {
            "title": title,
            "fuckingfast": natsorted(list(dict.fromkeys(fuckingfast_links))),
            "datanodes": natsorted(list(dict.fromkeys(datanodes_links))),
            "filekeeper": natsorted(list(dict.fromkeys(filekeeper_links))),
            "paste_links": paste_urls,
            "paste_items": paste_items,
            "magnets": magnets,
        }

    @classmethod
    async def resolve_page_mirrors(
        cls,
        page_url: str,
        preferred_hoster: Optional[str] = None,
        auto_decrypt_pastes: bool = True,
    ) -> Dict[str, Any]:
        """
        High-level resolver: fetches post HTML, parses mirrors, automatically decrypts
        embedded PrivateBin pastes, and accurately groups multi-part archives by release
        edition (e.g. CRACKED vs Hypervisor / Previous version) to prevent link cross-contamination.
        Decryption is executed in parallel with connection pooling for maximum speed.
        """
        html = await cls.fetch_html(page_url)
        mirrors = cls.parse_mirrors(html)

        if not auto_decrypt_pastes or not mirrors.get("paste_items"):
            return mirrors

        # Track release editions: release_name -> {"fuckingfast": [], "datanodes": [], "filekeeper": [], "optional": []}
        releases_map: Dict[str, Dict[str, Any]] = {}

        # Primary container
        primary_key = "Primary Release"
        releases_map[primary_key] = {
            "name": primary_key,
            "is_primary": True,
            "fuckingfast": list(mirrors.get("fuckingfast", [])),
            "datanodes": list(mirrors.get("datanodes", [])),
            "filekeeper": list(mirrors.get("filekeeper", [])),
            "optional": [],
        }

        items_to_process = mirrors["paste_items"]
        if preferred_hoster:
            pref_norm = preferred_hoster.lower().strip()
            matched = [item for item in mirrors["paste_items"] if item.get("hoster") == pref_norm]
            if matched:
                items_to_process = matched

        import inspect
        sig = inspect.signature(PrivateBinDecryptor.fetch_and_decrypt)
        accepts_client = "client" in sig.parameters or any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())

        async with httpx.AsyncClient(
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=30),
            timeout=15.0,
            verify=False,
        ) as client:
            tasks = [
                PrivateBinDecryptor.fetch_and_decrypt(item["url"], client=client)
                if accepts_client
                else PrivateBinDecryptor.fetch_and_decrypt(item["url"])
                for item in items_to_process
            ]
            decrypted_results = await asyncio.gather(*tasks, return_exceptions=True)

        for item, decrypted in zip(items_to_process, decrypted_results):
            if isinstance(decrypted, Exception) or not decrypted:
                continue
            paste_url = item["url"]
            sp_title = item.get("spoiler_title", "")
            try:
                # Determine release group: check spoiler title or archive prefix
                rel_name = sp_title
                if not rel_name:
                    # Check first non-optional archive prefix
                    for link in decrypted:
                        fn = get_filename_from_url(link)
                        prefix = extract_archive_prefix(fn)
                        if prefix != "__optional__" and prefix != "__main__":
                            if "cracked" in prefix.lower():
                                rel_name = "CRACKED Edition"
                            else:
                                rel_name = prefix
                            break
                if not rel_name:
                    rel_name = primary_key

                if rel_name not in releases_map:
                    releases_map[rel_name] = {
                        "name": rel_name,
                        "is_primary": (rel_name in (primary_key, "CRACKED Edition")),
                        "fuckingfast": [],
                        "datanodes": [],
                        "filekeeper": [],
                        "optional": [],
                    }

                for link in decrypted:
                    l_lower = link.lower()
                    fn = get_filename_from_url(link)
                    if extract_archive_prefix(fn) == "__optional__":
                        releases_map[rel_name]["optional"].append(link)

                    if "fuckingfast.co" in l_lower:
                        releases_map[rel_name]["fuckingfast"].append(link)
                    elif "datanodes.to" in l_lower:
                        releases_map[rel_name]["datanodes"].append(link)
                    elif "filekeeper.net" in l_lower:
                        releases_map[rel_name]["filekeeper"].append(link)
            except Exception:
                pass


        # Merge direct primary links into the matching primary release
        other_keys = [k for k in releases_map.keys() if k != primary_key]
        if primary_key in releases_map and other_keys:
            target_key = None
            if "CRACKED Edition" in releases_map:
                target_key = "CRACKED Edition"
            elif len(other_keys) == 1:
                target_key = other_keys[0]
            else:
                # Check archive prefix match with direct primary links
                prim_links = (
                    releases_map[primary_key]["fuckingfast"]
                    + releases_map[primary_key]["datanodes"]
                    + releases_map[primary_key]["filekeeper"]
                )
                prim_prefixes = {extract_archive_prefix(get_filename_from_url(l)) for l in prim_links}
                prim_prefixes.discard("__optional__")
                prim_prefixes.discard("__main__")
                for k in other_keys:
                    if k in prim_prefixes:
                        target_key = k
                        break
                if not target_key:
                    target_key = other_keys[0]

            if target_key:
                for k in ("fuckingfast", "datanodes", "filekeeper", "optional"):
                    releases_map[target_key][k].extend(releases_map[primary_key][k])
                del releases_map[primary_key]

        # Sort and deduplicate links inside each release with main parts first
        releases_list: List[Dict[str, Any]] = []
        for rname, rdata in releases_map.items():
            ff_main, ff_opt = partition_links(rdata["fuckingfast"])
            dn_main, dn_opt = partition_links(rdata["datanodes"])
            fk_main, fk_opt = partition_links(rdata["filekeeper"])

            rdata["main_parts"] = {"fuckingfast": ff_main, "datanodes": dn_main, "filekeeper": fk_main}
            rdata["optional_parts"] = {"fuckingfast": ff_opt, "datanodes": dn_opt, "filekeeper": fk_opt}

            rdata["fuckingfast"] = ff_main + [item["url"] for item in ff_opt]
            rdata["datanodes"] = dn_main + [item["url"] for item in dn_opt]
            rdata["filekeeper"] = fk_main + [item["url"] for item in fk_opt]

            if rdata["fuckingfast"] or rdata["datanodes"] or rdata["filekeeper"]:
                releases_list.append(rdata)

        # Determine primary release (CRACKED or first with links)
        primary_release = next((r for r in releases_list if "cracked" in r["name"].lower()), None)
        if not primary_release and releases_list:
            primary_release = releases_list[0]

        if primary_release:
            mirrors["fuckingfast"] = primary_release["fuckingfast"]
            mirrors["datanodes"] = primary_release["datanodes"]
            mirrors["filekeeper"] = primary_release["filekeeper"]
            mirrors["main_parts"] = primary_release.get("main_parts", {})
            mirrors["optional_parts"] = primary_release.get("optional_parts", {})
        else:
            mirrors["fuckingfast"] = []
            mirrors["datanodes"] = []
            mirrors["filekeeper"] = []
            mirrors["main_parts"] = {}
            mirrors["optional_parts"] = {}

        mirrors["releases"] = releases_list
        return mirrors

