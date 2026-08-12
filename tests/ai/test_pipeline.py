from __future__ import annotations

import sqlite3
from pathlib import Path

from ai.config import AICoachConfig
from ai.pipeline import AICoachPipeline
from swingvision_import.load import finalize_and_load
from swingvision_import.records import MatchRecord, PointRecord, SetRecord
from tests.ai.conftest import FakeAnthropicClient

_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "data" / "schema.sql"


def _seed_match(tmp_path: Path) -> tuple[sqlite3.Connection, int]:
    connection = sqlite3.connect(tmp_path / "test.db")
    connection.executescript(_SCHEMA_PATH.read_text(encoding="utf-8"))
    record = MatchRecord(
        date="2026-08-06",
        opponent="Alex",
        result="W",
        energy_rating=4,
        mental_rating=3,
        pros="Served big",
        cons="Slow starts",
        sets=[
            SetRecord(
                set_number=1,
                games_won=6,
                games_lost=4,
                points=[
                    PointRecord(1, 1, True, True, "ace"),
                    PointRecord(1, 2, False, True, "return_winner"),
                ],
            ),
        ],
    )
    match_id = finalize_and_load(connection, record)
    return connection, match_id


def test_generate_calls_the_api_and_saves_a_report(tmp_path):
    connection, match_id = _seed_match(tmp_path)
    client = FakeAnthropicClient()
    pipeline = AICoachPipeline(config=AICoachConfig(reports_dir=tmp_path / "reports"))

    report = pipeline.generate(connection, client, match_id)

    assert report.match_id == match_id
    assert len(client.messages.calls) == 3
    assert (tmp_path / "reports" / f"{match_id}.json").exists()


def test_generate_skips_the_api_when_a_report_already_exists(tmp_path):
    connection, match_id = _seed_match(tmp_path)
    client = FakeAnthropicClient()
    pipeline = AICoachPipeline(config=AICoachConfig(reports_dir=tmp_path / "reports"))

    pipeline.generate(connection, client, match_id)
    calls_after_first = len(client.messages.calls)
    pipeline.generate(connection, client, match_id)

    assert len(client.messages.calls) == calls_after_first


def test_generate_force_true_regenerates_and_overwrites(tmp_path):
    connection, match_id = _seed_match(tmp_path)
    client = FakeAnthropicClient()
    pipeline = AICoachPipeline(config=AICoachConfig(reports_dir=tmp_path / "reports"))

    pipeline.generate(connection, client, match_id)
    calls_after_first = len(client.messages.calls)
    pipeline.generate(connection, client, match_id, force=True)

    assert len(client.messages.calls) == calls_after_first + 3


def test_generate_loaded_from_cache_matches_the_originally_generated_report(tmp_path):
    connection, match_id = _seed_match(tmp_path)
    client = FakeAnthropicClient()
    pipeline = AICoachPipeline(config=AICoachConfig(reports_dir=tmp_path / "reports"))

    first = pipeline.generate(connection, client, match_id)
    second = pipeline.generate(connection, client, match_id)

    assert first == second
