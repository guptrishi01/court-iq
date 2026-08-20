"""CLI: parse hand-written review answers into structured point fields, and
apply them.

Usage:
    # 1. Hand-edit the pending JSON, writing a plain-language review_answer
    #    onto whichever flagged points you've actually reviewed - no need
    #    to touch point_end_type/point_won/net_approach directly.
    # 2. Ask Claude to parse those answers into resolved_* fields:
    python scripts/resolve_reviews.py path/to/pending.json --resolve

    # 3. Inspect the pending JSON's resolved_*/resolution_reasoning fields,
    #    then apply them (only this step actually clears needs_review):
    python scripts/resolve_reviews.py path/to/pending.json --apply

--resolve spends real API money (one call per point with a review_answer)
and never touches needs_review - it only fills in resolved_*. --apply is
free (no API call) and is the only thing that copies resolved_* onto the
real fields and clears needs_review; a point resolve() couldn't parse (or
that never had a review_answer) is left alone and still blocks finalize().
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
from swingvision_import.review import unresolved_flags  # noqa: E402


def main() -> None:
    """Parses CLI args and runs --resolve and/or --apply against a pending JSON."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("json_path", type=Path, help="Path to a staged pending-review JSON file.")
    parser.add_argument(
        "--resolve",
        action="store_true",
        help="Parse every point's review_answer into resolved_* fields (spends real API money).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply resolved_* fields onto the real point fields and clear needs_review.",
    )
    args = parser.parse_args()
    if not args.resolve and not args.apply:
        parser.error("pass --resolve, --apply, or both")

    configure_logging()
    pipeline = SwingVisionImportPipeline()

    if args.resolve:
        client = get_anthropic_client()
        pipeline.resolve(client, args.json_path)
        print("Review answers parsed.")

    if args.apply:
        record = pipeline.apply_resolutions(args.json_path)
        print("Resolutions applied.")
        flags = unresolved_flags(record)
        print(f"{len(flags)} point(s) still need review before this match can be finalized.")
        for flag in flags:
            print(f"  - {flag}")


if __name__ == "__main__":
    main()
