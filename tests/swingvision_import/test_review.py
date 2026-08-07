from __future__ import annotations

from pathlib import Path

from swingvision_import.records import MatchRecord, PointRecord, SetRecord
from swingvision_import.review import load_pending, save_pending, unresolved_flags


def _sample_record(needs_review: bool) -> MatchRecord:
    point = PointRecord(
        game_number=1,
        point_number=1,
        is_serving=True,
        point_won=True,
        point_end_type="winner",
        needs_review=needs_review,
    )
    return MatchRecord(
        date="2026-08-06",
        opponent="Alex",
        result="W",
        sets=[SetRecord(set_number=1, games_won=6, games_lost=4, points=[point])],
    )


def test_unresolved_flags_reports_pending_points():
    flags = unresolved_flags(_sample_record(needs_review=True))
    assert len(flags) == 1
    assert "point 1" in flags[0]


def test_unresolved_flags_empty_once_confirmed():
    assert unresolved_flags(_sample_record(needs_review=False)) == []


def test_json_round_trip(tmp_path: Path):
    record = _sample_record(needs_review=False)
    path = save_pending(record, tmp_path)
    assert load_pending(path) == record


def test_unresolved_flags_reports_every_flagged_point_across_multiple_sets():
    flagged_a = PointRecord(1, 1, True, True, "winner", needs_review=True)
    clean = PointRecord(1, 2, True, True, "ace", needs_review=False)
    flagged_b = PointRecord(2, 1, False, False, "unforced_error", needs_review=True)
    record = MatchRecord(
        date="2026-08-06",
        opponent="Alex",
        result="W",
        sets=[
            SetRecord(set_number=1, games_won=6, games_lost=4, points=[flagged_a, clean]),
            SetRecord(set_number=2, games_won=6, games_lost=3, points=[flagged_b]),
        ],
    )

    flags = unresolved_flags(record)

    assert len(flags) == 2
    assert any("set 1" in f and "point 1" in f for f in flags)
    assert any("set 2" in f and "point 1" in f for f in flags)


def test_save_pending_sanitizes_filesystem_unsafe_characters_in_opponent_name(tmp_path: Path):
    record = _sample_record(needs_review=False)
    record.opponent = 'Team A/B: "The Rematch"?'

    path = save_pending(record, tmp_path)

    assert path.exists()
    assert path.parent == tmp_path
    for unsafe_char in '<>:"/\\|?*':
        assert unsafe_char not in path.name
    assert load_pending(path).opponent == record.opponent


def test_save_pending_falls_back_to_a_placeholder_for_an_all_unsafe_opponent_name(tmp_path: Path):
    record = _sample_record(needs_review=False)
    record.opponent = "///"

    path = save_pending(record, tmp_path)

    assert path.exists()
    assert "unknown" in path.name


def test_save_pending_twice_overwrites_the_same_file_rather_than_duplicating(tmp_path: Path):
    record = _sample_record(needs_review=False)
    first_path = save_pending(record, tmp_path)

    record.pros = "Updated after re-review"
    second_path = save_pending(record, tmp_path)

    assert first_path == second_path
    assert list(tmp_path.glob("*.json")) == [first_path]
    assert load_pending(second_path).pros == "Updated after re-review"
