from __future__ import annotations

from pathlib import Path

from reports.config import ReportConfig


def test_default_output_dir_is_under_the_reports_package():
    config = ReportConfig()

    assert config.output_dir.name == "output"
    assert config.output_dir.parent.name == "reports"


def test_output_dir_can_be_overridden():
    custom = Path("/tmp/custom-reports")

    config = ReportConfig(output_dir=custom)

    assert config.output_dir == custom
