"""
FF-Downloader Batch Download & Queue Coordinator (Peak Edition)
Handles batch URL parsing from text files, raw HTML snippets, BBCode, Markdown, and stdin.
"""

import re
import sys
import urllib.parse
from pathlib import Path
from typing import List

IGNORED_DOMAINS = [
    "mozilla.org", "opera.com", "google.com", "github.com",
    "bit.ly", "privatebin.info", "w3.org", "cloudflare.com",
    "microsoft.com", "apple.com"
]


def extract_urls_from_text(text: str) -> List[str]:
    """
    Extracts all fuckingfast.co and direct download URLs from any mixed text,
    raw HTML snippet (e.g. <ul><li><a href="...">), BBCode [url=...], Markdown, or plain list.
    Supports case-insensitive domain matching and unquoted attributes.
    """
    if not text or not text.strip():
        return []

    extracted: List[str] = []

    # 1. HTML href attributes (quoted and unquoted, e.g. href="https://..." or href="magnet:?...")
    html_matches = re.findall(r'href=["\']?((?:https?://|magnet:\?)[^\s"\'<>]+)', text, re.IGNORECASE)
    extracted.extend(html_matches)

    # 2. Magnet links
    magnet_matches = re.findall(r'magnet:\?[^\s"\'<>\[\]]+', text, re.IGNORECASE)
    extracted.extend(magnet_matches)

    # 3. BBCode links (e.g. [url=https://...] or [url]https://...[/url])
    bbcode_matches = re.findall(r'\[url=["\']?((?:https?://|magnet:\?)[^\s"\'\]]+)', text, re.IGNORECASE)
    extracted.extend(bbcode_matches)
    bbcode_plain = re.findall(r'\[url\]((?:https?://|magnet:\?)[^\s"\'\[]+)\[/url\]', text, re.IGNORECASE)
    extracted.extend(bbcode_plain)

    # 4. Markdown links (e.g. [text](https://...))
    md_matches = re.findall(r'\[.*?\]\(((?:https?://|magnet:\?)[^\s\)]+)\)', text)
    extracted.extend(md_matches)

    # 5. Plain download host URLs (fuckingfast.co, datanodes.to, filekeeper.net, fitgirl-repacks.site)
    direct_hosts_pattern = r'https?://[^\s"\'<>\[\]]*(?:fuckingfast\.co|datanodes\.to|filekeeper\.net|fitgirl-repacks\.site)[^\s"\'<>\[\]]*'
    direct_matches = re.findall(direct_hosts_pattern, text, re.IGNORECASE)
    extracted.extend(direct_matches)

    # 6. General URLs if no matches yet
    if not extracted:
        general_matches = re.findall(r'https?://[^\s"\'<>\[\]]+', text, re.IGNORECASE)
        extracted.extend(general_matches)

    # Filter out known browser / help / software domains
    extracted = [
        u for u in extracted
        if not any(d in u.lower() for d in IGNORED_DOMAINS)
    ]

    # Clean and deduplicate while strictly preserving order
    seen = set()
    cleaned: List[str] = []
    for u in extracted:
        u_clean = u.rstrip(".,;)]}>\"'\\/[")
        u_lower = u_clean.lower()
        if u_lower not in seen and len(u_clean) > 8:
            seen.add(u_lower)
            cleaned.append(u_clean)

    return cleaned


def parse_urls_from_file(file_path: Path) -> List[str]:
    """Extract valid URLs from a text/HTML/BBCode file."""
    if not file_path.exists():
        return []
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return extract_urls_from_text(content)
    except Exception:
        return []


def parse_urls_from_stdin() -> List[str]:
    """Extract valid URLs from standard input if piped."""
    try:
        if not sys.stdin.isatty():
            content = sys.stdin.read()
            return extract_urls_from_text(content)
    except Exception:
        pass
    return []
