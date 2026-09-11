"""
ffdl.bridge.auth - Bearer Token Authentication for Localhost Daemon
===================================================================
Generates, stores, and validates cryptographically secure 256-bit
hex tokens stored in ~/.ffdl/bridge_auth.json with strict file permissions.
"""

from __future__ import annotations

import json
import os
import secrets
import stat
import sys
import time
from pathlib import Path
from typing import Optional


def get_auth_file_path() -> Path:
    """Returns ~/.ffdl/bridge_auth.json location."""
    config_dir = Path.home() / ".ffdl"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "bridge_auth.json"


def get_or_create_auth_token() -> str:
    """
    Retrieves existing Bearer token or generates a new 256-bit token
    and saves it to ~/.ffdl/bridge_auth.json with restricted permissions (0600).
    """
    auth_path = get_auth_file_path()
    if auth_path.exists():
        try:
            with open(auth_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                token = data.get("token")
                if token and isinstance(token, str) and len(token) >= 32:
                    return token
        except Exception:
            pass

    token = secrets.token_hex(32)
    auth_data = {
        "token": token,
        "created_at": time.time(),
        "algorithm": "bearer-hex-256",
    }
    tmp_path = auth_path.parent / f"auth.tmp.{os.getpid()}"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(auth_data, f, indent=2)
        f.flush()
        try:
            os.fsync(f.fileno())
        except Exception:
            pass

    if sys.platform != "win32":
        try:
            os.chmod(tmp_path, stat.S_IRUSR | stat.S_IWUSR)  # 0600
        except Exception:
            pass

    os.replace(tmp_path, auth_path)
    return token


def verify_auth_token(token: Optional[str]) -> bool:
    """
    Verifies Bearer token against stored ~/.ffdl/bridge_auth.json in constant time.
    """
    if not token or not isinstance(token, str):
        return False

    clean_token = token.strip()
    if clean_token.lower().startswith("bearer "):
        clean_token = clean_token[7:].strip()

    expected = get_or_create_auth_token()
    return secrets.compare_digest(clean_token, expected)
