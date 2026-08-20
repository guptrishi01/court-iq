"""Configuration for the intake web UI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class WebAppConfig:
    """Settings for where uploaded files land.

    Attributes:
        uploads_dir: Where uploaded SwingVision .xlsx exports are staged
            before parsing (gitignored - personal match data, not code).
        media_dir: Where uploaded match video is stored, one subdirectory
            per match (gitignored - personal match data, not code).
        max_content_length: Flask's upload size cap, in bytes. Generous by
            default since match video can be large.
    """

    uploads_dir: Path = _REPO_ROOT / "data" / "uploads"
    media_dir: Path = _REPO_ROOT / "data" / "media"
    max_content_length: int = 2 * 1024 * 1024 * 1024
