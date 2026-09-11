"""
ffdl.resolvers.cloud_fallback - Firecrawl Cloud Scraper Client
==============================================================
Uses Firecrawl v2 API (/v2/scrape and /v2/interact) to remotely scrape
complex, protected, or JS-heavy download pages.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, List, Optional
import httpx


def get_env_var(key_name: str, default: str = "") -> str:
    """Retrieve an API key from environment variables or .env files."""
    val = os.environ.get(key_name)
    if val and len(val.strip()) > 3:
        return val.strip()

    env_paths = [
        Path.cwd() / ".env",
        Path.home() / ".ffdl" / ".env",
    ]
    for ep in env_paths:
        if ep.exists():
            try:
                with open(ep, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith(f"{key_name}="):
                            parsed = line.strip().split("=", 1)[1].strip()
                            if parsed:
                                return parsed
            except Exception:
                pass
    return default


def get_firecrawl_api_key() -> str:
    """Retrieve Firecrawl API key from environment, .env file, or user config."""
    return get_env_var("FIRECRAWL_API_KEY", "")


class FirecrawlClient:
    """Async client for Firecrawl v2 API with multi-provider cloud scraper failover."""

    @classmethod
    async def scrape_page(cls, page_url: str, timeout: float = 30.0) -> Dict[str, Any]:
        """Scrape webpage and extract clean markdown and links using Firecrawl v2 or cloud fallback."""
        # 1. Primary: Firecrawl v2
        api_key = get_firecrawl_api_key()
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "url": page_url,
            "formats": ["markdown", "links", "html"],
            "waitFor": 3000,
        }
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post("https://api.firecrawl.dev/v2/scrape", json=payload, headers=headers)
                if resp.status_code == 200:
                    return resp.json().get("data", {})
                resp_v1 = await client.post("https://api.firecrawl.dev/v1/scrape", json=payload, headers=headers)
                if resp_v1.status_code == 200:
                    return resp_v1.json().get("data", {})
        except Exception:
            pass

        # 2. Secondary: Scrapfly if configured
        scrapfly_key = get_env_var("SCRAPFLY_API_KEY")
        if scrapfly_key:
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    sf_url = f"https://api.scrapfly.io/scrape?key={scrapfly_key}&url={page_url}&render_js=true"
                    resp = await client.get(sf_url)
                    if resp.status_code == 200:
                        content = resp.json().get("result", {}).get("content", "")
                        return {"html": content}
            except Exception:
                pass

        # 3. Tertiary: ZenRows if configured
        zenrows_key = get_env_var("ZENROWS_API_KEY")
        if zenrows_key:
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    zr_url = f"https://api.zenrows.com/v1/?apikey={zenrows_key}&url={page_url}&js_render=true"
                    resp = await client.get(zr_url)
                    if resp.status_code == 200:
                        return {"html": resp.text}
            except Exception:
                pass

        return {}
