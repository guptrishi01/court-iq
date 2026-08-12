from __future__ import annotations

import json

from ai.context import build_context


def test_build_context_carries_match_metadata_and_self_assessment(sample_match_stats):
    context = build_context(sample_match_stats)

    assert context.match_id == 1
    assert context.opponent == "Alex"
    assert context.result == "W"
    assert context.pros == "Served big"
    assert context.cons == "Slow starts"
    assert context.energy_rating == 4
    assert context.mental_rating == 3


def test_build_context_maps_every_stat_using_stat_definitions_abbreviations(sample_match_stats):
    context = build_context(sample_match_stats)

    assert context.stats["FS%"] == sample_match_stats.serving.first_serve_pct
    assert context.stats["BP%"] == sample_match_stats.receiving.break_point_conversion_pct
    assert context.stats["W/UE"] == sample_match_stats.point_outcomes.winner_to_ue_ratio
    assert context.stats["NS%"] == sample_match_stats.net.net_success_pct
    assert context.stats["DC%"] == sample_match_stats.clutch.deuce_conversion_pct


def test_build_context_is_deterministic(sample_match_stats):
    assert build_context(sample_match_stats) == build_context(sample_match_stats)


def test_to_dict_is_json_serializable(sample_match_stats):
    context = build_context(sample_match_stats)
    # Must not raise.
    json.dumps(context.to_dict())
