from __future__ import annotations

from swingvision_import.quality_check import (
    check_score_against_sets_sheet,
    check_serve_order,
    check_tracked_identity,
)
from swingvision_import.raw import RawSetRow, RawSettings
from swingvision_import.records import PointRecord, SetRecord


def _set_record(
    set_number: int, games_won: int, games_lost: int, first_is_serving: bool
) -> SetRecord:
    return SetRecord(
        set_number=set_number,
        games_won=games_won,
        games_lost=games_lost,
        points=[
            PointRecord(
                game_number=1,
                point_number=1,
                is_serving=first_is_serving,
                point_won=True,
                point_end_type="ace",
                needs_review=True,
            )
        ],
    )


def test_check_score_against_sets_sheet_matching_score_produces_no_note():
    sets = [_set_record(1, 6, 4, True)]
    raw_sets = [RawSetRow(set_number=1, winner="host", games_won=6, games_lost=4)]

    assert check_score_against_sets_sheet(sets, raw_sets) == []


def test_check_score_against_sets_sheet_mismatch_produces_a_note():
    sets = [_set_record(2, 5, 3, True)]
    raw_sets = [RawSetRow(set_number=2, winner="host", games_won=6, games_lost=4)]

    notes = check_score_against_sets_sheet(sets, raw_sets)

    assert len(notes) == 1
    assert "5-3" in notes[0]
    assert "6-4" in notes[0]


def test_check_score_against_sets_sheet_skips_sets_with_no_matching_raw_row():
    sets = [_set_record(3, 6, 0, True)]

    assert check_score_against_sets_sheet(sets, raw_sets=[]) == []


def test_check_serve_order_returns_empty_when_nothing_supplied():
    sets = [_set_record(1, 6, 4, True)]

    assert check_serve_order(sets, first_server_by_set=None) == []


def test_check_serve_order_matching_ground_truth_produces_no_note():
    sets = [_set_record(1, 6, 4, True)]

    assert check_serve_order(sets, {1: "me"}) == []


def test_check_serve_order_mismatch_produces_a_high_severity_note():
    sets = [_set_record(1, 6, 4, True)]

    notes = check_serve_order(sets, {1: "opponent"})

    assert len(notes) == 1
    assert "reversed" in notes[0]


def test_check_serve_order_skips_sets_with_no_ground_truth_supplied():
    sets = [_set_record(1, 6, 4, True), _set_record(2, 6, 3, False)]

    # Only set 1 has ground truth supplied; set 2 is silently skipped.
    assert check_serve_order(sets, {1: "me"}) == []


def test_check_tracked_identity_returns_empty_when_nothing_supplied():
    settings = RawSettings(host_name="Rishi Gupta", guest_name="Opponent")

    assert check_tracked_identity(settings, claimed_identity=None) == []
    assert check_tracked_identity(None, claimed_identity="Rishi Gupta") == []


def test_check_tracked_identity_matches_case_and_whitespace_insensitively():
    settings = RawSettings(host_name="Rishi Gupta", guest_name="Opponent")

    assert check_tracked_identity(settings, "  rishi gupta  ") == []


def test_check_tracked_identity_mismatch_produces_a_note():
    settings = RawSettings(host_name="Rishi Gupta", guest_name="Opponent")

    notes = check_tracked_identity(settings, "Someone Else")

    assert len(notes) == 1
    assert "Someone Else" in notes[0]
    assert "Rishi Gupta" in notes[0]
