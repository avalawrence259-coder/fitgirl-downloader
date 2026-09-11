from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class DownloaderInfo:
    id: str
    name: str
    executable_path: Optional[str]
    is_available: bool
    description: str
    cli_flags_supported: List[str]


class DownloaderDetector:
    """
    Auto-detects external download services (IDM, FDM, Aria2, JDownloader)
    across the Windows registry, standard filesystem paths, and PATH environment.
    """

    @classmethod
    def find_idm_path(cls) -> Optional[str]:
        # 1. PATH lookup
        found = shutil.which("IDMan.exe")
        if found and os.path.isfile(found):
            return found

        # 2. Windows Registry lookup
        if sys.platform == "win32":
            try:
                import winreg
                reg_paths = [
                    (winreg.HKEY_CURRENT_USER, r"Software\DownloadManager", "ExePath"),
                    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Internet Download Manager", "Path"),
                    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Internet Download Manager", "Path"),
                ]
                for hive, subkey, val_name in reg_paths:
                    try:
                        with winreg.OpenKey(hive, subkey) as key:
                            val, _ = winreg.QueryValueEx(key, val_name)
                            if val and os.path.isfile(val):
                                return val
                            if val and os.path.isdir(val):
                                candidate = os.path.join(val, "IDMan.exe")
                                if os.path.isfile(candidate):
                                    return candidate
                    except Exception:
                        pass
            except Exception:
                pass

        # 3. Standard Program Files installation paths
        candidates = [
            r"C:\Program Files (x86)\Internet Download Manager\IDMan.exe",
            r"C:\Program Files\Internet Download Manager\IDMan.exe",
        ]
        for c in candidates:
            if os.path.isfile(c):
                return c

        return None

    @classmethod
    def find_fdm_path(cls) -> Optional[str]:
        found = shutil.which("fdm.exe")
        if found and os.path.isfile(found):
            return found

        local_app_data = os.environ.get("LOCALAPPDATA", "")
        candidates = [
            r"C:\Program Files\Softdeluxe\Free Download Manager\fdm.exe",
            r"C:\Program Files (x86)\Softdeluxe\Free Download Manager\fdm.exe",
            r"C:\Program Files\FreeDownloadManager.ORG\Free Download Manager\fdm.exe",
            r"C:\Program Files (x86)\FreeDownloadManager.ORG\Free Download Manager\fdm.exe",
            r"C:\Program Files\Free Download Manager\fdm.exe",
            r"C:\Program Files (x86)\Free Download Manager\fdm.exe",
            os.path.join(local_app_data, "Softdeluxe", "Free Download Manager", "fdm.exe"),
            os.path.join(local_app_data, "Programs", "Free Download Manager", "fdm.exe"),
        ]
        for c in candidates:
            if c and os.path.isfile(c):
                return c

        if sys.platform == "win32":
            try:
                import winreg
                for root in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
                    for sub in [
                        r"Software\Microsoft\Windows\CurrentVersion\Uninstall",
                        r"Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
                    ]:
                        try:
                            k = winreg.OpenKey(root, sub)
                            for i in range(winreg.QueryInfoKey(k)[0]):
                                sk_name = winreg.EnumKey(k, i)
                                sk = winreg.OpenKey(k, sk_name)
                                try:
                                    dname = str(winreg.QueryValueEx(sk, "DisplayName")[0])
                                    if "free download manager" in dname.lower():
                                        # Try DisplayIcon or InstallLocation
                                        try:
                                            icon = str(winreg.QueryValueEx(sk, "DisplayIcon")[0]).strip('"')
                                            if os.path.isfile(icon) and icon.lower().endswith("fdm.exe"):
                                                return icon
                                        except Exception:
                                            pass
                                        try:
                                            loc = str(winreg.QueryValueEx(sk, "InstallLocation")[0]).strip('"')
                                            exe = os.path.join(loc, "fdm.exe")
                                            if os.path.isfile(exe):
                                                return exe
                                        except Exception:
                                            pass
                                except Exception:
                                    pass
                        except Exception:
                            pass
            except Exception:
                pass

        return None

    @classmethod
    def find_aria2_path(cls) -> Optional[str]:
        found = shutil.which("aria2c") or shutil.which("aria2c.exe")
        if found and os.path.isfile(found):
            return found

        candidates = [
            r"C:\tools\aria2\aria2c.exe",
            r"C:\ProgramData\chocolatey\bin\aria2c.exe",
        ]
        for c in candidates:
            if os.path.isfile(c):
                return c

        return None

    @classmethod
    def find_jdownloader_path(cls) -> Optional[str]:
        found = shutil.which("JDownloader2.exe")
        if found and os.path.isfile(found):
            return found

        local_app_data = os.environ.get("LOCALAPPDATA", "")
        candidates = [
            os.path.join(local_app_data, "JDownloader 2.0", "JDownloader2.exe"),
            r"C:\Program Files\JDownloader 2.0\JDownloader2.exe",
            r"C:\Program Files (x86)\JDownloader 2.0\JDownloader2.exe",
        ]
        for c in candidates:
            if c and os.path.isfile(c):
                return c

        return None

    @classmethod
    def detect_all(cls) -> Dict[str, DownloaderInfo]:
        """Scan whole system and return all supported engines with availability status."""
        results: Dict[str, DownloaderInfo] = {}

        # 1. FFDL Built-in (Always available & Recommended)
        results["ffdl"] = DownloaderInfo(
            id="ffdl",
            name="⚡ FFDL Built-in Accelerator (Recommended) [100% Automated, Zero-Click]",
            executable_path=sys.executable,
            is_available=True,
            description="16-Stream Direct Concurrency with Smart Resumption and Anti-Stall Guard",
            cli_flags_supported=["--concurrency", "--chunk-kb", "--overwrite"],
        )

        # 2. IDM
        idm_exe = cls.find_idm_path()
        results["idm"] = DownloaderInfo(
            id="idm",
            name="📥 Internet Download Manager (IDM) [Silent Background Queue]",
            executable_path=idm_exe,
            is_available=bool(idm_exe),
            description="Automated Silent Queue Injection via IDMan.exe (/d /p /f /n /a /s)",
            cli_flags_supported=["/d", "/p", "/f", "/n", "/a", "/s"],
        )

        # 3. FDM
        fdm_exe = cls.find_fdm_path()
        results["fdm"] = DownloaderInfo(
            id="fdm",
            name="🌐 Free Download Manager (FDM) [GUI Mode]",
            executable_path=fdm_exe,
            is_available=bool(fdm_exe),
            description="Dispatches direct links to Free Download Manager",
            cli_flags_supported=[],
        )

        # 4. Aria2
        aria2_exe = cls.find_aria2_path()
        results["aria2"] = DownloaderInfo(
            id="aria2",
            name="🦅 Aria2c High-Speed CLI",
            executable_path=aria2_exe,
            is_available=bool(aria2_exe),
            description="Ultra-lightweight multi-source command-line downloader",
            cli_flags_supported=["--concurrency", "--output"],
        )

        # 5. JDownloader
        jd_exe = cls.find_jdownloader_path()
        results["jdownloader"] = DownloaderInfo(
            id="jdownloader",
            name="☕ JDownloader 2",
            executable_path=jd_exe,
            is_available=bool(jd_exe),
            description="Automated package and multi-host archive queue",
            cli_flags_supported=["--output"],
        )

        return results

    @classmethod
    def get_available(cls) -> Dict[str, DownloaderInfo]:
        """Return only engines that are physically present and runnable on this system."""
        all_engines = cls.detect_all()
        return {k: v for k, v in all_engines.items() if v.is_available}
