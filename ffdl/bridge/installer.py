"""
ffdl.bridge.installer - Automated Native Messaging Host & Registry Installer
============================================================================
Registers `com.ffdl.native_host` in Windows HKCU registry for Google Chrome,
Microsoft Edge, and Mozilla Firefox.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

HOST_NAME = "com.ffdl.native_host"


def get_bridge_dir() -> Path:
    config_dir = Path.home() / ".ffdl" / "bridge"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def create_launcher_script(bridge_dir: Path) -> Path:
    """Creates a .bat launcher script for Windows or shell script for POSIX."""
    if sys.platform == "win32":
        bat_path = bridge_dir / "native_host.bat"
        python_exe = sys.executable
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write("@echo off\n")
            f.write(f'"{python_exe}" -m ffdl.bridge.native_host %*\n')
        return bat_path
    else:
        sh_path = bridge_dir / "native_host.sh"
        python_exe = sys.executable
        with open(sh_path, "w", encoding="utf-8") as f:
            f.write("#!/bin/sh\n")
            f.write(f'exec "{python_exe}" -m ffdl.bridge.native_host "$@"\n')
        os.chmod(sh_path, 0o755)
        return sh_path


def create_manifest(
    launcher_path: Path,
    bridge_dir: Path,
    is_firefox: bool = False,
    extension_id: Optional[str] = None,
) -> Path:
    """Creates Chrome or Firefox Native Messaging JSON Manifest."""
    manifest_name = f"{HOST_NAME}.firefox.json" if is_firefox else f"{HOST_NAME}.json"
    manifest_path = bridge_dir / manifest_name

    manifest_data: Dict[str, Any] = {
        "name": HOST_NAME,
        "description": "FFDL Download Accelerator Native Messaging Host",
        "path": str(launcher_path),
        "type": "stdio",
    }

    if is_firefox:
        manifest_data["allowed_extensions"] = [
            extension_id or "ffdl-extension@antigravity",
            "ffdl-extension@antigravity",
        ]
    else:
        origins = [
            "chrome-extension://*/",
            "chrome-extension://com.ffdl.extension/",
        ]
        if extension_id:
            clean_id = extension_id.strip().replace("chrome-extension://", "").rstrip("/")
            origins.insert(0, f"chrome-extension://{clean_id}/")
        manifest_data["allowed_origins"] = origins

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    return manifest_path


def install_windows_registry(manifest_path: Path, is_firefox: bool = False) -> bool:
    """Installs native messaging host into Windows HKCU Registry."""
    if sys.platform != "win32":
        return False

    try:
        import winreg

        targets = []
        if is_firefox:
            targets.append(f"Software\\Mozilla\\NativeMessagingHosts\\{HOST_NAME}")
        else:
            targets.append(f"Software\\Google\\Chrome\\NativeMessagingHosts\\{HOST_NAME}")
            targets.append(f"Software\\Microsoft\\Edge\\NativeMessagingHosts\\{HOST_NAME}")

        for subkey_path in targets:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, subkey_path) as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, str(manifest_path))

        return True
    except Exception as e:
        print(f"Registry installation warning: {e}")
        return False


def install_bridge(extension_id: Optional[str] = None) -> Dict[str, Any]:
    """Automates creation of launcher, manifests, and registry entries."""
    bridge_dir = get_bridge_dir()
    launcher_path = create_launcher_script(bridge_dir)
    chrome_manifest = create_manifest(launcher_path, bridge_dir, is_firefox=False, extension_id=extension_id)
    firefox_manifest = create_manifest(launcher_path, bridge_dir, is_firefox=True, extension_id=extension_id)

    chrome_ok = install_windows_registry(chrome_manifest, is_firefox=False)
    firefox_ok = install_windows_registry(firefox_manifest, is_firefox=True)

    from ffdl.bridge.auth import get_or_create_auth_token
    token = get_or_create_auth_token()

    return {
        "launcher": str(launcher_path),
        "chrome_manifest": str(chrome_manifest),
        "firefox_manifest": str(firefox_manifest),
        "chrome_installed": chrome_ok,
        "firefox_installed": firefox_ok,
        "auth_token": token,
    }
