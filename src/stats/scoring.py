"""Game-score reconstruction: derives break-point and deuce-point status.

Neither is a stored column — both are properties of a point's position within
its game's score, which only exists implicitly in the ordering of rows. This
replays each game's points in order, keeping a running point tally, rather
than modeling 0/15/30/40 labels directly; the tally is equivalent and simpler
to reason about.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import PointRow


@dataclass(frozen=True)
class PointContext:
    """A point annotated with the game-score context it was played at.

    Attributes:
        point: The underlying point row.
        is_break_point: True if, at this point, the tracked player was
            receiving and one point from winning the game. Always False for
            tiebreak games (see module docstring).
        is_deuce_point: True if, at this point, the game score was tied at
            40-40 (three points each) or later. Always False for tiebreak
            games.
    """

    point: PointRow
    is_break_point: bool
    is_deuce_point: bool


def reconstruct(points: list[PointRow]) -> list[PointContext]:
    """Annotates each point with its break-point/deuce-point status.

    Tiebreak games are excluded from both: a tiebreak's server rotates
    within the game itself (not a single server for the whole game, unlike a
    standard game), and "break point" doesn't map onto that scoring the same
    way — so both flags are False for any point with is_tiebreak_game=True.

    Args:
        points: Point rows for one match or set, already ordered by
            (set_number, game_number, point_number) — as returned by
            queries._fetch_points.

    Returns:
        One PointContext per input point, in the same order.
    """
    contexts = []
    player_points = 0
    opponent_points = 0
    current_game_is_serving = False
    current_key: tuple[int, int] | None = None

    for row in points:
        key = (row.set_number, row.game_number)
        if key != current_key:
            player_points = 0
            opponent_points = 0
            current_game_is_serving = row.is_serving
            current_key = key

        if row.is_tiebreak_game:
            is_break_point = False
            is_deuce_point = False
        else:
            is_deuce_point = player_points >= 3 and player_points == opponent_points
            is_break_point = (
                not current_game_is_serving
                and player_points >= 3
                and player_points - opponent_points >= 1
            )

        contexts.append(
            PointContext(point=row, is_break_point=is_break_point, is_deuce_point=is_deuce_point)
        )

        if row.point_won:
            player_points += 1
        else:
            opponent_points += 1

    return contexts
