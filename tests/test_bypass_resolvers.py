"""
Test Suite for Phase 5: Multi-Tier Stealth Cloudflare Bypass & FitGirl Scraper
Tests URLDispatcher classification, FuckingFast file ID extraction, and FitGirl HTML mirror grouping.
"""

import pytest
from ffdl.resolvers.dispatcher import URLDispatcher
from ffdl.resolvers.fuckingfast import FuckingFastResolver
from ffdl.resolvers.fitgirl_scraper import FitGirlPageScraper


def test_url_classification():
    assert URLDispatcher.classify_url("magnet:?xt=urn:btih:12345") == "magnet"
    assert URLDispatcher.classify_url("https://fitgirl-repacks.site/code-vein-ii/") == "fitgirl_page"
    assert URLDispatcher.classify_url("https://paste.fitgirl-repacks.site/?abcdef#12345") == "privatebin"
    assert URLDispatcher.classify_url("https://fuckingfast.co/dcnsbbuenlbx#part01.rar") == "fuckingfast"
    assert URLDispatcher.classify_url("https://datanodes.to/abc123/file.rar") == "datanodes"
    assert URLDispatcher.classify_url("https://filekeeper.net/xyz/file.rar") == "filekeeper"
    assert URLDispatcher.classify_url("https://example.com/archive.zip") == "generic_direct"


def test_fuckingfast_file_id_extraction():
    assert FuckingFastResolver.extract_file_id("https://fuckingfast.co/dcnsbbuenlbx#game.part01.rar") == "dcnsbbuenlbx"
    assert FuckingFastResolver.extract_file_id("https://fuckingfast.co/f/dcnsbbuenlbx/go") is None


def test_fitgirl_page_scraper_mirror_parsing():
    sample_html = """
    <html>
        <body>
            <h1 class="entry-title">CODE VEIN II [FitGirl Repack]</h1>
            <div class="su-spoiler-content">
                <h3>Filehoster: FuckingFast</h3>
                <a href="https://fuckingfast.co/part02#game.part02.rar">Part 2</a>
                <a href="https://fuckingfast.co/part01#game.part01.rar">Part 1</a>
                <h3>Filehoster: DataNodes</h3>
                <a href="https://datanodes.to/dn02#game.part02.rar">DN Part 2</a>
                <a href="https://datanodes.to/dn01#game.part01.rar">DN Part 1</a>
                <h3>Filehoster: FileKeeper</h3>
                <a href="https://filekeeper.net/fk01#game.part01.rar">FK Part 1</a>
                <h3>Torrent Mirrors</h3>
                <a href="magnet:?xt=urn:btih:fedcba9876543210&dn=Code+Vein+II">1337x Magnet</a>
                <a href="https://paste.fitgirl-repacks.site/?abcdef#key999">PrivateBin Backup</a>
            </div>
        </body>
    </html>
    """
    mirrors = FitGirlPageScraper.parse_mirrors(sample_html)
    assert mirrors["title"] == "CODE VEIN II [FitGirl Repack]"
    assert len(mirrors["fuckingfast"]) == 2
    # Check natural sort order
    assert "part01" in mirrors["fuckingfast"][0]
    assert "part02" in mirrors["fuckingfast"][1]

    assert len(mirrors["datanodes"]) == 2
    assert "dn01" in mirrors["datanodes"][0]

    assert len(mirrors["filekeeper"]) == 1
    assert len(mirrors["magnets"]) == 1
    assert len(mirrors["paste_links"]) == 1


def test_unbiased_batch_url_extraction():
    from ffdl.batch import extract_urls_from_text

    mixed_text = """
    Check out these download mirrors:
    1. FuckingFast: https://fuckingfast.co/part01#game.part01.rar
    2. DataNodes: [url=https://datanodes.to/dn01#game.part01.rar]DataNodes Mirror[/url]
    3. FileKeeper: <a href="https://filekeeper.net/fk01#game.part01.rar">FileKeeper Mirror</a>
    4. Magnet: magnet:?xt=urn:btih:1234567890abcdef&dn=Game+Repack
    """
    extracted = extract_urls_from_text(mixed_text)
    assert len(extracted) == 4
    assert any("fuckingfast.co" in u for u in extracted)
    assert any("datanodes.to" in u for u in extracted)
    assert any("filekeeper.net" in u for u in extracted)
    assert any("magnet:?" in u for u in extracted)


@pytest.mark.asyncio
async def test_fitgirl_resolve_page_mirrors_with_pastes(monkeypatch):
    from ffdl.resolvers.privatebin import PrivateBinDecryptor

    sample_html = """
    <html>
        <body>
            <h1 class="entry-title">TEST REPACK</h1>
            <a href="https://fuckingfast.co/part01#game.part01.rar">Part 1</a>
            <a href="https://paste.fitgirl-repacks.site/?abcdef#key123">PrivateBin</a>
        </body>
    </html>
    """

    async def mock_fetch_html(url, timeout=20.0):
        return sample_html

    async def mock_decrypt(url, timeout=15.0):
        return [
            "https://fuckingfast.co/part02#game.part02.rar",
            "https://datanodes.to/dn01#game.part01.rar",
        ]

    monkeypatch.setattr(FitGirlPageScraper, "fetch_html", mock_fetch_html)
    monkeypatch.setattr(PrivateBinDecryptor, "fetch_and_decrypt", mock_decrypt)

    mirrors = await FitGirlPageScraper.resolve_page_mirrors("https://fitgirl-repacks.site/test-repack/")
    assert len(mirrors["fuckingfast"]) == 2
    assert "part01" in mirrors["fuckingfast"][0]
    assert "part02" in mirrors["fuckingfast"][1]
    assert len(mirrors["datanodes"]) == 1
    assert "dn01" in mirrors["datanodes"][0]


