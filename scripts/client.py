"""Constructs the real Anthropic client for scripts.

ai/client.py's AnthropicClientLike is always injected, never constructed
inside ai/ or src/swingvision_import/ themselves, so tests never touch the
real API or spend real money. This module is the one place that actually
builds a real client - for scripts that intentionally want to.
"""

from __future__ import annotations

import os

import anthropic
from dotenv import load_dotenv


def get_anthropic_client() -> anthropic.Anthropic:
    """Loads .env (if present) and constructs a real Anthropic client.

    Returns:
        An anthropic.Anthropic client authenticated from the
        ANTHROPIC_API_KEY environment variable.

    Raises:
        RuntimeError: If ANTHROPIC_API_KEY isn't set after loading .env.
    """
    load_dotenv()
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Copy .env.example to .env and fill in "
            "a real key, or export it in your shell before running this script."
        )
    return anthropic.Anthropic(api_key=api_key)
