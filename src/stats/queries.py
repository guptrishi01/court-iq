"""Derived-stat aggregation from data/schema.sql, per docs/stat-definitions.md.

Each stat category has a pure `*_from_points` function (easy to unit test
with hand-built PointRow lists) and the module-level `match_stats` function
that fetches from SQLite and assembles the full MatchStats bundle.
"""

from __future__ import annotations

import sqlite3

from .models import (
    ClutchStats,
    MatchStats,
    NetStats,
    PointOutcomeStats,
    PointRow,
    ReceivingStats,
    SelfAssessment,
    ServingStats,
)
from .scoring import reconstruct

_FETCH_POINTS_SQL = """
    SELECT
        s.set_number,
        p.game_number,
        p.point_number,
        p.is_serving,
        p.first_serve_in,
        p.second_serve_in,
        p.point_won,
        p.point_end_type,
        p.net_approach,
        p.net_point_won,
        p.is_tiebreak_game
    FROM point p
    JOIN "set" s ON p.set_id = s.set_id
    WHERE s.match_id = ?{set_filter}
    ORDER BY s.set_number, p.game_number, p.point_number
"""


def _pct(numerator: int, denominator: int) -> float:
    """Computes a percentage, returning 0.0 rather than dividing by zero.

    Args:
        numerator: The count meeting the condition.
        denominator: The total count.

    Returns:
        `numerator / denominator * 100`, rounded to 1 decimal place, or 0.0
        if denominator is 0.
    """
    if denominator == 0:
        return 0.0
    return round(numerator / denominator * 100, 1)


def _fetch_points(
    conn: sqlite3.Connection, match_id: int, set_id: int | None = None
) -> list[PointRow]:
    """Fetches a match's (or one set's) points, ordered for aggregation.

    Args:
        conn: An open SQLite connection.
        match_id: The match to fetch points for.
        set_id: If given, restricts to this one set (set-level scope);
            otherwise all sets in the match (match-level scope).

    Returns:
        Ordered PointRow list, ready for the *_from_points functions or
        scoring.reconstruct.
    """
    set_filter = " AND s.set_id = ?" if set_id is not None else ""
    params = (match_id, set_id) if set_id is not None else (match_id,)
    cursor = conn.execute(_FETCH_POINTS_SQL.format(set_filter=set_filter), params)
    return [
        PointRow(
            set_number=row[0],
            game_number=row[1],
            point_number=row[2],
            is_serving=bool(row[3]),
            first_serve_in=None if row[4] is None else bool(row[4]),
            second_serve_in=None if row[5] is None else bool(row[5]),
            point_won=bool(row[6]),
            point_end_type=row[7],
            net_approach=bool(row[8]),
            net_point_won=None if row[9] is None else bool(row[9]),
            is_tiebreak_game=bool(row[10]),
        )
        for row in cursor.fetchall()
    ]


def _non_tiebreak_games(points: list[PointRow]) -> list[list[PointRow]]:
    """Groups points into per-game lists, excluding tiebreak games.

    Args:
        points: Ordered point rows (see _fetch_points).

    Returns:
        One list of points per non-tiebreak game, in play order.
    """
    games: dict[tuple[int, int], list[PointRow]] = {}
    order: list[tuple[int, int]] = []
    for row in points:
        if row.is_tiebreak_game:
            continue
        key = (row.set_number, row.game_number)
        if key not in games:
            games[key] = []
            order.append(key)
        games[key].append(row)
    return [games[key] for key in order]


def serving_stats_from_points(points: list[PointRow]) -> ServingStats:
    """Computes serving stats from already-fetched point rows.

    Args:
        points: Ordered point rows for a match or a single set.

    Returns:
        The serving stats for that scope.
    """
    serve_points = [p for p in points if p.is_serving]
    first_serves_total = len(serve_points)
    first_serves_in = sum(1 for p in serve_points if p.first_serve_in)
    second_serve_points = [p for p in serve_points if p.first_serve_in is False]
    second_serves_total = len(second_serve_points)
    second_serves_in = sum(1 for p in second_serve_points if p.second_serve_in)
    aces = sum(1 for p in points if p.point_end_type == "ace")
    double_faults = sum(1 for p in points if p.point_end_type == "double_fault")

    service_games_won = 0
    service_games_total = 0
    for game in _non_tiebreak_games(points):
        if not game[0].is_serving:
            continue
        service_games_total += 1
        if game[-1].point_won:
            service_games_won += 1

    return ServingStats(
        first_serves_total=first_serves_total,
        first_serves_in=first_serves_in,
        first_serve_pct=_pct(first_serves_in, first_serves_total),
        second_serves_total=second_serves_total,
        second_serves_in=second_serves_in,
        second_serve_pct=_pct(second_serves_in, second_serves_total),
        aces=aces,
        double_faults=double_faults,
        service_games_won=service_games_won,
        service_games_total=service_games_total,
        service_hold_pct=_pct(service_games_won, service_games_total),
    )


