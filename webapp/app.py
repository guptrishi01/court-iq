"""Flask entry point: a local intake form for staging a SwingVision match.

Reuses SwingVisionImportPipeline.ingest()/suggest() exactly as
scripts/import_match.py does - a second front door onto the same pipeline,
not a parallel implementation. Scope is intentionally bounded to intake
plus a read-only results page; resolving needs_review flags is still a
hand-edit-the-JSON step (or the existing CLI), not built here.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "src"))
sys.path.insert(0, str(_REPO_ROOT))

from flask import Flask, render_template, request  # noqa: E402

from logging_config import configure_logging  # noqa: E402
from scripts.client import get_anthropic_client  # noqa: E402
from swingvision_import.config import ImportConfig  # noqa: E402
from swingvision_import.pipeline import SwingVisionImportPipeline  # noqa: E402
from swingvision_import.review import load_pending, unresolved_flags  # noqa: E402
from webapp.config import WebAppConfig  # noqa: E402
from webapp.uploads import save_uploaded_videos, save_uploaded_xlsx  # noqa: E402

_SET_NUMBERS = (1, 2, 3)
_OVERRIDE_TEXT_FIELDS = ("pros", "cons", "notes", "location")
_OVERRIDE_RATING_FIELDS = ("energy_rating", "mental_rating")


def _parse_first_server_by_set(form) -> dict[int, str] | None:
    """Builds the set_number -> "me"/"opponent" map from the intake form.

    Args:
        form: The submitted form (request.form).

    Returns:
        The map, or None if no set's question was answered.
    """
    first_server_by_set = {}
    for set_number in _SET_NUMBERS:
        value = form.get(f"first_server_set{set_number}")
        if value:
            first_server_by_set[set_number] = value
    return first_server_by_set or None


def _parse_match_overrides(form) -> dict[str, object]:
    """Builds the ingest() match_overrides kwargs from the intake form.

    Args:
        form: The submitted form (request.form).

    Returns:
        Only the fields the user actually filled in - ingest() defaults
        handle the rest.
    """
    overrides: dict[str, object] = {}
    for field in _OVERRIDE_RATING_FIELDS:
        value = form.get(field)
        if value:
            overrides[field] = int(value)
    for field in _OVERRIDE_TEXT_FIELDS:
        value = form.get(field)
        if value:
            overrides[field] = value
    return overrides


def _render_result(record, json_path: Path, *, suggested: bool):
    flags = unresolved_flags(record)
    return render_template(
        "import_result.html.jinja",
        json_filename=json_path.name,
        date=record.date,
        opponent=record.opponent,
        flag_count=len(flags),
        import_notes=record.import_notes,
        suggested=suggested,
    )


def create_app(
    import_config: ImportConfig | None = None,
    webapp_config: WebAppConfig | None = None,
) -> Flask:
    """Builds the Flask app.

    Args:
        import_config: SwingVision import pipeline settings. Defaults to
            ImportConfig() if not given.
        webapp_config: Upload directory settings. Defaults to
            WebAppConfig() if not given.

    Returns:
        A configured, ready-to-run Flask app.
    """
    configure_logging()
    app = Flask(__name__)
    # Template files are named *.html.jinja (matching reports/templates/'s
    # convention) - Flask's default autoescape heuristic only recognizes a
    # bare .html extension, so it must be forced on explicitly here rather
    # than relied on by default.
    app.jinja_env.autoescape = True

    import_config = import_config or ImportConfig()
    webapp_config = webapp_config or WebAppConfig()
    app.config["MAX_CONTENT_LENGTH"] = webapp_config.max_content_length
    pipeline = SwingVisionImportPipeline(import_config)

    @app.get("/")
    def index():
        return render_template("import_form.html.jinja")

    @app.post("/import")
    def do_import():
        xlsx_file = request.files.get("xlsx_file")
        if xlsx_file is None or not xlsx_file.filename:
            return (
                render_template(
                    "import_form.html.jinja",
                    error="Please choose a SwingVision .xlsx export.",
                ),
                400,
            )

        date = request.form["date"]
        opponent = request.form["opponent"]
        result = request.form["result"]

        xlsx_path = save_uploaded_xlsx(
            xlsx_file, date=date, opponent=opponent, uploads_dir=webapp_config.uploads_dir
        )
        video_files = [f for f in request.files.getlist("video_files") if f and f.filename]
        save_uploaded_videos(
            video_files, date=date, opponent=opponent, media_dir=webapp_config.media_dir
        )

        try:
            json_path = pipeline.ingest(
                xlsx_path,
                date=date,
                opponent=opponent,
                result=result,
                first_server_by_set=_parse_first_server_by_set(request.form),
                tracked_identity=request.form.get("tracked_identity") or None,
                **_parse_match_overrides(request.form),
            )
        except ValueError as exc:
            return render_template("import_form.html.jinja", error=str(exc)), 400

        return _render_result(load_pending(json_path), json_path, suggested=False)

    @app.post("/suggest")
    def do_suggest():
        json_filename = request.form["json_filename"]
        pending_dir = import_config.pending_dir.resolve()
        json_path = (pending_dir / json_filename).resolve()
        if pending_dir not in json_path.parents or not json_path.exists():
            return "Pending match not found.", 404

        client = get_anthropic_client()
        record = pipeline.suggest(client, json_path)

        return _render_result(record, json_path, suggested=True)

    return app


if __name__ == "__main__":
    # Binds to 127.0.0.1 by default (Flask's own default) - a local,
    # single-user tool, never meant to be exposed beyond localhost.
    create_app().run(debug=True)