@pytest.mark.asyncio
async def test_fitgirl_multi_release_isolation(monkeypatch):
    """
    Ensure primary cracked repack (14 parts) is isolated from secondary
    archived/hypervisor repack (39 parts) and not hallucinated into 53 parts.
    """
    from ffdl.resolvers.privatebin import PrivateBinDecryptor

    sample_html = """
    <html>
        <body>
            <h1 class="entry-title">Prince of Persia: The Lost Crown</h1>
            <!-- Primary Section -->
            <ul>
                <li><a href="https://paste.fitgirl-repacks.site/?cracked#key1">CRACKED Paste</a></li>
            </ul>
            <!-- Secondary Spoiler Section -->
            <div class="su-spoiler su-spoiler-closed">
                <div class="su-spoiler-title">Hypervisor Bypass version of the game</div>
                <div class="su-spoiler-content">
                    <a href="https://paste.fitgirl-repacks.site/?hyper#key2">Hypervisor Paste</a>
                </div>
            </div>
        </body>
    </html>
    """

    async def mock_fetch_html(url, timeout=20.0):
        return sample_html

    async def mock_decrypt(url, timeout=15.0):
        if "cracked" in url:
            # 14 parts
            links = [f"https://fuckingfast.co/crk{i}#Prince_of_Persia_The_Lost_Crown_CRACKED_--_fitgirl-repacks.site_--_.part{i:02d}.rar" for i in range(1, 10)]
            links += [f"https://fuckingfast.co/opt{i}#fg-optional-vo{i}.bin" for i in range(1, 6)]
            return links
        elif "hyper" in url:
            # 39 parts
            links = [f"https://fuckingfast.co/hyp{i}#Prince_of_Persia_The_Lost_Crown_--_fitgirl-repacks.site_--_.part{i:02d}.rar" for i in range(1, 35)]
            links += [f"https://fuckingfast.co/opt{i}#fg-optional-vo{i}.bin" for i in range(1, 6)]
            return links
        return []

    monkeypatch.setattr(FitGirlPageScraper, "fetch_html", mock_fetch_html)
    monkeypatch.setattr(PrivateBinDecryptor, "fetch_and_decrypt", mock_decrypt)

    mirrors = await FitGirlPageScraper.resolve_page_mirrors("https://fitgirl-repacks.site/prince-of-persia-the-lost-crown/")
    # Must NOT be 53 parts!
    assert len(mirrors["fuckingfast"]) == 14
    assert len(mirrors["releases"]) == 2
    # Verify releases breakdown
    rel_names = [r["name"] for r in mirrors["releases"]]
    assert "CRACKED Edition" in rel_names
    assert "Hypervisor Bypass version of the game" in rel_names
    hyper_rel = next(r for r in mirrors["releases"] if "Hypervisor" in r["name"])
    assert len(hyper_rel["fuckingfast"]) == 39

    # Verify main parts vs optional parts partitioning
    assert len(mirrors["main_parts"]["fuckingfast"]) == 9
    assert len(mirrors["optional_parts"]["fuckingfast"]) == 5


def test_fitgirl_optional_file_partitioning_and_selection():
    """Verify intelligent classification and selection of main vs optional/selective parts."""
    from ffdl.resolvers.fitgirl_scraper import classify_file_component, partition_links
    from ffdl.interactive import select_repack_components

    # 1. Classification
    c_main = classify_file_component("Cyberpunk_2077.part01.rar")
    assert not c_main["is_optional"]

    c_french = classify_file_component("fg-optional-french-vo.bin")
    assert c_french["is_optional"]
    assert c_french["type"] == "french_vo"
    assert "French" in c_french["label"]

    c_ost = classify_file_component("fg-optional-bonus-soundtracks.bin")
    assert c_ost["is_optional"]
    assert c_ost["type"] == "bonus_ost"

    # 2. Partitioning
    links = [
        "https://fuckingfast.co/1#game.part01.rar",
        "https://fuckingfast.co/2#game.part02.rar",
        "https://fuckingfast.co/3#game.part03.rar",
        "https://fuckingfast.co/4#fg-optional-french.bin",
        "https://fuckingfast.co/5#fg-optional-ost.bin",
    ]
    main_links, opt_items = partition_links(links)
    assert len(main_links) == 3
    assert len(opt_items) == 2

    # 3. Selection presets
    # main only
    res_main = select_repack_components(links, main_only=True)
    assert len(res_main) == 3
    assert all("part" in u for u in res_main)

    # all parts
    res_all = select_repack_components(links, all_parts=True)
    assert len(res_all) == 5

    # select by keyword
    res_french = select_repack_components(links, select_optionals="french")
    assert len(res_french) == 4
    assert any("french" in u for u in res_french)
    assert not any("ost" in u for u in res_french)

    # select by index
    res_idx = select_repack_components(links, select_optionals="2")
    assert len(res_idx) == 4


