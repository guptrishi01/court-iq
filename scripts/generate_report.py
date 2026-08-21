"""CLI: generate a self-contained match report.html from a finalized match.

Usage:
    python scripts/generate_report.py <match_id>
    python scripts/generate_report.py <match_id> --no-ai
    python scripts/generate_report.py <match_id> --output my_report.html
    python scripts/generate_report.py --history

Requires the match to already be finalized into SQL (pipeline.finalize()) -
this is the last step in the pipeline, after ingest -> review -> resolve/
suggest -> finalize. By default also generates (or loads a cached) AI
coaching report, which spends real API money the first time for a given
match_id; --no-ai renders stats only. --history renders the cross-match
trend report instead of a single match's report.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "src"))
sys.path.insert(0, str(_REPO_ROOT))

from ai.pipeline import AICoachPipeline  # noqa: E402
from logging_config import configure_logging  # noqa: E402
from reports.render import render_history_report_to_file, render_match_report_to_file  # noqa: E402
from scripts.client import get_anthropic_client  # noqa: E402
from stats.queries import all_match_ids, match_stats  # noqa: E402
from swingvision_import.config import ImportConfig  # noqa: E402
from swingvision_import.db import get_connection  # noqa: E402


def main() -> None:
    """Parses CLI args and renders a match or history report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("match_id", type=int, nargs="?", help="The match to render a report for.")
    parser.add_argument(
        "--history", action="store_true", help="Render the cross-match trend report instead."
    )
    parser.add_argument(
        "--no-ai", action="store_true", help="Skip AI coaching - render stats only, no API call."
    )
    parser.add_argument(
        "--output", type=Path, help="Output .html path (defaults per ReportConfig)."
    )
    args = parser.parse_args()
    if not args.history and args.match_id is None:
        parser.error("match_id is required unless --history is given")

    configure_logging()
    import_config = ImportConfig()
    connection = get_connection(import_config.db_path, import_config.schema_path)

    if args.history:
        stats = [match_stats(connection, match_id) for match_id in all_match_ids(connection)]
        output_path = render_history_report_to_file(stats, output_path=args.output)
    else:
        stats = match_stats(connection, args.match_id)
        coaching_report = None
        if not args.no_ai:
            client = get_anthropic_client()
            coaching_report = AICoachPipeline().generate(connection, client, args.match_id)
        output_path = render_match_report_to_file(
            stats, output_path=args.output, coaching_report=coaching_report
        )

    connection.close()
    print(f"Report written to {output_path}")


if __name__ == "__main__":
    main()
