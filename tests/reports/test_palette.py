from __future__ import annotations

from reports import palette


def test_css_vars_substitutes_every_placeholder_token():
    # If any placeholder token were left unsubstituted, it would still be
    # present verbatim (all-caps, matching a constant's own name).
    assert "SEQUENTIAL_LIGHT" not in palette.CSS_VARS
    assert "STATUS_GOOD" not in palette.CSS_VARS


def test_css_vars_contains_the_documented_hex_values():
    assert palette.SEQUENTIAL_LIGHT in palette.CSS_VARS
    assert palette.SEQUENTIAL_DARK in palette.CSS_VARS
    assert palette.STATUS_GOOD in palette.CSS_VARS
    assert palette.STATUS_CRITICAL in palette.CSS_VARS


def test_dark_mode_is_scoped_to_a_prefers_color_scheme_media_query():
    assert "@media (prefers-color-scheme: dark)" in palette.CSS_VARS