def receiving_stats_from_points(points: list[PointRow]) -> ReceivingStats:
    """Computes receiving stats from already-fetched point rows.

    Args:
        points: Ordered point rows for a match or a single set.

    Returns:
        The receiving stats for that scope.
    """
    contexts = reconstruct(points)
    break_points_total = sum(1 for c in contexts if c.is_break_point)
    break_points_converted = sum(1 for c in contexts if c.is_break_point and c.point.point_won)

    return_games_won = 0
    return_games_total = 0
    for game in _non_tiebreak_games(points):
        if game[0].is_serving:
            continue
        return_games_total += 1
        if game[-1].point_won:
            return_games_won += 1

    return ReceivingStats(
        break_points_total=break_points_total,
        break_points_converted=break_points_converted,
        break_point_conversion_pct=_pct(break_points_converted, break_points_total),
        return_games_won=return_games_won,
        return_games_total=return_games_total,
        return_win_pct=_pct(return_games_won, return_games_total),
    )


def point_outcome_stats_from_points(points: list[PointRow]) -> PointOutcomeStats:
    """Computes point outcome stats from already-fetched point rows.

    Args:
        points: Ordered point rows for a match or a single set.

    Returns:
        The point outcome stats for that scope.
    """
    total_points_played = len(points)
    total_points_won = sum(1 for p in points if p.point_won)
    winners = sum(1 for p in points if p.point_end_type == "winner")
    unforced_errors = sum(1 for p in points if p.point_end_type == "unforced_error")
    forced_errors = sum(1 for p in points if p.point_end_type == "forced_error")
    return_winners = sum(1 for p in points if p.point_end_type == "return_winner")
    return_errors = sum(1 for p in points if p.point_end_type == "return_error")

    return PointOutcomeStats(
        total_points_played=total_points_played,
        total_points_won=total_points_won,
        points_won_pct=_pct(total_points_won, total_points_played),
        winners=winners,
        unforced_errors=unforced_errors,
        forced_errors=forced_errors,
        return_winners=return_winners,
        return_errors=return_errors,
        winner_to_ue_ratio=round(winners / unforced_errors, 2) if unforced_errors else 0.0,
    )


def net_stats_from_points(points: list[PointRow]) -> NetStats:
    """Computes net stats from already-fetched point rows.

    Args:
        points: Ordered point rows for a match or a single set.

    Returns:
        The net stats for that scope.
    """
    net_approaches = sum(1 for p in points if p.net_approach)
    net_points_won = sum(1 for p in points if p.net_approach and p.net_point_won)
    return NetStats(
        net_approaches=net_approaches,
        net_points_won=net_points_won,
        net_success_pct=_pct(net_points_won, net_approaches),
    )


def clutch_stats_from_points(points: list[PointRow]) -> ClutchStats:
    """Computes clutch stats from already-fetched point rows.

    Args:
        points: Ordered point rows for a match or a single set.

    Returns:
        The clutch stats for that scope.
    """
    contexts = reconstruct(points)
    deuce_points_played = sum(1 for c in contexts if c.is_deuce_point)
    deuces_converted = sum(1 for c in contexts if c.is_deuce_point and c.point.point_won)
    return ClutchStats(
        deuce_points_played=deuce_points_played,
        deuces_converted=deuces_converted,
        deuce_conversion_pct=_pct(deuces_converted, deuce_points_played),
    )


def match_stats(conn: sqlite3.Connection, match_id: int, set_id: int | None = None) -> MatchStats:
    """Assembles the full derived-stats bundle for a match or one of its sets.

    Args:
        conn: An open SQLite connection.
        match_id: The match to aggregate.
        set_id: If given, scopes every stat to this one set; otherwise
            aggregates across the whole match.

    Returns:
        The full MatchStats bundle.

    Raises:
        ValueError: If no match with this match_id exists.
    """
    row = conn.execute(
        "SELECT date, opponent, result, energy_rating, mental_rating, pros, cons "
        "FROM match WHERE match_id = ?",
        (match_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"No match with match_id={match_id}")
    date, opponent, result, energy_rating, mental_rating, pros, cons = row

    points = _fetch_points(conn, match_id, set_id)

    return MatchStats(
        match_id=match_id,
        date=date,
        opponent=opponent,
        result=result,
        serving=serving_stats_from_points(points),
        receiving=receiving_stats_from_points(points),
        point_outcomes=point_outcome_stats_from_points(points),
        net=net_stats_from_points(points),
        clutch=clutch_stats_from_points(points),
        self_assessment=SelfAssessment(
            energy_rating=energy_rating,
            mental_rating=mental_rating,
            pros=pros,
            cons=cons,
        ),
    )
