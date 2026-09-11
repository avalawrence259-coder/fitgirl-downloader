"""
ffdl.resolvers.datanodes - DataNodes & FileKeeper Direct Resolver
================================================================
Handles DataNodes.to and FileKeeper.net direct filehost links.
Probes direct download endpoints and bypasses interstitial redirects.
"""

from __future__ import annotations

import re
import urllib.parse
from typing import Dict, Optional
import httpx


class DirectHostResolver:
    """Direct probe and header extractor for DataNodes and FileKeeper."""

    @staticmethod
    def is_datanodes_url(url: str) -> bool:
        return "datanodes.to" in url.lower()

    @staticmethod
    def is_filekeeper_url(url: str) -> bool:
        return "filekeeper.net" in url.lower()

    @classmethod
    async def probe_direct_url(cls, url: str, timeout: float = 12.0) -> Dict[str, Any]:
        """Send Range probe to check if link directly serves binary content."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Range": "bytes=0-0",
        }
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=timeout, verify=False) as client:
                resp = await client.get(url, headers=headers)
                supports_ranges = resp.status_code == 206 or resp.headers.get("accept-ranges") == "bytes"
                size = 0
                cr = resp.headers.get("content-range")
                if cr and "/" in cr:
                    val = cr.split("/")[-1].strip()
                    if val.isdigit():
                        size = int(val)
                elif resp.headers.get("content-length"):
                    val = resp.headers.get("content-length", "").strip()
                    if val.isdigit():
                        size = int(val)

                # Extract filename from Content-Disposition or path
                filename = "download.bin"
                cd = resp.headers.get("content-disposition", "")
                if "filename=" in cd:
                    match = re.search(r'filename\*?=(?:UTF-8\'\')?["\']?([^"\';\r\n]+)["\']?', cd)
                    if match:
                        filename = match.group(1).strip()
                else:
                    path_name = urllib.parse.urlparse(str(resp.url)).path.split("/")[-1]
                    if path_name and len(path_name) > 3 and "." in path_name:
                        filename = path_name

                # If filename has no extension or is default, fallback to original url path
                if filename == "download.bin" or "." not in filename:
                    orig_cand = urllib.parse.urlparse(url).path.split("/")[-1]
                    if orig_cand and "." in orig_cand:
                        filename = orig_cand

                return {
                    "direct_url": str(resp.url),
                    "original_url": url,
                    "filename": re.sub(r'[\\/*?:"<>|]', "_", filename),
                    "size_bytes": size,
                    "supports_ranges": supports_ranges,
                    "status_code": resp.status_code,
                }
        except Exception as e:
            return {
                "direct_url": url,
                "original_url": url,
                "filename": "download.bin",
                "size_bytes": 0,
                "supports_ranges": False,
                "status_code": 500,
                "error": str(e),
            }

    @classmethod
    def resolve_datanodes_playwright(cls, url: str, timeout: float = 30.0) -> Optional[str]:
        """
        Uses Playwright with stealth offscreen automation to bypass DataNodes interstitial pages
        and resolve direct CDN streaming URL.
        """
        try:
            from playwright.sync_api import sync_playwright
            import time

            with sync_playwright() as p:
                launch_kwargs = {
                    "headless": False,
                    "args": [
                        "--disable-blink-features=AutomationControlled",
                        "--window-position=-2400,-2400",
                        "--window-size=1000,800",
                        "--mute-audio",
                        "--no-sandbox",
                    ],
                }
                try:
                    browser = p.chromium.launch(channel="chrome", **launch_kwargs)
                except Exception:
                    browser = p.chromium.launch(**launch_kwargs)

                context = browser.new_context(viewport={"width": 1000, "height": 800}, accept_downloads=True)
                page = context.new_page()
                captured_url: Optional[str] = None

                def on_download(download):
                    nonlocal captured_url
                    captured_url = download.url
                    try:
                        download.cancel()
                    except Exception:
                        pass

                page.on("download", on_download)
                page.on("popup", lambda p_tab: p_tab.close())

                page.goto(url, wait_until="domcontentloaded", timeout=int(timeout * 1000))

                for sec in range(int(timeout)):
                    time.sleep(1)
                    if captured_url:
                        break

                    dl_inputs = page.query_selector_all(
                        "input[value='Download'], button:has-text('Download'), button#download-button, input[type='submit']"
                    )
                    for btn in dl_inputs:
                        try:
                            if btn.is_visible():
                                btn.click()
                                time.sleep(1)
                                for extra in context.pages:
                                    if extra != page:
                                        try:
                                            extra.close()
                                        except Exception:
                                            pass
                                btn.click()
                                time.sleep(3)
                                break
                        except Exception:
                            pass

                try:
                    browser.close()
                except Exception:
                    pass
                return captured_url
        except Exception:
            return None

    @classmethod
    def resolve_filekeeper_playwright(cls, url: str, timeout: float = 30.0) -> Optional[str]:
        """
        Uses Playwright with stealth offscreen automation to navigate FileKeeper 5s countdown,
        close ad popups, and resolve direct CDN streaming URL.
        """
        try:
            from playwright.sync_api import sync_playwright
            import time

            with sync_playwright() as p:
                launch_kwargs = {
                    "headless": False,
                    "args": [
                        "--disable-blink-features=AutomationControlled",
                        "--window-position=-2400,-2400",
                        "--window-size=1000,800",
                        "--mute-audio",
                        "--no-sandbox",
                    ],
                }
                try:
                    browser = p.chromium.launch(channel="chrome", **launch_kwargs)
                except Exception:
                    browser = p.chromium.launch(**launch_kwargs)

                context = browser.new_context(viewport={"width": 1000, "height": 800}, accept_downloads=True)
                page = context.new_page()
                captured_url: Optional[str] = None

                def on_download(download):
                    nonlocal captured_url
                    captured_url = download.url
                    try:
                        download.cancel()
                    except Exception:
                        pass

                page.on("download", on_download)
                page.on("popup", lambda p_tab: p_tab.close())

                page.goto(url, wait_until="domcontentloaded", timeout=int(timeout * 1000))

                for sec in range(int(timeout)):
                    time.sleep(1)
                    if captured_url:
                        break

                    btn = page.query_selector("#download-button, a#download-link, button:has-text('Download')")
                    if btn and btn.is_visible():
                        try:
                            btn.click()
                            time.sleep(1)
                            for extra in context.pages:
                                if extra != page:
                                    try:
                                        extra.close()
                                    except Exception:
                                        pass
                            btn.click()
                            time.sleep(3)
                            break
                        except Exception:
                            pass

                try:
                    browser.close()
                except Exception:
                    pass
                return captured_url
        except Exception:
            return None

