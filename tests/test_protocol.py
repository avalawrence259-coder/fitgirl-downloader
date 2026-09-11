"""
tests.test_protocol - Protocol Parser, Deep Link, and Daemon Test Suite
=======================================================================
"""

import json
from unittest.mock import MagicMock, patch
import pytest

from ffdl.protocol import (
    build_protocol_url,
    parse_protocol_url,
    is_windows_protocol_registered,
    register_windows_protocol,
    unregister_windows_protocol,
)
from ffdl.daemon import ExtensionAPIHandler


def test_parse_protocol_url_full():
    uri = "ffdl://download?url=https%3A%2F%2Ffitgirl-repacks.site%2Fgame%2F&hoster=fuckingfast&main_only=1&out=D%3A%5CGames"
    res = parse_protocol_url(uri)
    assert res["action"] == "download"
    assert res["url"] == "https://fitgirl-repacks.site/game/"
    assert res["hoster"] == "fuckingfast"
    assert res["main_only"] is True
    assert res["out_dir"] == "D:\\Games"


def test_parse_protocol_url_variations():
    # Test bare scheme
    uri1 = "ffdl:download?url=https://example.com/test&hoster=datanodes&all=1"
    res1 = parse_protocol_url(uri1)
    assert res1["url"] == "https://example.com/test"
    assert res1["hoster"] == "datanodes"
    assert res1["all_parts"] is True
    assert res1["main_only"] is False

    # Test select query
    uri2 = "ffdl://download?url=https://example.com/test&select=french,ost"
    res2 = parse_protocol_url(uri2)
    assert res2["select"] == "french,ost"


def test_build_protocol_url():
    built = build_protocol_url(
        url="https://fitgirl-repacks.site/game/",
        hoster="filekeeper",
        main_only=True,
        out_dir="C:\\Downloads",
    )
    assert built.startswith("ffdl://download?")
    assert "hoster=filekeeper" in built
    assert "main_only=1" in built

    parsed = parse_protocol_url(built)
    assert parsed["url"] == "https://fitgirl-repacks.site/game/"
    assert parsed["hoster"] == "filekeeper"
    assert parsed["main_only"] is True
    assert parsed["out_dir"] == "C:\\Downloads"


def test_windows_protocol_registration_flow():
    """Verify registry mock flow for protocol registration."""
    with patch("winreg.CreateKey") as mock_create_key, \
         patch("winreg.SetValueEx") as mock_set_value:
        mock_create_key.return_value.__enter__.return_value = MagicMock()
        success = register_windows_protocol("python.exe")
        assert success is True
        assert mock_set_value.call_count >= 3


def test_daemon_api_health_payload():
    """Test daemon API status endpoint."""
    from io import BytesIO

    handler = ExtensionAPIHandler.__new__(ExtensionAPIHandler)
    handler.path = "/health"
    handler.command = "GET"
    handler.wfile = BytesIO()
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()

    handler.do_GET()
    output = handler.wfile.getvalue().decode("utf-8")
    data = json.loads(output)
    assert data["status"] == "online"
    assert data["app"] == "ffdl-accelerator"
