"""The specific palette slots this project uses.

Every hex value here is lifted verbatim from the dataviz skill's validated
reference palette (references/palette.md) — never re-derived or eyeballed.
Light/dark switching uses `prefers-color-scheme` only; there's no in-page
theme toggle, since this is a static downloaded file, not a Claude Artifact.
"""

from __future__ import annotations

# Sequential (single-hue, magnitude): trend lines, the point-outcome bar chart.
SEQUENTIAL_LIGHT = "#2a78d6"
SEQUENTIAL_DARK = "#3987e5"
SEQUENTIAL_TRACK_LIGHT = "#cde2fb"  # step 100 - the meter's unfilled track
SEQUENTIAL_TRACK_DARK = "#184f95"  # step 600

# Categorical, first two slots only - this project never seats a 3rd
# categorical series (serve in/out; the combined hold%/return% line chart).
CATEGORICAL_1_LIGHT = "#2a78d6"
CATEGORICAL_1_DARK = "#3987e5"
CATEGORICAL_2_LIGHT = "#eb6834"
CATEGORICAL_2_DARK = "#d95926"

# Status (fixed, mode-invariant, never themed): win/loss ticks.
STATUS_GOOD = "#0ca30c"
STATUS_CRITICAL = "#d03b3b"

# Chart chrome & ink.
SURFACE_LIGHT, SURFACE_DARK = "#fcfcfb", "#1a1a19"
PAGE_LIGHT, PAGE_DARK = "#f9f9f7", "#0d0d0d"
INK_PRIMARY_LIGHT, INK_PRIMARY_DARK = "#0b0b0b", "#ffffff"
INK_SECONDARY_LIGHT, INK_SECONDARY_DARK = "#52514e", "#c3c2b7"
INK_MUTED = "#898781"
GRIDLINE_LIGHT, GRIDLINE_DARK = "#e1e0d9", "#2c2c2a"
BASELINE_LIGHT, BASELINE_DARK = "#c3c2b7", "#383835"

_CSS_VARS_TEMPLATE = """
.viz-root {
  color-scheme: light;
  --surface: SURFACE_LIGHT;
  --page: PAGE_LIGHT;
  --ink-primary: INK_PRIMARY_LIGHT;
  --ink-secondary: INK_SECONDARY_LIGHT;
  --ink-muted: INK_MUTED;
  --gridline: GRIDLINE_LIGHT;
  --baseline: BASELINE_LIGHT;
  --sequential: SEQUENTIAL_LIGHT;
  --sequential-track: SEQUENTIAL_TRACK_LIGHT;
  --categorical-1: CATEGORICAL_1_LIGHT;
  --categorical-2: CATEGORICAL_2_LIGHT;
  --status-good: STATUS_GOOD;
  --status-critical: STATUS_CRITICAL;
}
@media (prefers-color-scheme: dark) {
  .viz-root {
    color-scheme: dark;
    --surface: SURFACE_DARK;
    --page: PAGE_DARK;
    --ink-primary: INK_PRIMARY_DARK;
    --ink-secondary: INK_SECONDARY_DARK;
    --gridline: GRIDLINE_DARK;
    --baseline: BASELINE_DARK;
    --sequential: SEQUENTIAL_DARK;
    --sequential-track: SEQUENTIAL_TRACK_DARK;
    --categorical-1: CATEGORICAL_1_DARK;
    --categorical-2: CATEGORICAL_2_DARK;
  }
}
"""


def _build_css_vars() -> str:
    """Fills the CSS custom-property block in from the module's hex constants.

    Returns:
        The `.viz-root` CSS block (light defaults + dark media-query
        override), ready to embed in a `<style>` tag.
    """
    values = {
        "SURFACE_LIGHT": SURFACE_LIGHT,
        "SURFACE_DARK": SURFACE_DARK,
        "PAGE_LIGHT": PAGE_LIGHT,
        "PAGE_DARK": PAGE_DARK,
        "INK_PRIMARY_LIGHT": INK_PRIMARY_LIGHT,
        "INK_PRIMARY_DARK": INK_PRIMARY_DARK,
        "INK_SECONDARY_LIGHT": INK_SECONDARY_LIGHT,
        "INK_SECONDARY_DARK": INK_SECONDARY_DARK,
        "INK_MUTED": INK_MUTED,
        "GRIDLINE_LIGHT": GRIDLINE_LIGHT,
        "GRIDLINE_DARK": GRIDLINE_DARK,
        "BASELINE_LIGHT": BASELINE_LIGHT,
        "BASELINE_DARK": BASELINE_DARK,
        "SEQUENTIAL_LIGHT": SEQUENTIAL_LIGHT,
        "SEQUENTIAL_DARK": SEQUENTIAL_DARK,
        "SEQUENTIAL_TRACK_LIGHT": SEQUENTIAL_TRACK_LIGHT,
        "SEQUENTIAL_TRACK_DARK": SEQUENTIAL_TRACK_DARK,
        "CATEGORICAL_1_LIGHT": CATEGORICAL_1_LIGHT,
        "CATEGORICAL_1_DARK": CATEGORICAL_1_DARK,
        "CATEGORICAL_2_LIGHT": CATEGORICAL_2_LIGHT,
        "CATEGORICAL_2_DARK": CATEGORICAL_2_DARK,
        "STATUS_GOOD": STATUS_GOOD,
        "STATUS_CRITICAL": STATUS_CRITICAL,
    }
    css = _CSS_VARS_TEMPLATE
    for name, value in values.items():
        css = css.replace(name, value)
    return css


CSS_VARS = _build_css_vars()
