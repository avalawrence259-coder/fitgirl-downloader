"""
Unit and integration tests for authenticated Loopback RPC Daemon (Port 41194).
"""

import json
import threading
import time
import urllib.request
import urllib.error
import pytest

from ffdl.bridge.auth import (
    get_or_create_auth_token,
    verify_auth_token,
)
from ffdl.bridge.server import (
    BridgeServer,
    BridgeRequestHandler,
)

TEST_PORT = 41198


@pytest.fixture(scope="module")
def bridge_test_server():
    server = BridgeServer(host="127.0.0.1", port=TEST_PORT)
    t = threading.Thread(target=server.start, daemon=True)
    t.start()
    time.sleep(0.3)
    yield server
    server.shutdown()


def test_auth_token_lifecycle():
    token = get_or_create_auth_token()
    assert isinstance(token, str)
    assert len(token) >= 32
    assert verify_auth_token(token) is True
    assert verify_auth_token(f"Bearer {token}") is True
    assert verify_auth_token("invalid-token") is False
    assert verify_auth_token("") is False


def test_health_endpoint(bridge_test_server):
    req = urllib.request.Request(f"http://127.0.0.1:{TEST_PORT}/health")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["status"] == "online"
        assert data["service"] == "ffdl-bridge"


def test_queue_without_auth_succeeds(bridge_test_server):
    payload = json.dumps({"url": "https://fitgirl-repacks.site/game/"}).encode("utf-8")
    req = urllib.request.Request(
        f"http://127.0.0.1:{TEST_PORT}/api/v1/queue",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["status"] == "queued"


def test_queue_with_invalid_token_fails(bridge_test_server):
    payload = json.dumps({"url": "https://fitgirl-repacks.site/game/"}).encode("utf-8")
    req = urllib.request.Request(
        f"http://127.0.0.1:{TEST_PORT}/api/v1/queue",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer bad-token-12345",
        },
    )
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(req)
    assert exc_info.value.code == 401


def test_queue_with_valid_token_succeeds(bridge_test_server):
    token = get_or_create_auth_token()
    payload = json.dumps({
        "url": "https://fitgirl-repacks.site/prince-of-persia/",
        "hoster": "fuckingfast",
        "main_only": True,
    }).encode("utf-8")

    req = urllib.request.Request(
        f"http://127.0.0.1:{TEST_PORT}/api/v1/queue",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["status"] == "queued"
        assert data["hoster"] == "fuckingfast"
        assert data["main_only"] is True


def test_cors_headers(bridge_test_server):
    req = urllib.request.Request(
        f"http://127.0.0.1:{TEST_PORT}/api/v1/queue",
        method="OPTIONS",
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 204
        headers = dict(resp.headers)
        assert headers.get("Access-Control-Allow-Origin") == "*"
        assert "Authorization" in headers.get("Access-Control-Allow-Headers", "")
