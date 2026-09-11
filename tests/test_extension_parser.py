"""
Unit tests verifying browser extension compatibility, deep-link synthesis,
and FitGirl DOM classification logic.
"""

import re
from ffdl.protocol import build_protocol_url, parse_protocol_url
from ffdl.resolvers.fitgirl_scraper import classify_file_component


def test_extension_deep_link_roundtrip():
    post_url = "https://fitgirl-repacks.site/prince-of-persia-the-lost-crown/"
    deep_link = build_protocol_url(
        url=post_url,
        hoster="fuckingfast",
        main_only=True,
    )
    assert deep_link.startswith("ffdl://download?")
    assert "url=" in deep_link
    assert "hoster=fuckingfast" in deep_link
    assert "main_only=1" in deep_link

    parsed = parse_protocol_url(deep_link)
    assert parsed["url"] == post_url
    assert parsed["hoster"] == "fuckingfast"
    assert parsed["main_only"] is True


def test_extension_part_count_regex_simulation():
    sample_text_1 = "Download Mirrors (Direct Links) - 53 parts (500 MB each)"
    match = re.search(r"(\d+)\s*(?:parts|rar\s*parts|files)", sample_text_1, re.I)
    assert match is not None
    assert match.group(1) == "53"

    sample_text_2 = "Multi-Uploads: 14 parts"
    match2 = re.search(r"(\d+)\s*(?:parts|rar\s*parts|files)", sample_text_2, re.I)
    assert match2 is not None
    assert match2.group(1) == "14"


def test_component_classification_for_extension_options():
    c1 = classify_file_component("fg-01.bin")
    assert c1["type"] == "main"
    assert c1["is_optional"] is False

    c2 = classify_file_component("fg-selective-english.bin")
    assert c2["type"] == "english_vo"
    assert c2["is_optional"] is True

    c3 = classify_file_component("fg-optional-bonus.bin")
    assert c3["type"] == "bonus_content"
    assert c3["is_optional"] is True
