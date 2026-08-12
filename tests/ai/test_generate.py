from __future__ import annotations

import logging

from ai.config import AICoachConfig
from ai.context import build_context
from ai.generate import generate_all
from tests.ai.conftest import FakeAnthropicClient


def test_generate_all_invokes_all_three_specialists(sample_match_stats):
    client = FakeAnthropicClient()
    context = build_context(sample_match_stats)

    generate_all(client, AICoachConfig(), context)

    assert len(client.messages.calls) == 3
    systems = {call["system"] for call in client.messages.calls}
    assert any("strategy analyst" in s for s in systems)
    assert any("drill designer" in s for s in systems)
    assert any("conditioning coach" in s for s in systems)


def test_generate_all_returns_items_in_the_right_category_slot(sample_match_stats):
    client = FakeAnthropicClient()
    context = build_context(sample_match_stats)

    strategy, drills, fitness = generate_all(client, AICoachConfig(), context)

    assert strategy[0].category == "strategy"
    assert drills[0].category == "drill"
    assert fitness[0].category == "fitness"


def test_generate_all_does_not_fail_the_whole_report_when_one_specialist_fails(
    sample_match_stats, caplog
):
    client = FakeAnthropicClient(raise_for={"drill"})
    context = build_context(sample_match_stats)

    with caplog.at_level(logging.ERROR):
        strategy, drills, fitness = generate_all(client, AICoachConfig(), context)

    assert len(strategy) == 1
    assert drills == []
    assert len(fitness) == 1
    assert any("drill" in record.message for record in caplog.records)
