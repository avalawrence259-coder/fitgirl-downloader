"""
ffdl.resolvers.dispatcher - Master URL Router & Protocol Dispatcher
===================================================================
Automatically identifies URL type and delegates to the appropriate resolver.
Supports:
- FitGirl Game Pages (https://fitgirl-repacks.site/...)
- FuckingFast Links (https://fuckingfast.co/...)
- PrivateBin Encrypted Pastes (https://paste.fitgirl-repacks.site/...)
- DataNodes Links (https://datanodes.to/...)
- FileKeeper Links (https://filekeeper.net/...)
- Torrent Magnet URIs (magnet:?xt=...)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from ffdl.resolvers.datanodes import DirectHostResolver
from ffdl.resolvers.fitgirl_scraper import FitGirlPageScraper
from ffdl.resolvers.fuckingfast import FuckingFastResolver
from ffdl.resolvers.privatebin import PrivateBinDecryptor
from ffdl.resolvers.torrent import TorrentResolver


class URLDispatcher:
    """Master URL routing detector and execution dispatcher."""

    @staticmethod
    def classify_url(url: str) -> str:
        """Identify target URL classification using URL netloc/domain."""
        import urllib.parse
        u_raw = url.strip()
        if u_raw.lower().startswith("magnet:?"):
            return "magnet"
        parsed = urllib.parse.urlparse(u_raw)
        netloc = (parsed.netloc or "").lower()
        if "paste.fitgirl-repacks.site" in netloc or ("privatebin" in netloc and "#" in u_raw):
            return "privatebin"
        if "fitgirl-repacks.site" in netloc:
            return "fitgirl_page"
        if "fuckingfast.co" in netloc:
            return "fuckingfast"
        if "datanodes.to" in netloc:
            return "datanodes"
        if "filekeeper.net" in netloc:
            return "filekeeper"
        return "generic_direct"

    @classmethod
    async def resolve_target(cls, url: str, preferred_hoster: Optional[str] = None) -> Dict[str, Any]:
        """Dispatch URL to the correct resolver tier."""
        url_type = cls.classify_url(url)

        if url_type == "magnet":
            info = TorrentResolver.parse_magnet_info(url)
            return {"type": "magnet", "data": info}

        if url_type == "fitgirl_page":
            mirrors = await FitGirlPageScraper.resolve_page_mirrors(url, preferred_hoster=preferred_hoster)
            return {"type": "fitgirl_page", "data": mirrors}

        if url_type == "privatebin":
            links = await PrivateBinDecryptor.fetch_and_decrypt(url)
            return {"type": "privatebin", "links": links}

        if url_type == "fuckingfast":
            direct = await FuckingFastResolver.resolve(url)
            probe = {}
            if direct:
                probe = await DirectHostResolver.probe_direct_url(direct)
            return {"type": "fuckingfast", "direct_url": direct or url, "probe": probe}

        if url_type in ("datanodes", "filekeeper", "generic_direct"):
            probe = await DirectHostResolver.probe_direct_url(url)
            direct_url = url
            if url_type == "datanodes" and probe.get("size_bytes", 0) <= 0:
                import asyncio
                playwright_url = await asyncio.to_thread(DirectHostResolver.resolve_datanodes_playwright, url)
                if playwright_url:
                    direct_url = playwright_url
                    probe = await DirectHostResolver.probe_direct_url(playwright_url)
                    probe["direct_url"] = playwright_url
            elif url_type == "filekeeper" and probe.get("size_bytes", 0) <= 0:
                import asyncio
                playwright_url = await asyncio.to_thread(DirectHostResolver.resolve_filekeeper_playwright, url)
                if playwright_url:
                    direct_url = playwright_url
                    probe = await DirectHostResolver.probe_direct_url(playwright_url)
                    probe["direct_url"] = playwright_url

            if probe.get("direct_url"):
                direct_url = probe["direct_url"]

            return {"type": url_type, "direct_url": direct_url, "probe": probe}

        return {"type": "unknown", "url": url}
