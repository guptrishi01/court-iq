from __future__ import annotations

import sqlite3

import pytest

from swingvision_import.load import UnresolvedReviewError
from swingvision_import.pipeline import SwingVisionImportPipeline
from swingvision_import.review import load_pending, save_pending


def _clear_review_flags(pipeline, json_path):
    record = load_pending(json_path)
    for set_record in record.sets:
        for point in set_record.points:
            point.needs_review = False
    save_pending(record, pipeline.config.pending_dir)


def test_ingest_writes_pending_json_without_touching_sql(synthetic_xlsx, import_config):
    pipeline = SwingVisionImportPipeline(import_config)
    json_path = pipeline.ingest(synthetic_xlsx, date="2026-08-06", opponent="Alex", result="W")

    assert json_path.exists()
    assert not import_config.db_path.exists()


def test_finalize_rejects_until_flags_resolved(synthetic_xlsx, import_config):
    pipeline = SwingVisionImportPipeline(import_config)
    json_path = pipeline.ingest(synthetic_xlsx, date="2026-08-06", opponent="Alex", result="W")

    with pytest.raises(UnresolvedReviewError):
        pipeline.finalize(json_path)


def test_finalize_loads_once_flags_are_cleared(synthetic_xlsx, import_config):
    pipeline = SwingVisionImportPipeline(import_config)
    json_path = pipeline.ingest(synthetic_xlsx, date="2026-08-06", opponent="Alex", result="W")
    _clear_review_flags(pipeline, json_path)

    match_id = pipeline.finalize(json_path)
    assert match_id == 1


def test_rerunning_finalize_on_same_match_is_rejected_not_duplicated(synthetic_xlsx, import_config):
    pipeline = SwingVisionImportPipeline(import_config)
    json_path = pipeline.ingest(synthetic_xlsx, date="2026-08-06", opponent="Alex", result="W")
    _clear_review_flags(pipeline, json_path)

    pipeline.finalize(json_path)
    with pytest.raises(ValueError):
        pipeline.finalize(json_path)


def test_match_overrides_survive_the_full_ingest_then_finalize_round_trip(
    synthetic_xlsx, import_config
):
    pipeline = SwingVisionImportPipeline(import_config)
    json_path = pipeline.ingest(
        synthetic_xlsx,
        date="2026-08-06",
        opponent="Alex",
        result="W",
        energy_rating=5,
        pros="Aggressive on return games",
    )
    _clear_review_flags(pipeline, json_path)
    pipeline.finalize(json_path)

    connection = sqlite3.connect(import_config.db_path)
    row = connection.execute("SELECT energy_rating, pros FROM match").fetchone()
    connection.close()
    assert row == (5, "Aggressive on return games")


def test_reingesting_the_same_match_overwrites_the_pending_file_at_the_same_path(
    synthetic_xlsx, import_config
):
    pipeline = SwingVisionImportPipeline(import_config)
    first_path = pipeline.ingest(synthetic_xlsx, date="2026-08-06", opponent="Alex", result="W")
    second_path = pipeline.ingest(
        synthetic_xlsx, date="2026-08-06", opponent="Alex", result="W", pros="Revised notes"
    )

    assert first_path == second_path
    assert list(import_config.pending_dir.glob("*.json")) == [first_path]
