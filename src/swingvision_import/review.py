"""Staging-JSON persistence and the review-flag gate that guards SQL loading."""

from __future__ import annotations

import json
import re
from pathlib import Path

from .records import MatchRecord

# Characters invalid in Windows filenames (a superset of what's invalid on
# macOS/Linux), plus whitespace collapsed to a single underscore. Opponent
# names are free text, so this can't assume they're already filename-safe.
_UNSAFE_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def slugify_filename(value: str) -> str:
    """Turns free text into a filesystem-safe filename component.

    Args:
        value: The raw text (e.g. an opponent's name) to sanitize.

    Returns:
        The text with filename-unsafe characters replaced by underscores,
        or "unknown" if nothing safe remains.
    """
    slug = _UNSAFE_FILENAME_CHARS.sub("_", value.strip())
    slug = re.sub(r"\s+", "_", slug).strip("._")
    return slug or "unknown"


def save_pending(record: MatchRecord, pending_dir: Path) -> Path:
    """Writes a MatchRecord to the pending-review JSON directory.

    Re-saving a record for the same date/opponent overwrites the existing
    file rather than creating a duplicate.

    Args:
        record: The match to stage for review.
        pending_dir: Directory to write the JSON file into; created if it
            doesn't already exist.

    Returns:
        Path to the written JSON file.
    """
    pending_dir.mkdir(parents=True, exist_ok=True)
    opponent_slug = slugify_filename(record.opponent)
    path = pending_dir / f"{record.date}_{opponent_slug}.json"
    path.write_text(json.dumps(record.to_dict(), indent=2), encoding="utf-8")
    return path


def load_pending(path: Path) -> MatchRecord:
    """Loads a staged MatchRecord back from its JSON file.

    Args:
        path: Path to a JSON file previously written by save_pending.

    Returns:
        The reconstructed MatchRecord.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    return MatchRecord.from_dict(data)


def unresolved_flags(record: MatchRecord) -> list[str]:
    """Lists every point in a record that still needs manual review.

    Args:
        record: The match to check.

    Returns:
        One human-readable description per point with needs_review=True,
        identifying its set, game, point number, and outcome type. Empty
        if the record is fully resolved and safe to finalize into SQL.
    """
    flags = []
    for set_record in record.sets:
        for point in set_record.points:
            if not point.needs_review:
                continue
            message = (
                f"set {set_record.set_number} game {point.game_number} "
                f"point {point.point_number}: '{point.point_end_type}' needs confirmation"
            )
            if point.ai_suggested_point_end_type is not None:
                message += (
                    f" (Claude suggests '{point.ai_suggested_point_end_type}': "
                    f"{point.ai_suggestion_reasoning})"
                )
            flags.append(message)
    return flags
