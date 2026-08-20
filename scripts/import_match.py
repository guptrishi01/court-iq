"""CLI: SwingVision .xlsx -> staged pending-review JSON.

Usage:
    python scripts/import_match.py first-half.xlsx --date 2026-08-18 \\
        --opponent "Real Opponent" --result W [--suggest]

Only stages the match for review (ingest) - finalize() into SQL is a
separate, deliberate step (not run here), same two-stage design the
pipeline itself enforces. --suggest additionally runs Claude-assisted
review suggestions on the staged points; it spends real API money, so it's
opt-in via this flag rather than always running.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "src"))
sys.path.insert(0, str(_REPO_ROOT))

from logging_config import configure_logging  # noqa: E402
from scripts.client import get_anthropic_client  # noqa: E402
from swingvision_import.pipeline import SwingVisionImportPipeline  # noqa: E402
from swingvision_import.review import load_pending, unresolved_flags  # noqa: E402


def main() -> None:
    """Parses CLI args, runs ingest (and optionally suggest), and reports flags."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("xlsx_path", type=Path)
    parser.add_argument("--date", required=True, help="ISO-format match date.")
    parser.add_argument("--opponent", required=True)
    parser.add_argument("--result", required=True, choices=["W", "L"])
    parser.add_argument(
        "--suggest",
        action="store_true",
        help="Also run Claude-assisted review suggestions (spends real API money).",
    )
    args = parser.parse_args()

    configure_logging()

    pipeline = SwingVisionImportPipeline()
    json_path = pipeline.ingest(
        args.xlsx_path, date=args.date, opponent=args.opponent, result=args.result
    )
    print(f"Staged: {json_path}")

    if args.suggest:
        client = get_anthropic_client()
        pipeline.suggest(client, json_path)
        print("Suggestions added.")

    flags = unresolved_flags(load_pending(json_path))
    print(f"{len(flags)} point(s) still need review before this match can be finalized.")


if __name__ == "__main__":
    main()
