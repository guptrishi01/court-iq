"""Orchestrates the SwingVision import flow: ingest, optional AI-assisted
review suggestions, then finalize.

ingest() never touches SQL — it only stages a reviewable JSON file, routing
through either the direct Points-sheet parse (transform.py, when a Pro
export has real Points rows) or the Shots-based reconstruction fallback
(reconstruct.py, confirmed the actual path for two real non-Pro exports).
suggest() is a separate, explicit, opt-in step — it spends real API money,
so it never runs automatically inside ingest(). finalize() is the only path
into the database, and delegates the review-flag gate to
load.finalize_and_load; suggestions never bypass that gate.
"""

from __future__ import annotations

import logging
from pathlib import Path

from ai.client import AnthropicClientLike

from . import db, load, reconstruct, review, review_assist
from .config import ImportConfig
from .parse import SwingVisionParser
from .records import MatchRecord
from .review_assist import SuggestionConfig
from .transform import transform

logger = logging.getLogger(__name__)


class SwingVisionImportPipeline:
    """Orchestrates the SwingVision import flow.

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

        Raises:
            ValueError: If the Points sheet is empty (no Pro rollup) and
                there's also no Settings sheet to identify the tracked
                player for Shots-based reconstruction.
        """
        raw = self._parser.parse(xlsx_path)

        if raw.points:
            record = transform(
                raw,
                date=date,
                opponent=opponent,
                result=result,
                config=self.config,
                source_file=str(xlsx_path),
                **match_overrides,
            )
        else:
            if raw.settings is None:
                raise ValueError(
                    f"{xlsx_path}: Points sheet is empty (no Pro rollup) and no "
                    "Settings sheet was found to identify the tracked player for "
                    "Shots-based reconstruction."
                )
            logger.info(
                "Points sheet is empty for %s — reconstructing from Shots instead "
                "(SwingVision's point rollup needs Pro; shot tracking doesn't).",
                xlsx_path,
            )
            sets, skipped = reconstruct.reconstruct_all(raw.shots, raw.settings.host_name)
            if skipped:
                logger.warning(
                    "%d point(s) skipped during reconstruction (no shot data): %s",
                    len(skipped),
                    skipped,
                )
            record = MatchRecord(
                date=date,
                opponent=opponent,
                result=result,
                source_file=str(xlsx_path),
                sets=sets,
                **match_overrides,
            )

        json_path = review.save_pending(record, self.config.pending_dir)
        flags = review.unresolved_flags(record)
        logger.info(
            "Staged %s vs %s at %s (%d point(s) need review)",
            date, opponent, json_path, len(flags),
        )
        return json_path

    def suggest(
        self,
        client: AnthropicClientLike,
        json_path: Path,
        *,
        suggestion_config: SuggestionConfig | None = None,
    ) -> MatchRecord:
        """Generates Claude-assisted suggestions for a staged match's flagged points.

        Opt-in and separate from ingest()/finalize() on purpose — this
        spends real API money, so it never runs automatically. Only
        applies to points that came from Shots-based reconstruction
        (source_point_number is not None); a direct Points-sheet parse has
        no raw shot sequence to re-fetch and reason over. Never clears
        needs_review — the user still confirms every point by hand.

        Args:
            client: An anthropic.Anthropic-shaped client (injected so
                tests never hit the real API or spend real money).
            json_path: Path to a pending JSON file previously written by
                ingest().
            suggestion_config: Model/token settings. Defaults
                to SuggestionConfig() if not given.

        Returns:
            The record with ai_suggested_point_end_type/
            ai_suggestion_reasoning filled in where a suggestion succeeded.
            Also re-saved to the same pending JSON path so the suggestions
            persist across the actual manual review.

        Raises:
            ValueError: If the staged record has no source_file to
                re-parse for shot context.
        """
        record = review.load_pending(json_path)
        if record.source_file is None:
            raise ValueError(f"{json_path}: record has no source_file to re-parse.")

        suggestion_config = suggestion_config or SuggestionConfig()
        raw = self._parser.parse(Path(record.source_file))
        shots_by_point = reconstruct.group_shots_by_point(raw.shots)

        suggested_count = 0
        for set_record in record.sets:
            for point in set_record.points:
                if point.source_point_number is None:
                    continue
                shot_context = shots_by_point.get(point.source_point_number, [])
                try:
                    suggestion = review_assist.suggest_point_resolution(
                        client, suggestion_config, point, shot_context
                    )
                except review_assist.SuggestionError:
                    logger.exception(
                        "Suggestion failed for set %d game %d point %d",
                        set_record.set_number,
                        point.game_number,
                        point.point_number,
                    )
                    continue
                point.ai_suggested_point_end_type = suggestion.point_end_type
                point.ai_suggestion_reasoning = suggestion.reasoning
                suggested_count += 1

        review.save_pending(record, self.config.pending_dir)
        logger.info("Generated %d suggestion(s) for %s", suggested_count, json_path)
        return record

    def finalize(self, json_path: Path) -> int:
        """Loads a staged match and writes it to SQL if fully reviewed.

        Args:
            json_path: Path to a pending JSON file previously written by
                ingest() (and possibly hand-edited, or annotated by
                suggest(), to resolve review flags).

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
