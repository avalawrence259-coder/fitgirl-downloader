"""
ffdl.resolver - Backward Compatibility Facade
=============================================
Redirects legacy imports to the modular ffdl.resolvers package.
"""

from __future__ import annotations

import asyncio
import re
import warnings
from typing import Any, Dict, List, Optional
from natsort import natsorted, ns

warnings.warn(
    "ffdl.resolver is deprecated; use ffdl.resolvers instead.",
    DeprecationWarning,
    stacklevel=2,
)

from ffdl.resolvers.dispatcher import URLDispatcher
from ffdl.resolvers.datanodes import DirectHostResolver
from ffdl.resolvers.fitgirl_scraper import FitGirlPageScraper, classify_file_component, partition_links
from ffdl.resolvers.fuckingfast import FuckingFastResolver
from ffdl.resolvers.privatebin import PrivateBinDecryptor
from ffdl.resolvers.torrent import TorrentResolver
from ffdl.resolvers.cloud_fallback import FirecrawlClient, get_firecrawl_api_key

__all__ = [
    "URLDispatcher",
    "DirectHostResolver",
    "FitGirlPageScraper",
    "FuckingFastResolver",
    "PrivateBinDecryptor",
    "TorrentResolver",
    "FirecrawlClient",
    "get_firecrawl_api_key",
    "classify_file_component",
    "partition_links",
    "natural_sort_key",
    "sort_archive_parts",
    "is_paste_url",
    "resolve_url_metadata",
]


def natural_sort_key(url: str):
    """Sort URLs naturally by numeric part numbers."""
    name = url.split("#")[-1] if "#" in url else url.split("/")[-1]
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r"(\d+)", name)]


def sort_archive_parts(urls: List[str]) -> List[str]:
    """Sort a list of download URLs naturally by their part numbers."""
    return natsorted(urls, alg=ns.IGNORECASE)


def is_paste_url(url: str) -> bool:
    """Check if URL is a pastebin or aggregator link rather than a direct filehost link."""
    u = url.lower().strip()
    return any(p in u for p in [
        "paste.", "pastebin.com", "rentry.co", "rentry.org",
        "justpaste.it", "pastee.org", "controlc.com", "hastebin"
    ])


async def resolve_url_metadata(url: str, timeout: float = 15.0) -> Dict[str, Any]:
    """Legacy helper: resolves metadata via URLDispatcher."""
    resolved = await URLDispatcher.resolve_target(url)
    return resolved.get("probe", {})
