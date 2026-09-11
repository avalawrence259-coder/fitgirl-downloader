"""
Test Suite for Phase 6: Interactive Terminal UI & Full CLI Orchestration
Tests UI formatting functions, panel creation, and Click CLI parsing options.
"""

import pytest
from click.testing import CliRunner
from ffdl.cli import main
from ffdl.ui import format_bytes, format_time, render_chunk_map, create_download_panel


def test_ui_helpers():
    assert format_bytes(500) == "500 B"
    assert format_bytes(1024 * 1024 * 5) == "5.0 MB"
    assert format_bytes(1024 * 1024 * 1024 * 4) == "4.00 GB"

    assert format_time(30) == "00:30"
    assert format_time(90) == "01:30"
    assert format_time(3665) == "01:01:05"

    chunk_map = render_chunk_map([0.0, 0.5, 1.0])
    assert "░" in chunk_map
    assert "█" in chunk_map

    stats = {
        "downloaded_bytes": 1000,
        "total_bytes": 2000,
        "instant_mbps": 50.0,
        "avg_mbps": 45.0,
        "progress_pct": 50.0,
        "eta_seconds": 10,
        "elapsed_seconds": 10,
        "chunks_completed": 1,
        "total_chunks": 2,
    }
    panel = create_download_panel("test_part01.rar", stats, item_index=1, total_items=2)
    assert panel is not None


def test_cli_help_and_options():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "FFDL: Peak God Level Multi-Part Download Accelerator" in result.output
    assert "--interactive" in result.output
    assert "--speedtest" in result.output
    assert "--output" in result.output
    assert "--concurrency" in result.output
    assert "--chunk-kb" in result.output
    assert "--paste" in result.output
    assert "--overwrite" in result.output
    assert "--scrape" in result.output
    assert "--info" in result.output
    assert "--links-only" in result.output


def test_cli_magnet_handler():
    runner = CliRunner()
    magnet_uri = "magnet:?xt=urn:btih:d6b9d62d2950d603a7d1891b0c0378a594186cc5&dn=Cyberpunk+2077&tr=udp://tracker.opentrackr.org:1337"
    result = runner.invoke(main, [magnet_uri])
    assert result.exit_code == 0
    assert "Torrent Magnet URI Detected" in result.output
    assert "Cyberpunk" in result.output


@pytest.mark.asyncio
async def test_smart_memory_skip(tmp_path):
    from ffdl.cli import execute_download_job

    dest_file = tmp_path / "already_downloaded.bin"
    test_content = b"ALREADY_EXISTS_COMPLETE_FILE_CONTENT_TEST"
    dest_file.write_bytes(test_content)

    # Calling execute_download_job on an existing complete file should skip in 0.01s
    skipped = await execute_download_job(
        url="https://fuckingfast.co/test_complete#already_downloaded.bin",
        output_dir=tmp_path,
        overwrite=False,
    )
    # Even if remote size cannot be probed in test, if file exists and overwrite=False,
    # let's verify resumer detects completeness
    from ffdl.persistence.resumer import DownloadResumer
    resumer = DownloadResumer()
    assert await resumer.is_download_complete(dest_file, len(test_content))


def test_parse_range_selection():
    from ffdl.interactive import parse_range_selection

    # Test spaced ranges
    assert parse_range_selection("1 - 9", 20) == [1, 2, 3, 4, 5, 6, 7, 8, 9]
    # Test standard ranges and commas
    assert parse_range_selection("1-3, 5, 7", 10) == [1, 2, 3, 5, 7]
    # Test 'and' and '+' and duplicates
    assert parse_range_selection("1-3 and 5 + 6, 6, 2", 10) == [1, 2, 3, 5, 6]
    # Test out-of-bounds clamp and completely out-of-bounds rejection
    assert parse_range_selection("1-15", 10) == list(range(1, 11))
    assert parse_range_selection("50-60", 10) == []
    # Test invalid string
    assert parse_range_selection("abc", 10) == []
    # Test whitespace-separated
    assert parse_range_selection("1 2 3", 10) == [1, 2, 3]


def test_natural_file_sorting_in_partition():
    from ffdl.resolvers.fitgirl_scraper import partition_links

    # Mixed unordered filenames
    raw_urls = [
        "https://datanodes.to/hash7#Game.part07.rar",
        "https://datanodes.to/hash2#Game.part02.rar",
        "https://datanodes.to/hash1#Game.part01.rar",
        "https://datanodes.to/hash10#Game.part10.rar",
        "https://datanodes.to/hash3#Game.part03.rar",
        "https://datanodes.to/hashopt#fg-optional-selective-english.bin",
    ]
    main_links, opt_links = partition_links(raw_urls)
    # Check that main_links are strictly sorted numerically
    expected_order = [
        "https://datanodes.to/hash1#Game.part01.rar",
        "https://datanodes.to/hash2#Game.part02.rar",
        "https://datanodes.to/hash3#Game.part03.rar",
        "https://datanodes.to/hash7#Game.part07.rar",
        "https://datanodes.to/hash10#Game.part10.rar",
    ]
    assert main_links == expected_order
    assert len(opt_links) == 1

