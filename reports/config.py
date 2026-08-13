"""Configuration for report generation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class ReportConfig:
    """Settings for where generated report HTML files are written.

    Attributes:
        output_dir: Default directory for rendered reports (gitignored —
            generated output, not code). Callers can always override with
            an explicit output_path instead of relying on this default.
    """

    output_dir: Path = _REPO_ROOT / "reports" / "output"
