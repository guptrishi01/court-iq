"""Atomically writes a fully-reviewed MatchRecord into match/set/point.

This is where the user's core requirement is enforced in code: a match with
any unresolved review flag is rejected outright, and a match is written as
one all-or-nothing transaction, never partially.
"""

from __future__ import annotations

import sqlite3

from .records import MatchRecord
from .review import unresolved_flags


class UnresolvedReviewError(ValueError):
    """Raised when a match still has unconfirmed SwingVision review flags.

    Attributes:
        flags: Human-readable descriptions of each unresolved point, as
            returned by review.unresolved_flags.
    """

    def __init__(self, flags: list[str]) -> None:
        """Initializes the error.

        Args:
            flags: Descriptions of each unresolved point.
        """
        super().__init__(
            "Match has unresolved review flags and cannot be loaded:\n" + "\n".join(flags)
        )
        self.flags = flags


def _already_loaded(cursor: sqlite3.Cursor, record: MatchRecord) -> bool:
    """Checks whether a match with this date/opponent is already loaded.

    Args:
        cursor: An open cursor on the target database.
        record: The match to check for.

    Returns:
        True if a match row with the same date and opponent already exists.
    """
    cursor.execute(
        "SELECT 1 FROM match WHERE date = ? AND opponent = ? LIMIT 1",
        (record.date, record.opponent),
    )
    return cursor.fetchone() is not None


def finalize_and_load(connection: sqlite3.Connection, record: MatchRecord) -> int:
    """Writes a fully-reviewed match into match/set/point as one transaction.

    Refuses to write anything — not even a partial match — if any point
    still has an unresolved review flag, or if this match is already
    loaded.

    Args:
        connection: An open SQLite connection with the schema applied.
        record: The match to load. Every point's needs_review must be
            False.

    Returns:
        The newly inserted match's match_id.

    Raises:
        UnresolvedReviewError: If any point still has needs_review=True.
        ValueError: If a match with the same date and opponent is already
            loaded.
        sqlite3.IntegrityError: If a value violates the schema's
            constraints (e.g. an invalid point_end_type); the whole
            transaction is rolled back first.
    """
    flags = unresolved_flags(record)
    if flags:
        raise UnresolvedReviewError(flags)

    cursor = connection.cursor()
    if _already_loaded(cursor, record):
        raise ValueError(f"Match on {record.date} vs {record.opponent} is already loaded.")

    try:
        cursor.execute(
            """
            INSERT INTO match (date, opponent, result, match_type, location,
                                energy_rating, mental_rating, pros, cons, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.date,
                record.opponent,
                record.result,
                record.match_type,
                record.location,
                record.energy_rating,
                record.mental_rating,
                record.pros,
                record.cons,
                record.notes,
            ),
        )
        match_id = cursor.lastrowid

        for set_record in record.sets:
            cursor.execute(
                """
                INSERT INTO "set" (match_id, set_number, games_won, games_lost, is_tiebreak_set)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    match_id,
                    set_record.set_number,
                    set_record.games_won,
                    set_record.games_lost,
                    set_record.is_tiebreak_set,
                ),
            )
            set_id = cursor.lastrowid

            for point in set_record.points:
                cursor.execute(
                    """
                    INSERT INTO point (set_id, game_number, point_number, is_serving,
                                        first_serve_in, second_serve_in, point_won,
                                        point_end_type, net_approach,
                                        is_tiebreak_game, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        set_id,
                        point.game_number,
                        point.point_number,
                        point.is_serving,
                        point.first_serve_in,
                        point.second_serve_in,
                        point.point_won,
                        point.point_end_type,
                        point.net_approach,
                        point.is_tiebreak_game,
                        point.notes,
                    ),
                )
    except Exception:
        connection.rollback()
        raise
    else:
        connection.commit()
        return match_id
