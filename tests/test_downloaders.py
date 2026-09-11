import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from ffdl.downloaders.detector import DownloaderDetector, DownloaderInfo
from ffdl.downloaders.dispatcher import DownloaderDispatcher
from ffdl.interactive import choose_downloader_engine


def test_downloader_detector_structure():
    all_engines = DownloaderDetector.detect_all()
    assert "ffdl" in all_engines
    assert "idm" in all_engines
    assert "fdm" in all_engines
    assert "aria2" in all_engines
    assert "jdownloader" in all_engines

    for name, info in all_engines.items():
        assert isinstance(info, DownloaderInfo)
        assert info.id == name
        assert isinstance(info.name, str)
        assert isinstance(info.is_available, bool)
        assert isinstance(info.cli_flags_supported, list)


def test_downloader_detector_ffdl_always_available():
    available = DownloaderDetector.get_available()
    assert "ffdl" in available
    assert available["ffdl"].is_available is True
    assert available["ffdl"].executable_path is not None


def test_downloader_detector_idm_detection():
    idm_path = DownloaderDetector.find_idm_path()
    # On Windows where IDM is installed, this will return the path
    if idm_path:
        assert os.path.isfile(idm_path)
        assert "IDMan.exe" in idm_path


@pytest.mark.asyncio
async def test_downloader_dispatcher_idm(tmp_path):
    executed_cmds = []

    def mock_run(cmd, *args, **kwargs):
        executed_cmds.append(cmd)
        return MagicMock(returncode=0)

    test_urls = [
        "https://datanodes.to/mock1#Game.part01.rar",
        "https://datanodes.to/mock2#Game.part02.rar",
    ]

    with patch("subprocess.run", side_effect=mock_run):
        with patch.object(
            DownloaderDispatcher,
            "resolve_url_info",
            side_effect=lambda u: {
                "direct_url": u.replace("datanodes.to", "cdn.datanodes.to"),
                "filename": u.split("#")[-1],
                "total_size": 1000,
            },
        ):
            success = await DownloaderDispatcher.dispatch_to_idm(
                idm_exe=r"C:\Program Files (x86)\Internet Download Manager\IDMan.exe",
                urls=test_urls,
                output_dir=tmp_path,
                start_queue=True,
            )
            assert success is True

    # 2 files queued + 1 queue start command
    assert len(executed_cmds) == 3
    # First part
    assert executed_cmds[0] == [
        r"C:\Program Files (x86)\Internet Download Manager\IDMan.exe",
        "/d", "https://cdn.datanodes.to/mock1#Game.part01.rar",
        "/p", str(tmp_path.resolve()),
        "/f", "Game.part01.rar",
        "/n",
        "/a",
    ]
    # Second part
    assert executed_cmds[1] == [
        r"C:\Program Files (x86)\Internet Download Manager\IDMan.exe",
        "/d", "https://cdn.datanodes.to/mock2#Game.part02.rar",
        "/p", str(tmp_path.resolve()),
        "/f", "Game.part02.rar",
        "/n",
        "/a",
    ]
    # Start queue
    assert executed_cmds[2] == [
        r"C:\Program Files (x86)\Internet Download Manager\IDMan.exe",
        "/s",
    ]


@pytest.mark.asyncio
async def test_downloader_dispatcher_fdm(tmp_path):
    executed_cmds = []

    def mock_run(cmd, *args, **kwargs):
        executed_cmds.append(cmd)
        return MagicMock(returncode=0)

    test_urls = ["https://mock.cdn/file1.rar"]

    with patch("subprocess.run", side_effect=mock_run):
        with patch.object(
            DownloaderDispatcher,
            "resolve_url_info",
            return_value={"direct_url": "https://mock.cdn/file1.rar", "filename": "file1.rar", "total_size": 100},
        ):
            success = await DownloaderDispatcher.dispatch_to_fdm(
                fdm_exe="fdm.exe",
                urls=test_urls,
                output_dir=tmp_path,
            )
            assert success is True
    assert len(executed_cmds) == 1
    assert executed_cmds[0] == ["fdm.exe", "--url", "https://mock.cdn/file1.rar", "--folder", str(tmp_path.resolve())]


def test_choose_downloader_engine_preferred():
    # Preferred ffdl
    assert choose_downloader_engine(preferred="ffdl", interactive_prompt=False) == "ffdl"
    # Preferred non-existent falls back to ffdl
    assert choose_downloader_engine(preferred="non_existent_engine_xyz", interactive_prompt=False) == "ffdl"
