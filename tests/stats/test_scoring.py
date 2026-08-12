from __future__ import annotations

from stats.models import PointRow
from stats.scoring import reconstruct


def _point(
    game_number: int,
    point_number: int,
    is_serving: bool,
    point_won: bool,
    *,
    set_number: int = 1,
    is_tiebreak_game: bool = False,
) -> PointRow:
    return PointRow(
        set_number=set_number,
        game_number=game_number,
        point_number=point_number,
        is_serving=is_serving,
        first_serve_in=True,
        second_serve_in=None,
        point_won=point_won,
        point_end_type="winner" if point_won else "unforced_error",
        net_approach=False,
        net_point_won=None,
        is_tiebreak_game=is_tiebreak_game,
    )


def test_deuce_point_flagged_only_at_the_tied_three_all_score():
    # Player serving: 0-0,1-0,1-1,2-1,2-2,3-2,3-3(deuce),4-3(ad, not deuce)
    won_sequence = [True, False, True, False, True, False, True, True]
    points = [_point(1, i + 1, True, won) for i, won in enumerate(won_sequence)]

    contexts = reconstruct(points)

    deuce_flags = [c.is_deuce_point for c in contexts]
    assert deuce_flags == [False, False, False, False, False, False, True, False]


def test_no_break_points_possible_while_serving():
    won_sequence = [True, True, True, True]
    points = [_point(1, i + 1, True, won) for i, won in enumerate(won_sequence)]

    contexts = reconstruct(points)

    assert all(not c.is_break_point for c in contexts)


def test_break_point_earned_and_converted_while_receiving():
    # Receiving: 1-0,2-0,3-0(BP),4-0 win
    won_sequence = [True, True, True, True]
    points = [_point(1, i + 1, False, won) for i, won in enumerate(won_sequence)]

    contexts = reconstruct(points)

    break_flags = [c.is_break_point for c in contexts]
    assert break_flags == [False, False, False, True]
    converted = [c for c in contexts if c.is_break_point and c.point.point_won]
    assert len(converted) == 1


def test_break_points_saved_then_score_reaches_deuce():
    # Receiving. Score progression (player-opponent before each point):
    # 0-0, 1-0, 2-0, 3-0(BP#1, lost), 3-1(BP#2, lost), 3-2(BP#3, lost), 3-3(deuce)
    won_sequence = [True, True, True, False, False, False]
    points = [_point(1, i + 1, False, won) for i, won in enumerate(won_sequence)]

    contexts = reconstruct(points)

    break_flags = [c.is_break_point for c in contexts]
    assert break_flags == [False, False, False, True, True, True]
    assert all(not c.point.point_won for c in contexts if c.is_break_point)

    # One more point brings the score to 3-3, which is a deuce point.
    points.append(_point(1, 7, False, True))
    contexts = reconstruct(points)
    assert contexts[-1].is_deuce_point is True
    assert contexts[-1].is_break_point is False


def test_tiebreak_games_never_flagged_regardless_of_score():
    # Same 3-0-while-receiving shape that would be a break point in a normal
    # game, but marked as a tiebreak game.
    won_sequence = [True, True, True, True]
    points = [
        _point(1, i + 1, False, won, is_tiebreak_game=True) for i, won in enumerate(won_sequence)
    ]

    contexts = reconstruct(points)

    assert all(not c.is_break_point and not c.is_deuce_point for c in contexts)


def test_tally_resets_between_games_and_sets():
    # Game 1 ends at a deuce-tally point (3-3); game 2 starts fresh and its
    # first point must not inherit game 1's tally.
    won_sequence = [True, False, True, False, True, False]
    game_one = [_point(1, i + 1, True, won) for i, won in enumerate(won_sequence)]
    game_two = [_point(2, 1, True, True)]
    set_two_game_one = [_point(1, 1, True, True, set_number=2)]

    contexts = reconstruct(game_one + game_two + set_two_game_one)

    assert contexts[-2].is_deuce_point is False  # first point of game 2
    assert contexts[-1].is_deuce_point is False  # first point of set 2, game 1
