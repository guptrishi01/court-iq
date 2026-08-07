"""Orchestrates the two-step SwingVision import flow.

ingest() never touches SQL — it only stages a reviewable JSON file.
finalize() is the only path into the database, and delegates the
review-flag gate to load.finalize_and_load.
"""

from __future__ import annotations

import logging
from pathlib import Path

from . import db, load, review
from .config import ImportConfig
from .parse import SwingVisionParser
from .transform import transform

logger = logging.getLogger(__name__)


class SwingVisionImportPipeline:
    """Orchestrates the two-step SwingVision import flow.

    ingest() never touches SQL — it only stages a reviewable JSON file.
    finalize() is the only path into the database, and delegates the
    review-flag gate to load.finalize_and_load.
    """

    def __init__(self, config: ImportConfig | None = None) -> None:
        """Initializes the pipeline.

        Args:
            config: Sheet/column aliases and file paths to use. Defaults to
                ImportConfig() if not given.
        """
        self.config = config or ImportConfig()
        self._parser = SwingVisionParser(self.config)

    def ingest(
        self,
        xlsx_path: Path,
        *,
        date: str,
        opponent: str,
        result: str,
        **match_overrides: object,
    ) -> Path:
        """Parses a SwingVision export and stages it for review.

        Args:
            xlsx_path: Path to the SwingVision .xlsx export.
            date: ISO-format date of the match.
            opponent: Opponent's name.
            result: Match result, "W" or "L".
            **match_overrides: Additional MatchRecord fields (e.g.
                energy_rating, pros, cons, location).

        Returns:
            Path to the staged pending-review JSON file.
        """
        raw = self._parser.parse(xlsx_path)
        record = transform(
            raw,
            date=date,
            opponent=opponent,
            result=result,
            config=self.config,
            source_file=str(xlsx_path),
            **match_overrides,
        )
        json_path = review.save_pending(record, self.config.pending_dir)
        flags = review.unresolved_flags(record)
        logger.info(
            "Staged %s vs %s at %s (%d point(s) need review)",
            date, opponent, json_path, len(flags),
        )
        return json_path

    def finalize(self, json_path: Path) -> int:
        """Loads a staged match and writes it to SQL if fully reviewed.

        Args:
            json_path: Path to a pending JSON file previously written by
                ingest() (and possibly hand-edited to resolve review
                flags).

        Returns:
            The newly inserted match's match_id.

        Raises:
            UnresolvedReviewError: If any point still needs review.
            ValueError: If this match is already loaded.
        """
        record = review.load_pending(json_path)
        connection = db.get_connection(self.config.db_path, self.config.schema_path)
        try:
            match_id = load.finalize_and_load(connection, record)
        finally:
            connection.close()
        logger.info("Loaded match_id=%d (%s vs %s)", match_id, record.date, record.opponent)
        return match_id
