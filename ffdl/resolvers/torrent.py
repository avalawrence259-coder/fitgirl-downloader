"""
ffdl.resolvers.torrent - Magnet URI & Torrent Mirror Resolver
=============================================================
Parses, cleans, and extracts magnet links from 1337x, RuTor, and FitGirl posts.
"""

from __future__ import annotations

import re
import urllib.parse
from typing import Dict, List, Optional
import httpx


class TorrentResolver:
    """Extracts real magnet URIs from tracker redirect pages or HTML."""

    @staticmethod
    def is_magnet_url(url: str) -> bool:
        """Check whether URL is a magnet link."""
        return url.strip().lower().startswith("magnet:?")

    @staticmethod
    def parse_magnet_info(magnet_url: str) -> Dict[str, str]:
        """Extract display name, hash (xt), and trackers from magnet URI."""
        parsed = urllib.parse.urlparse(magnet_url)
        params = urllib.parse.parse_qs(parsed.query)

        name = params.get("dn", ["Unknown Torrent"])[0]
        xt = params.get("xt", [""])[0]
        trackers = params.get("tr", [])

        return {
            "name": name,
            "hash": xt,
            "trackers": trackers,
            "raw_magnet": magnet_url,
        }

    @classmethod
    def extract_magnets_from_html(cls, html: str) -> List[str]:
        """Extract all magnet:? links embedded in an HTML document."""
        matches = re.findall(r'href=["\']?(magnet:\?[^"\'<>\s]+)', html, re.IGNORECASE)
        # Deduplicate preserving order
        seen = set()
        clean = []
        for m in matches:
            if m not in seen:
                seen.add(m)
                clean.append(m)
        return clean
