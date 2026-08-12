from __future__ import annotations

import pytest

from ai.client import SpecialistError, call_specialist
from ai.config import AICoachConfig
from ai.records import DrillItem, FitnessItem
from tests.ai.conftest import FakeAnthropicClient


def test_call_specialist_parses_a_valid_strategy_response():
    client = FakeAnthropicClient()

    items = call_specialist(client, AICoachConfig(), "strategy", "You are a strategy analyst.")

    assert len(items) == 1
    assert items[0].category == "strategy"
    assert items[0].supporting_stat.stat == "FS%"


def test_call_specialist_parses_drill_specific_fields():
    client = FakeAnthropicClient()

    items = call_specialist(client, AICoachConfig(), "drill", "You are a drill designer.")

    assert isinstance(items[0], DrillItem)
    assert items[0].drill_name == "Cross-court consistency"


def test_call_specialist_parses_fitness_specific_fields():
    client = FakeAnthropicClient()

    items = call_specialist(client, AICoachConfig(), "fitness", "You are a conditioning coach.")

    assert isinstance(items[0], FitnessItem)
    assert items[0].focus_area == "endurance"


def test_call_specialist_raises_specialist_error_on_invalid_json():
    client = FakeAnthropicClient(raise_for={"strategy"})

    with pytest.raises(SpecialistError) as exc_info:
        call_specialist(client, AICoachConfig(), "strategy", "You are a strategy analyst.")

    assert exc_info.value.category == "strategy"
    assert exc_info.value.raw_response == "not valid json"


def test_call_specialist_raises_specialist_error_on_missing_required_key():
    # Missing supporting_stat/priority.
    incomplete_item = {"observation": "x", "recommendation": "y"}
    client = FakeAnthropicClient(response_for={"strategy": [incomplete_item]})

    with pytest.raises(SpecialistError):
        call_specialist(client, AICoachConfig(), "strategy", "You are a strategy analyst.")


def test_call_specialist_passes_model_and_sampling_config_through():
    client = FakeAnthropicClient()
    config = AICoachConfig(model="claude-sonnet-5", max_tokens=512, temperature=0.3)

    call_specialist(client, config, "strategy", "You are a strategy analyst.")

    call = client.messages.calls[0]
    assert call["model"] == "claude-sonnet-5"
    assert call["max_tokens"] == 512
    assert call["temperature"] == 0.3
