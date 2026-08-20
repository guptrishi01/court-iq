from __future__ import annotations

import sqlite3
from pathlib import Path

from ai.config import AICoachConfig
from ai.pipeline import AICoachPipeline
from swingvision_import.load import finalize_and_load
from swingvision_import.records import MatchRecord, PointRecord, SetRecord
from swingvision_import.review import save_pending
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


def test_generate_folds_in_shot_pattern_summary_from_the_matching_pending_json(tmp_path):
    connection, match_id = _seed_match(tmp_path)
    pending_dir = tmp_path / "pending"
    save_pending(
        MatchRecord(
            date="2026-08-06",
            opponent="Alex",
            result="W",
            shot_pattern_summary={"avg_rally_length": 4.75},
        ),
        pending_dir,
    )
    client = FakeAnthropicClient()
    pipeline = AICoachPipeline(
        config=AICoachConfig(reports_dir=tmp_path / "reports", pending_dir=pending_dir)
    )

    pipeline.generate(connection, client, match_id)

    assert all("avg_rally_length" in call["system"] for call in client.messages.calls)


def test_generate_degrades_cleanly_when_the_matching_pending_json_is_corrupt(tmp_path):
    connection, match_id = _seed_match(tmp_path)
    pending_dir = tmp_path / "pending"
    pending_dir.mkdir(parents=True)
    (pending_dir / "2026-08-06_Alex.json").write_text("not valid json", encoding="utf-8")
    client = FakeAnthropicClient()
    pipeline = AICoachPipeline(
        config=AICoachConfig(reports_dir=tmp_path / "reports", pending_dir=pending_dir)
    )

    report = pipeline.generate(connection, client, match_id)

    assert report.match_id == match_id
    assert all("avg_rally_length" not in call["system"] for call in client.messages.calls)


def test_generate_degrades_cleanly_when_no_pending_json_matches(tmp_path):
    connection, match_id = _seed_match(tmp_path)
    client = FakeAnthropicClient()
    pipeline = AICoachPipeline(
        config=AICoachConfig(reports_dir=tmp_path / "reports", pending_dir=tmp_path / "pending")
    )

    report = pipeline.generate(connection, client, match_id)

    assert report.match_id == match_id
    assert all("avg_rally_length" not in call["system"] for call in client.messages.calls)
