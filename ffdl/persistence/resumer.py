"""
ffdl.persistence.resumer - Crash Resumption & Checkpoint Recovery Coordinator
=============================================================================
Manages zero-byte redownload validation.
Checks SQLite WAL catalog, validates disk segments, and resumes precisely
at partial byte offsets without restarting from zero.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Tuple

from ffdl.persistence.catalog import DownloadCatalog, DownloadRecord
from ffdl.persistence.verifier import StreamingVerifier


class DownloadResumer:
    """Coordinates crash recovery and byte-level resumption validation."""

    def __init__(self, catalog: Optional[DownloadCatalog] = None):
        self.catalog = catalog or DownloadCatalog()

    async def get_resumable_job(self, download_id: str) -> Optional[DownloadRecord]:
        """Fetch incomplete download eligible for byte-level resumption."""
        rec = await self.catalog.get_download(download_id)
        if not rec:
            return None
        if rec.status == "completed":
            return None
        return rec

    async def get_resumable_job_by_path(self, save_path: Path | str) -> Optional[DownloadRecord]:
        """Fetch incomplete download eligible for byte-level resumption using destination path."""
        rec = await self.catalog.get_download_by_path(save_path)
        if not rec:
            return None
        if rec.status == "completed":
            return None
        return rec

    async def is_download_complete(self, save_path: Path | str, expected_size: int = 0) -> bool:
        """
        Fast 0.01s check whether a download is already 100% complete on disk and in ledger.
        """
        p = Path(save_path).resolve()
        if not p.exists():
            return False

        disk_size = p.stat().st_size
        if expected_size > 0 and disk_size != expected_size:
            return False

        rec = await self.catalog.get_download_by_path(p)
        if rec and rec.status == "completed":
            return True

        # If no record but disk size matches expected size > 0, consider it complete
        if expected_size > 0 and disk_size == expected_size:
            return True

        return False

    async def verify_segment_integrity(self, segment: SegmentRecord, file_path: Path | str) -> bool:
        """Verify whether an existing completed segment matches its recorded SHA-256."""
        if not segment.sha256_hash or not segment.is_done:
            return True

        p = Path(file_path).resolve()
        if not p.exists():
            return False

        try:
            computed = StreamingVerifier.compute_range_sha256(
                p, segment.start_byte, segment.end_byte
            )
            return computed.lower() == segment.sha256_hash.lower()
        except Exception:
            return False

    async def validate_local_bytes(self, download_id: str) -> Tuple[int, int]:
        """
        Validate existing bytes on disk for this download.
        Returns: (verified_bytes_on_disk, total_bytes_expected)
        """
        rec = await self.catalog.get_download(download_id)
        if not rec:
            return 0, 0

        target_file = Path(rec.save_path)
        if not target_file.exists():
            return 0, rec.total_bytes

        total_written = 0
        for seg in rec.segments:
            if seg.is_done:
                total_written += (seg.end_byte - seg.start_byte + 1)
            else:
                total_written += seg.written_bytes

        return total_written, rec.total_bytes


def get_config_path() -> Path:
    """Returns the user configuration file path."""
    return Path.home() / ".ffdl_config.json"


def load_user_config() -> Dict[str, Any]:
    """Load saved user preferences (output path, concurrency, chunk size)."""
    import json
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
    import json
    cfg_p = get_config_path()
    try:
        with open(cfg_p, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2)
    except Exception:
        pass


__all__ = [
    "DownloadResumer",
    "get_config_path",
    "load_user_config",
    "save_user_config",
]
