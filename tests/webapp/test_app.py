from __future__ import annotations

import io
import json

from swingvision_import.review import load_pending, unresolved_flags
from tests.ai.conftest import FakeMessage, FakeTextBlock


def _upload(client, xlsx_bytes: bytes, *, filename: str = "export.xlsx", **extra_form):
    data = {
        "xlsx_file": (io.BytesIO(xlsx_bytes), filename),
        "date": "2026-08-06",
        "opponent": "Alex",
        "result": "W",
    }
    data.update(extra_form)
    return client.post("/import", data=data, content_type="multipart/form-data")


class _FakeSuggestionMessages:
    def create(self, **kwargs):
        payload = json.dumps(
            {"point_end_type": "forced_error", "reasoning": "Deep shot.", "confidence": "medium"}
        )
        return FakeMessage(content=[FakeTextBlock(text=payload)])


class _FakeSuggestionClient:
    def __init__(self):
        self.messages = _FakeSuggestionMessages()


def test_index_renders_form(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"Import a SwingVision match" in response.data


def test_import_stages_pending_json_matching_direct_ingest(client, xlsx_bytes, import_config):
    response = _upload(client, xlsx_bytes)

    assert response.status_code == 200
    assert b"Staged: 2026-08-06 vs Alex" in response.data

    json_path = import_config.pending_dir / "2026-08-06_Alex.json"
    assert json_path.exists()
    record = load_pending(json_path)
    assert len(unresolved_flags(record)) > 0
    assert record.import_notes  # the fixture's gap point produces one


def test_import_missing_xlsx_returns_400_with_error(client):
    response = client.post(
        "/import",
        data={"date": "2026-08-06", "opponent": "Alex", "result": "W"},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert b"choose a SwingVision" in response.data


def test_import_saves_uploaded_video_into_a_per_match_directory(
    client, xlsx_bytes, webapp_config
):
    response = _upload(
        client, xlsx_bytes, video_files=(io.BytesIO(b"fake video bytes"), "clip.mp4")
    )

    assert response.status_code == 200
    saved_video = webapp_config.media_dir / "2026-08-06_Alex" / "clip.mp4"
    assert saved_video.exists()
    assert saved_video.read_bytes() == b"fake video bytes"


def test_hostile_xlsx_filename_does_not_escape_uploads_dir(
    client, xlsx_bytes, webapp_config, tmp_path
):
    response = _upload(client, xlsx_bytes, filename="../../../evil.xlsx")

    assert response.status_code == 200
    assert not (tmp_path / "evil.xlsx").exists()
    assert list(webapp_config.uploads_dir.iterdir())  # something safe landed inside


def test_hostile_video_filename_does_not_escape_media_dir(client, xlsx_bytes, tmp_path):
    response = _upload(
        client, xlsx_bytes, video_files=(io.BytesIO(b"x"), "../../../evil.mp4")
    )

    assert response.status_code == 200
    assert not (tmp_path / "evil.mp4").exists()


def test_ingest_first_server_and_tracked_identity_feed_quality_check(client, xlsx_bytes):
    response = _upload(
        client,
        xlsx_bytes,
        first_server_set1="opponent",  # wrong on purpose - point 1 was really host serving
        tracked_identity="Someone Else",
    )

    assert response.status_code == 200
    assert b"reversed" in response.data
    assert b"Someone Else" in response.data


def test_suggest_rejects_path_traversal_in_json_filename(client):
    response = client.post("/suggest", data={"json_filename": "../../../../etc/passwd"})

    assert response.status_code == 404


def test_suggest_returns_404_for_a_nonexistent_pending_file(client):
    response = client.post("/suggest", data={"json_filename": "does_not_exist.json"})

    assert response.status_code == 404


def test_suggest_runs_claude_assist_and_shows_updated_notes(
    client, xlsx_bytes, monkeypatch
):
    _upload(client, xlsx_bytes)
    monkeypatch.setattr("webapp.app.get_anthropic_client", lambda: _FakeSuggestionClient())

    response = client.post("/suggest", data={"json_filename": "2026-08-06_Alex.json"})

    assert response.status_code == 200
    assert b"Claude suggestions have been added" in response.data
