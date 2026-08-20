from __future__ import annotations

from pathlib import Path

import pytest

from swingvision_import.config import ImportConfig
from swingvision_import.parse import SwingVisionParser
from swingvision_import.raw import RawMatchExport, RawPointRow, RawSetRow
from swingvision_import.records import MatchRecord
from swingvision_import.transform import transform


def _record(synthetic_xlsx: Path) -> MatchRecord:
    config = ImportConfig()
    raw = SwingVisionParser(config).parse(synthetic_xlsx)
    return transform(raw, date="2026-08-06", opponent="Alex", result="W", config=config)


def test_ace_is_not_flagged_but_unforced_error_is(synthetic_xlsx):
    points = _record(synthetic_xlsx).sets[0].points

    ace_point = next(p for p in points if p.point_end_type == "ace")
    assert ace_point.needs_review is False

    ue_point = next(p for p in points if p.point_end_type == "unforced_error")
    assert ue_point.needs_review is True


def test_net_fields_default_to_manual_fill_in(synthetic_xlsx):
    for point in _record(synthetic_xlsx).sets[0].points:
        assert point.net_approach is False


def test_points_are_ordered_within_each_set(synthetic_xlsx):
    ordering = [(p.game_number, p.point_number) for p in _record(synthetic_xlsx).sets[0].points]
    assert ordering == sorted(ordering)


def test_unrecognized_end_type_raises_instead_of_silently_mapping():
    raw = RawMatchExport(
        sets=[RawSetRow(set_number=1, winner="host", games_won=6, games_lost=4)],
        points=[
            RawPointRow(
                set_number=1,
                game_number=1,
                point_number=1,
                server="host",
                winner="host",
                end_type="let",
            )
        ],
    )
    with pytest.raises(ValueError, match="let"):
        transform(raw, date="2026-08-06", opponent="Alex", result="W", config=ImportConfig())


def test_points_are_grouped_into_the_correct_set_not_flattened():
    raw = RawMatchExport(
        sets=[
            RawSetRow(set_number=1, winner="host", games_won=6, games_lost=4),
            RawSetRow(set_number=2, winner="guest", games_won=3, games_lost=6),
        ],
        points=[
            RawPointRow(1, 1, 1, "host", "host", "ace"),
            RawPointRow(1, 1, 2, "host", "host", "winner"),
            RawPointRow(2, 1, 1, "guest", "guest", "double_fault"),
        ],
    )
    record = transform(raw, date="2026-08-06", opponent="Alex", result="L", config=ImportConfig())

    assert len(record.sets) == 2
    assert [p.point_end_type for p in record.sets[0].points] == ["ace", "winner"]
    assert [p.point_end_type for p in record.sets[1].points] == ["double_fault"]
    # A double fault is a clear-cut serve outcome, not one of the ambiguous
    # AI-guessed categories, so it should not require manual review.
    assert record.sets[1].points[0].needs_review is False


def test_set_with_zero_points_is_kept_not_dropped():
    raw = RawMatchExport(
        sets=[RawSetRow(set_number=1, winner="host", games_won=6, games_lost=0)],
        points=[],
    )
    record = transform(raw, date="2026-08-06", opponent="Alex", result="W", config=ImportConfig())

    assert len(record.sets) == 1
    assert record.sets[0].points == []


def test_server_and_winner_matching_is_case_and_whitespace_insensitive():
    raw = RawMatchExport(
        sets=[RawSetRow(set_number=1, winner="host", games_won=6, games_lost=4)],
        points=[RawPointRow(1, 1, 1, "  Host ", "HOST", "ace")],
    )
    record = transform(raw, date="2026-08-06", opponent="Alex", result="W", config=ImportConfig())

    point = record.sets[0].points[0]
    assert point.is_serving is True
    assert point.point_won is True


def test_match_overrides_are_passed_through_to_the_record():
    raw = RawMatchExport(sets=[RawSetRow(set_number=1, winner="host", games_won=6, games_lost=4)])
    record = transform(
        raw,
        date="2026-08-06",
        opponent="Alex",
        result="W",
        config=ImportConfig(),
        energy_rating=4,
        mental_rating=5,
        pros="Served big on break points",
        cons="Too many unforced errors off the backhand",
        location="Club Court 3",
    )

    assert record.energy_rating == 4
    assert record.mental_rating == 5
    assert record.pros == "Served big on break points"
    assert record.cons == "Too many unforced errors off the backhand"
    assert record.location == "Club Court 3"
