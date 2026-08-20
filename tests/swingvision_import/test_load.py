from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from swingvision_import.load import UnresolvedReviewError, finalize_and_load
from swingvision_import.records import MatchRecord, PointRecord, SetRecord

_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "data" / "schema.sql"


def _connection(tmp_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(tmp_path / "test.db")
    connection.executescript(_SCHEMA_PATH.read_text(encoding="utf-8"))
    return connection


def _record(needs_review: bool) -> MatchRecord:
    point = PointRecord(
        game_number=1,
        point_number=1,
        is_serving=True,
        point_won=True,
        point_end_type="ace",
        needs_review=needs_review,
    )
    return MatchRecord(
        date="2026-08-06",
        opponent="Alex",
        result="W",
        sets=[SetRecord(set_number=1, games_won=6, games_lost=4, points=[point])],
    )


def test_finalize_rejects_unresolved_review_flags(tmp_path):
    connection = _connection(tmp_path)
    with pytest.raises(UnresolvedReviewError):
        finalize_and_load(connection, _record(needs_review=True))
    assert connection.execute("SELECT COUNT(*) FROM match").fetchone()[0] == 0


def test_finalize_writes_match_set_and_points_atomically(tmp_path):
    connection = _connection(tmp_path)
    match_id = finalize_and_load(connection, _record(needs_review=False))

    assert connection.execute("SELECT COUNT(*) FROM match").fetchone()[0] == 1
    point_count = connection.execute(
        'SELECT COUNT(*) FROM point p JOIN "set" s ON p.set_id = s.set_id WHERE s.match_id = ?',
        (match_id,),
    ).fetchone()[0]
    assert point_count == 1


def test_finalize_refuses_duplicate_match(tmp_path):
    connection = _connection(tmp_path)
    finalize_and_load(connection, _record(needs_review=False))

    with pytest.raises(ValueError) as exc_info:
        finalize_and_load(connection, _record(needs_review=False))

    assert "already loaded" in str(exc_info.value)
    assert connection.execute("SELECT COUNT(*) FROM match").fetchone()[0] == 1


def test_dedupe_does_not_false_positive_on_a_different_date_or_opponent(tmp_path):
    connection = _connection(tmp_path)
    finalize_and_load(connection, _record(needs_review=False))

    same_opponent_different_date = _record(needs_review=False)
    same_opponent_different_date.date = "2026-08-13"
    finalize_and_load(connection, same_opponent_different_date)

    same_date_different_opponent = _record(needs_review=False)
    same_date_different_opponent.opponent = "Jordan"
    finalize_and_load(connection, same_date_different_opponent)

    assert connection.execute("SELECT COUNT(*) FROM match").fetchone()[0] == 3


def test_finalize_writes_all_sets_and_points_for_a_multi_set_match(tmp_path):
    connection = _connection(tmp_path)
    record = MatchRecord(
        date="2026-08-06",
        opponent="Alex",
        result="W",
        sets=[
            SetRecord(
                set_number=1,
                games_won=6,
                games_lost=4,
                points=[
                    PointRecord(1, 1, True, True, "ace"),
                    PointRecord(1, 2, True, False, "double_fault"),
                ],
            ),
            SetRecord(
                set_number=2,
                games_won=6,
                games_lost=2,
                points=[PointRecord(1, 1, False, False, "forced_error")],
            ),
        ],
    )

    match_id = finalize_and_load(connection, record)

    set_count = connection.execute(
        'SELECT COUNT(*) FROM "set" WHERE match_id = ?', (match_id,)
    ).fetchone()[0]
    point_count = connection.execute(
        'SELECT COUNT(*) FROM point p JOIN "set" s ON p.set_id = s.set_id WHERE s.match_id = ?',
        (match_id,),
    ).fetchone()[0]
    assert set_count == 2
    assert point_count == 3


def test_finalize_preserves_match_level_field_values(tmp_path):
    connection = _connection(tmp_path)
    record = _record(needs_review=False)
    record.pros = "Strong first serve"
    record.cons = "Slow second-serve recovery"
    record.energy_rating = 4
    record.mental_rating = 3
    record.location = "Club Court 3"

    match_id = finalize_and_load(connection, record)

    row = connection.execute(
        "SELECT pros, cons, energy_rating, mental_rating, location "
        "FROM match WHERE match_id = ?",
        (match_id,),
    ).fetchone()
    assert row == ("Strong first serve", "Slow second-serve recovery", 4, 3, "Club Court 3")


def test_finalize_rolls_back_the_entire_match_on_a_constraint_violation(tmp_path):
    """A point_end_type outside the schema's CHECK constraint slips past the
    needs_review gate (it's a structural/data-integrity problem, not a
    reviewer-confidence one) and must fail atomically: nothing from this
    match - not even the sets that were valid - should land in the database."""
    connection = _connection(tmp_path)
    record = MatchRecord(
        date="2026-08-06",
        opponent="Alex",
        result="W",
        sets=[
            SetRecord(
                set_number=1,
                games_won=6,
                games_lost=4,
                points=[PointRecord(1, 1, True, True, "ace")],
            ),
            SetRecord(
                set_number=2,
                games_won=6,
                games_lost=2,
                # Not a value the "set"/point CHECK constraint allows.
                points=[PointRecord(1, 1, False, False, "let")],
            ),
        ],
    )

    with pytest.raises(sqlite3.IntegrityError):
        finalize_and_load(connection, record)

    assert connection.execute("SELECT COUNT(*) FROM match").fetchone()[0] == 0
    assert connection.execute('SELECT COUNT(*) FROM "set"').fetchone()[0] == 0
    assert connection.execute("SELECT COUNT(*) FROM point").fetchone()[0] == 0
