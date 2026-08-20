from __future__ import annotations

import json

import anthropic
import httpx
import pytest

from swingvision_import.raw import RawShotRow
from swingvision_import.records import PointRecord
from swingvision_import.review_assist import (
    SuggestionConfig,
    SuggestionError,
    suggest_point_resolution,
)
from tests.ai.conftest import FakeMessage, FakeTextBlock


class _FakeMessages:
    """A purpose-built fake for review_assist's single-shot-suggestion
    prompt/response shape - reuses tests/ai/conftest.py's FakeMessage/
    FakeTextBlock response primitives rather than redefining them, but
    review_assist's response schema (point_end_type/reasoning/confidence)
    doesn't match ai/'s specialist item schema, so FakeAnthropicClient
    itself isn't a fit here."""

    def __init__(self, response_text: str | None = None, raise_error: Exception | None = None):
        self.response_text = response_text
        self.raise_error = raise_error
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.raise_error:
            raise self.raise_error
        return FakeMessage(content=[FakeTextBlock(text=self.response_text)])


class _FakeClient:
    def __init__(self, response_text: str | None = None, raise_error: Exception | None = None):
        self.messages = _FakeMessages(response_text, raise_error)


def _point() -> PointRecord:
    return PointRecord(
        game_number=1,
        point_number=1,
        is_serving=True,
        point_won=False,
        point_end_type="unforced_error",
        needs_review=True,
    )


def _shots() -> list[RawShotRow]:
    return [
        RawShotRow(1, 1, "Rishi Gupta", "first_serve", "Serve", "In"),
        RawShotRow(1, 2, "Opponent", "first_return", "Forehand", "In"),
        RawShotRow(1, 3, "Rishi Gupta", "serve_plus_one", "Forehand", "Net"),
    ]


def test_suggest_point_resolution_parses_a_valid_response():
    valid = json.dumps(
        {"point_end_type": "forced_error", "reasoning": "Wide angle return.", "confidence": "high"}
    )
    client = _FakeClient(response_text=valid)

    suggestion = suggest_point_resolution(client, SuggestionConfig(), _point(), _shots())

    assert suggestion.point_end_type == "forced_error"
    assert suggestion.confidence == "high"
    assert "angle" in suggestion.reasoning


def test_suggest_point_resolution_includes_shot_context_in_the_prompt():
    valid = json.dumps({"point_end_type": "unforced_error", "reasoning": "x", "confidence": "low"})
    client = _FakeClient(response_text=valid)

    suggest_point_resolution(client, SuggestionConfig(), _point(), _shots())

    system = client.messages.calls[0]["system"]
    assert "serve_plus_one" in system
    assert '"result": "Net"' in system


def test_suggest_point_resolution_raises_on_api_failure():
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    error = anthropic.APIConnectionError(message="boom", request=request)
    client = _FakeClient(raise_error=error)

    with pytest.raises(SuggestionError) as exc_info:
        suggest_point_resolution(client, SuggestionConfig(), _point(), _shots())

    assert exc_info.value.raw_response == ""
    assert "boom" in str(exc_info.value)


def test_suggest_point_resolution_raises_on_invalid_json():
    client = _FakeClient(response_text="not json")

    with pytest.raises(SuggestionError) as exc_info:
        suggest_point_resolution(client, SuggestionConfig(), _point(), _shots())

    assert exc_info.value.raw_response == "not json"


def test_suggest_point_resolution_raises_on_an_invalid_point_end_type():
    invalid = json.dumps({"point_end_type": "let", "reasoning": "x", "confidence": "low"})
    client = _FakeClient(response_text=invalid)

    with pytest.raises(SuggestionError):
        suggest_point_resolution(client, SuggestionConfig(), _point(), _shots())


def test_suggest_point_resolution_raises_on_missing_required_key():
    incomplete = json.dumps({"point_end_type": "winner"})
    client = _FakeClient(response_text=incomplete)

    with pytest.raises(SuggestionError):
        suggest_point_resolution(client, SuggestionConfig(), _point(), _shots())


def test_suggest_point_resolution_passes_model_and_sampling_config_through():
    valid = json.dumps({"point_end_type": "winner", "reasoning": "x", "confidence": "high"})
    client = _FakeClient(response_text=valid)
    config = SuggestionConfig(model="claude-sonnet-5", max_tokens=256, temperature=0.1)

    suggest_point_resolution(client, config, _point(), _shots())

    call = client.messages.calls[0]
    assert call["model"] == "claude-sonnet-5"
    assert call["max_tokens"] == 256
    assert call["temperature"] == 0.1
