"""Best-guess configuration for parsing SwingVision's exported .xlsx match file.

SwingVision publishes no official export schema (no public API, closed help
center, JS-rendered marketing site) — the sheet/column names below are our
best guess from secondhand reporting. When a real exported match is available,
correct the aliases here, not the parsing logic in parse.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_SHEET_NAMES: dict[str, str] = {
    "sets": "Sets",
    "games": "Games",
    "points": "Points",
}

DEFAULT_COLUMN_ALIASES: dict[str, dict[str, list[str]]] = {
    "sets": {
        "set_number": ["Set #", "Set", "SetNumber"],
        "winner": ["Set Winner", "Winner"],
        "games_won": ["Games Won"],
        "games_lost": ["Games Lost"],
    },
    "games": {
        "set_number": ["Set #", "Set"],
        "game_number": ["Game #", "Game", "GameNumber"],
        "server": ["Server", "Serving Player"],
        "winner": ["Game Winner", "Winner"],
    },
    "points": {
        "set_number": ["Set #", "Set"],
        "game_number": ["Game #", "Game", "GameNumber"],
        "point_number": ["Point #", "Point", "PointNumber"],
        "server": ["Server", "Serving Player"],
        "winner": ["Point Winner", "Winner"],
        "first_serve_in": ["1st Serve In", "First Serve In"],
        "second_serve_in": ["2nd Serve In", "Second Serve In"],
        "end_type": ["Shot Type", "Point End Type", "Outcome"],
    },
}

# SwingVision's AI classification for these point-outcome labels is unreliable
# enough that a match may not be finalized into SQL until a human confirms
# them (see review.unresolved_flags / load.finalize_and_load).
NEEDS_REVIEW_END_TYPES: frozenset[str] = frozenset(
    {"winner", "unforced_error", "forced_error"}
)


@dataclass(frozen=True)
class ImportConfig:
    """Configuration for parsing a SwingVision export and loading it into SQL.

    Attributes:
        sheet_names: Maps each logical sheet key ("sets", "games", "points")
            to the sheet name expected in the .xlsx workbook.
        column_aliases: Maps each sheet key to a mapping of canonical field
            name -> list of header strings that may represent it in a real
            export. Update this, not the parsing logic in parse.py, once a
            real export's actual headers are known.
        needs_review_end_types: Point-outcome labels whose AI classification
            is unreliable enough that a match may not be finalized into SQL
            until a human confirms them.
        pending_dir: Directory where staged (pre-review) match JSON files
            are written by review.save_pending.
        db_path: Path to the SQLite database file.
        schema_path: Path to the SQL schema script applied on first use.
    """

    sheet_names: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_SHEET_NAMES))
    column_aliases: dict[str, dict[str, list[str]]] = field(
        default_factory=lambda: {k: dict(v) for k, v in DEFAULT_COLUMN_ALIASES.items()}
    )
    needs_review_end_types: frozenset[str] = NEEDS_REVIEW_END_TYPES
    pending_dir: Path = _REPO_ROOT / "src" / "swingvision_import" / "pending"
    db_path: Path = _REPO_ROOT / "data" / "court_iq.db"
    schema_path: Path = _REPO_ROOT / "data" / "schema.sql"
