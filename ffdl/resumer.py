"""
ffdl.resumer - Deprecated Root Resumer Module
============================================
This module is deprecated and will be removed in a future major version.
Please import from `ffdl.persistence.resumer` instead.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Any, Dict, Optional

warnings.warn(
    "ffdl.resumer is deprecated; use ffdl.persistence.resumer instead.",
    DeprecationWarning,
    stacklevel=2,
)

from ffdl.persistence.resumer import DownloadResumer


def get_meta_path(target_file_path: Path) -> Path:
    """Returns the .ffmeta state file path for a given target file."""
    return target_file_path.parent / f"{target_file_path.name}.ffmeta"


def load_meta(meta_path: Path) -> Optional[Dict[str, Any]]:
    """Load existing download checkpoint if present."""
    if not meta_path.exists():
        return None
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_meta(meta_path: Path, meta_data: Dict[str, Any]):
    """Atomically save checkpoint to disk."""
    temp_path = meta_path.parent / f"{meta_path.name}.tmp"
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(meta_data, f, indent=2)
        if temp_path.exists():
            temp_path.replace(meta_path)
    except Exception:
        pass


def remove_meta(meta_path: Path):
    """Remove checkpoint state on 100% successful completion."""
    try:
        if meta_path.exists():
            meta_path.unlink()
    except Exception:
        pass


def get_config_path() -> Path:
    """Returns the user configuration file path."""
    return Path.home() / ".ffdl_config.json"


def load_user_config() -> Dict[str, Any]:
    """Load saved user preferences (output path, concurrency, chunk size)."""
    cfg_p = get_config_path()
    defaults = {
        "output_dir": str(Path.home() / "Downloads"),
        "concurrency": 16,
        "chunk_kb": 256,
    }
    if not cfg_p.exists():
        return defaults
    try:
        with open(cfg_p, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {**defaults, **data}
    except Exception:
        return defaults


def save_user_config(config_data: Dict[str, Any]):
    """Persist user download configuration preferences."""
    cfg_p = get_config_path()
    try:
        with open(cfg_p, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2)
    except Exception:
        pass


__all__ = [
    "DownloadResumer",
    "get_meta_path",
    "load_meta",
    "save_meta",
    "remove_meta",
    "get_config_path",
    "load_user_config",
    "save_user_config",
]
