"""Calls one coaching specialist and parses its structured JSON output.

The Anthropic client is always passed in, never constructed here — that's
what lets tests inject a fake client and never touch the real API or spend
real money.
"""

from __future__ import annotations

import json
import logging
from typing import Protocol

import anthropic

from .config import AICoachConfig
from .records import Category, CoachingItem, DrillItem, FitnessItem, SupportingStat

logger = logging.getLogger(__name__)

_ITEM_CLASSES: dict[str, type] = {
    "strategy": CoachingItem,
    "drill": DrillItem,
    "fitness": FitnessItem,
}

_EXTRA_FIELDS: dict[str, list[str]] = {
    "strategy": [],
    "drill": ["drill_name", "frequency"],
    "fitness": ["focus_area"],
}


class _Message(Protocol):
    content: list[object]


class _Messages(Protocol):
    def create(self, **kwargs: object) -> _Message: ...


class AnthropicClientLike(Protocol):
    """The minimal shape of anthropic.Anthropic this module depends on.

    Defined as a Protocol (structural typing) rather than importing
    anthropic.Anthropic directly, so a test's fake client only needs to
    match this shape, not subclass or mock the real SDK class.
    """

    messages: _Messages


class SpecialistError(RuntimeError):
    """Raised when a coaching specialist call fails.

    Covers both failure modes: the API call itself failing (auth, rate
    limit, network — an `anthropic.APIError`), and the API call succeeding
    but returning a response that isn't valid JSON matching the expected
    item schema. Both are handled identically by generate.py — one
    specialist failing degrades that section of the report, not the whole
    thing — so they share one exception type rather than two.

    Attributes:
        category: Which specialist failed.
        raw_response: The raw text that failed to parse, or "" if the API
            call itself failed before any response was received.
    """

    def __init__(self, category: str, raw_response: str, cause: Exception) -> None:
        super().__init__(f"{category} specialist failed: {cause}")
        self.category = category
        self.raw_response = raw_response


def call_specialist(
    client: AnthropicClientLike,
    config: AICoachConfig,
    category: Category,
    system_prompt: str,
) -> list[CoachingItem]:
    """Calls one coaching specialist and parses its structured JSON output.

    Args:
        client: An anthropic.Anthropic-shaped client.
        config: Model/token/temperature settings.
        category: "strategy", "drill", or "fitness" — selects which
            dataclass to parse items into.
        system_prompt: The specialist's full system prompt, already built
            by prompts.py (includes the context and the response schema).

    Returns:
        The parsed list of items for this specialist.

    Raises:
        SpecialistError: If the API call itself fails (auth, rate limit,
            network — any `anthropic.APIError`), or if it succeeds but the
            response isn't valid JSON matching the expected item schema.
    """
    try:
        response = client.messages.create(
            model=config.model,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": "Generate the coaching items now."}],
        )
    except anthropic.APIError as exc:
        raise SpecialistError(category, "", exc) from exc

    raw_text = response.content[0].text

    item_class = _ITEM_CLASSES[category]
    extra_fields = _EXTRA_FIELDS[category]
    try:
        raw_items = json.loads(raw_text)
        return [
            item_class(
                category=category,
                observation=raw["observation"],
                recommendation=raw["recommendation"],
                supporting_stat=SupportingStat(**raw["supporting_stat"]),
                priority=raw["priority"],
                **{field: raw[field] for field in extra_fields},
            )
            for raw in raw_items
        ]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise SpecialistError(category, raw_text, exc) from exc
