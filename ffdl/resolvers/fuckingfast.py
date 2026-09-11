"""
ffdl.resolvers.fuckingfast - Multi-Tier FuckingFast Bypass & CDN Resolver
========================================================================
Implements the 4-Tier Hybrid Resolver Hierarchy:
Tier 0: Fast Path (<200ms) - Direct HTMX POST /f/{id}/go extracting HX-Redirect
Tier 1: Local Stealth CDP - Patchright / Chromium Turnstile checkbox auto-solver
Tier 2: Local Proxy - FlareSolverr localhost bridge
Tier 3: Cloud Fallback - Firecrawl Scraper API
"""

from __future__ import annotations

import asyncio
import re
import urllib.parse
from typing import Optional
import httpx

from ffdl.resolvers.cloud_fallback import FirecrawlClient


class FuckingFastResolver:
    """Multi-tier Cloudflare Turnstile bypass for FuckingFast."""

    @staticmethod
    def extract_file_id(url: str) -> Optional[str]:
        """Extract file ID from FuckingFast URL (e.g. /dcnsbbuenlbx#part01.rar -> dcnsbbuenlbx)."""
        parsed = urllib.parse.urlparse(url)
        path = parsed.path.strip("/").split("/")[0]
        if path and path not in ("dl", "f"):
            return path
        return None

    @classmethod
    async def try_tier0_htmx_fast_path(cls, url: str, timeout: float = 3.0) -> Optional[str]:
        """
        Tier 0: Fast Path (<200ms)
        Sends HTMX POST request to /f/{id}/go.
        Returns the direct CDN URL from HX-Redirect or Location header without browser automation.
        """
        file_id = cls.extract_file_id(url)
        if not file_id:
            return None

        post_url = f"https://fuckingfast.co/f/{file_id}/go"
        headers = {
            "Host": "fuckingfast.co",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "HX-Request": "true",
            "HX-Current-URL": url,
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://fuckingfast.co",
            "Referer": url,
        }

        try:
            async with httpx.AsyncClient(follow_redirects=False, timeout=timeout, verify=False) as client:
                resp = await client.post(post_url, headers=headers, content=b"")
                # Look for HX-Redirect or location header
                redirect_url = (
                    resp.headers.get("hx-redirect")
                    or resp.headers.get("HX-Redirect")
                    or resp.headers.get("location")
                    or resp.headers.get("Location")
                )
                if redirect_url and "dl.fuckingfast.co/dl/" in redirect_url:
                    return redirect_url

                # Check if body contains direct link
                match = re.search(r'https?://[^\s"\'<>]*dl\.fuckingfast\.co/dl/[^\s"\'<>]+', resp.text)
                if match:
                    return match.group(0)
        except Exception:
            pass

        return None

    @classmethod
    def try_tier1_stealth_browser(cls, url: str, timeout: float = 25.0) -> Optional[str]:
        """
        Tier 1: Local Stealth Browser
        Launches Playwright with anti-detection flags, offscreen positioning (-2400,-2400),
        monitors network traffic, waits for Turnstile verification, closes ad popups,
        and extracts the direct CDN streaming URL.
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
                        "--window-size=600,500",
                        "--mute-audio",
                        "--no-sandbox",
                    ],
                }
                try:
                    browser = p.chromium.launch(channel="chrome", **launch_kwargs)
                except Exception:
                    browser = p.chromium.launch(**launch_kwargs)

                context = browser.new_context(
                    viewport={"width": 600, "height": 500},
                    accept_downloads=True,
                )
                page = context.new_page()
                captured_url: Optional[str] = None

                def on_download(download):
                    nonlocal captured_url
                    if "dl.fuckingfast.co/dl/" in download.url:
                        captured_url = download.url
                    try:
                        download.cancel()
                    except Exception:
                        pass

                def on_response(response):
                    nonlocal captured_url
                    u = response.url
                    if "dl.fuckingfast.co/dl/" in u:
                        captured_url = u
                    for h, v in response.headers.items():
                        if ("hx-redirect" in h.lower() or "location" in h.lower()) and "dl.fuckingfast.co/dl/" in v:
                            captured_url = v

                page.on("download", on_download)
                page.on("response", on_response)

                page.goto(url, wait_until="domcontentloaded", timeout=int(timeout * 1000))

                for _ in range(int(timeout)):
                    time.sleep(1)
                    if captured_url:
                        break

                    token = page.evaluate("() => window.turnstileToken || ''")
                    style = page.evaluate(
                        "() => { const b = document.querySelector('a.link-button'); return b ? b.getAttribute('style') : 'none'; }"
                    )

                    # When Turnstile token is generated or button cursor is no longer not-allowed
                    if token or ("cursor:not-allowed" not in (style or "")):
                        btn = page.query_selector("a.link-button")
                        if btn:
                            try:
                                btn.click(force=True)
                            except Exception:
                                pass
                            time.sleep(1)
                            for p_extra in context.pages:
                                if p_extra != page:
                                    try:
                                        p_extra.close()
                                    except Exception:
                                        pass
                            try:
                                btn.click(force=True)
                            except Exception:
                                pass
                            time.sleep(2)
                            break

                try:
                    browser.close()
                except Exception:
                    pass

                return captured_url

        except Exception:
            return None

    @classmethod
    async def resolve(cls, url: str) -> Optional[str]:
        """Execute the 4-tier cascade to resolve FuckingFast CDN streaming link."""
        if "/dl/" in url and "dl.fuckingfast.co" in url:
            return url

        # Tier 0: Fast Path (<200ms)
        fast_link = await cls.try_tier0_htmx_fast_path(url)
        if fast_link:
            return fast_link

        # Tier 1: Local Stealth Browser
        stealth_link = await asyncio.to_thread(cls.try_tier1_stealth_browser, url)
        if stealth_link:
            return stealth_link

        # Tier 3: Cloud Fallback via Firecrawl API
        try:
            fc_data = await FirecrawlClient.scrape_page(url)
            for link in fc_data.get("links", []):
                if "dl.fuckingfast.co/dl/" in link:
                    return link
        except Exception:
            pass

        return None
