"""Hand-rolled inline SVG+CSS+JS chart fragments.

Follows the dataviz skill's method (pick the form, assign color by job,
apply mark specs, ship the hover layer) instead of a plotting library — the
report is HTML already, so real interactivity costs nothing extra.

Each function returns a self-contained HTML fragment (style + svg + tooltip
+ script), safe to embed multiple times on one page given distinct
chart_id values. Fragments each carry their own small `<style>` block
(some duplication when several charts share a page) so every fragment also
renders correctly on its own, which is what test_charts.py exercises.

All labels are free text from the database (opponent names, point-outcome
categories) - every label goes into the DOM via a `data-*` attribute (HTML-
escaped on the way in) and is read back with `.dataset` / set with
`.textContent` in the emitted JS, never `innerHTML` — see the dataviz
skill's interaction.md security note.
"""

from __future__ import annotations

import html
import json
from dataclasses import dataclass

from . import palette

_WIDTH = 640
_BAR_HEIGHT = 24
_BAR_GAP = 12
_ROW_LABEL_WIDTH = 160

_TOOLTIP_STYLE = """
.viz-tooltip {
  position: absolute;
  pointer-events: none;
  background: var(--surface);
  color: var(--ink-primary);
  border: 1px solid var(--gridline);
  border-radius: 4px;
  padding: 4px 8px;
  font: 12px system-ui, -apple-system, "Segoe UI", sans-serif;
  opacity: 0;
  transition: opacity 0.1s;
  white-space: nowrap;
  z-index: 10;
}
.viz-tooltip .value { font-weight: 600; }
.viz-tooltip .label { color: var(--ink-secondary); margin-left: 4px; }
.viz-root { position: relative; }
"""

_TOOLTIP_SCRIPT_TEMPLATE = """
(function () {
  var root = document.getElementById(CHART_ID);
  if (!root) { return; }
  var tooltip = root.querySelector(".viz-tooltip");
  var marks = root.querySelectorAll("[data-value]");
  marks.forEach(function (mark) {
    mark.addEventListener("pointerenter", show);
    mark.addEventListener("pointermove", show);
    mark.addEventListener("pointerleave", hide);
    mark.addEventListener("focus", show);
    mark.addEventListener("blur", hide);
  });
  function show(evt) {
    var mark = evt.currentTarget;
    var valueEl = document.createElement("span");
    valueEl.className = "value";
    valueEl.textContent = mark.dataset.value;
    var labelEl = document.createElement("span");
    labelEl.className = "label";
    labelEl.textContent = mark.dataset.label;
    tooltip.replaceChildren(valueEl, labelEl);
    var rect = root.getBoundingClientRect();
    var clientX = evt.clientX !== undefined ? evt.clientX : rect.left;
    var clientY = evt.clientY !== undefined ? evt.clientY : rect.top;
    tooltip.style.left = (clientX - rect.left + 12) + "px";
    tooltip.style.top = (clientY - rect.top - 28) + "px";
    tooltip.style.opacity = "1";
  }
  function hide() {
    tooltip.style.opacity = "0";
  }
})();
"""


def _svg_open(chart_id: str, width: int, height: int) -> str:
    return (
        f'<div class="viz-root" id="{html.escape(chart_id)}">'
        f"<style>{palette.CSS_VARS}{_TOOLTIP_STYLE}</style>"
        '<div class="viz-tooltip" role="tooltip"></div>'
        f'<svg viewBox="0 0 {width} {height}" width="100%" '
        f'style="max-width:{width}px;display:block" role="img">'
    )


def _svg_close(chart_id: str) -> str:
    # json.dumps, not an f-string or raw substitution, so a chart_id
    # containing a quote or backslash can't break out of the JS string
    # literal — chart_id is a fixed constant at every call site today, but
    # this keeps the function safe even if that ever changes.
    script = _TOOLTIP_SCRIPT_TEMPLATE.replace("CHART_ID", json.dumps(chart_id))
    return f"</svg><script>{script}</script></div>"


def _title(text: str) -> str:
    return (
        f'<text x="0" y="16" fill="var(--ink-primary)" font-size="14" '
        f'font-weight="600">{html.escape(text)}</text>'
    )


@dataclass(frozen=True)
class BarDatum:
    """One row of a bar_chart.

    Attributes:
        label: The category label (e.g. a point_end_type).
        value: The magnitude for this category.
    """

    label: str
    value: float


def bar_chart(chart_id: str, title: str, data: list[BarDatum]) -> str:
    """Horizontal bar chart: one sequential hue, sorted high to low.

    Per the dataviz skill's choosing-a-form guide, "compare magnitude,
    low->high" gets a sequential (one-hue) treatment, not categorical — the
    categories here aren't the subject of the chart, the counts are.

    Args:
        chart_id: Unique DOM id for this chart instance on its page.
        title: Chart title, rendered above the bars.
        data: Rows to plot; rendered sorted descending by value regardless
            of input order.

    Returns:
        A self-contained HTML fragment.
    """
    ordered = sorted(data, key=lambda d: d.value, reverse=True)
    max_value = max((d.value for d in ordered), default=0) or 1
    chart_width = _WIDTH - _ROW_LABEL_WIDTH - 48
    height = 32 + max(len(ordered), 1) * (_BAR_HEIGHT + _BAR_GAP)

    parts = [_title(title)]
    for i, datum in enumerate(ordered):
        y = 32 + i * (_BAR_HEIGHT + _BAR_GAP)
        bar_width = max((datum.value / max_value) * chart_width, 2)
        safe_label = html.escape(datum.label)
        parts.append(
            f'<text x="{_ROW_LABEL_WIDTH - 8}" y="{y + _BAR_HEIGHT / 2 + 4:.1f}" '
            f'text-anchor="end" fill="var(--ink-secondary)" font-size="12">{safe_label}</text>'
            f'<rect x="{_ROW_LABEL_WIDTH}" y="{y}" width="{bar_width:.1f}" height="{_BAR_HEIGHT}" '
            f'rx="4" fill="var(--sequential)" tabindex="0" '
            f'data-label="{safe_label}" data-value="{datum.value:g}" />'
            f'<text x="{_ROW_LABEL_WIDTH + bar_width + 6:.1f}" '
            f'y="{y + _BAR_HEIGHT / 2 + 4:.1f}" fill="var(--ink-primary)" '
            f'font-size="12">{datum.value:g}</text>'
        )

    return _svg_open(chart_id, _WIDTH, height) + "".join(parts) + _svg_close(chart_id)


@dataclass(frozen=True)
class StackedBarRow:
    """One row of a stacked_bar_chart.

    Attributes:
        label: The row's label (e.g. "1st serve").
        category_1_value: Value in the first (categorical slot 1) segment.
        category_2_value: Value in the second (categorical slot 2) segment.
    """

    label: str
    category_1_value: float
    category_2_value: float


def stacked_bar_chart(
    chart_id: str,
    title: str,
    category_1_name: str,
    category_2_name: str,
    rows: list[StackedBarRow],
) -> str:
    """Stacked bar chart for exactly 2 categories (e.g. serve in vs. out).

    Args:
        chart_id: Unique DOM id for this chart instance on its page.
        title: Chart title.
        category_1_name: Name of the categorical-slot-1 segment.
        category_2_name: Name of the categorical-slot-2 segment.
        rows: One row per bar, each with both segments' values.

    Returns:
        A self-contained HTML fragment.
    """
    chart_width = _WIDTH - _ROW_LABEL_WIDTH - 48
    height = 56 + max(len(rows), 1) * (_BAR_HEIGHT + _BAR_GAP)
    gap = 2
    max_total = max((r.category_1_value + r.category_2_value for r in rows), default=0) or 1

    safe_cat_1, safe_cat_2 = html.escape(category_1_name), html.escape(category_2_name)
    legend = (
        '<g transform="translate(0,32)">'
        '<rect x="0" y="-10" width="10" height="10" rx="2" fill="var(--categorical-1)" />'
        f'<text x="14" y="-1" fill="var(--ink-secondary)" font-size="12">{safe_cat_1}</text>'
        '<rect x="90" y="-10" width="10" height="10" rx="2" fill="var(--categorical-2)" />'
        f'<text x="104" y="-1" fill="var(--ink-secondary)" font-size="12">{safe_cat_2}</text>'
        "</g>"
    )

    parts = [_title(title), legend]
    for i, row in enumerate(rows):
        y = 56 + i * (_BAR_HEIGHT + _BAR_GAP)
        seg1_width = max((row.category_1_value / max_total) * chart_width - gap / 2, 0)
        seg2_width = max((row.category_2_value / max_total) * chart_width - gap / 2, 0)
        safe_label = html.escape(row.label)
        parts.append(
            f'<text x="{_ROW_LABEL_WIDTH - 8}" y="{y + _BAR_HEIGHT / 2 + 4:.1f}" '
            f'text-anchor="end" fill="var(--ink-secondary)" font-size="12">{safe_label}</text>'
            f'<rect x="{_ROW_LABEL_WIDTH}" y="{y}" width="{seg1_width:.1f}" height="{_BAR_HEIGHT}" '
            f'rx="4" fill="var(--categorical-1)" tabindex="0" '
            f'data-label="{safe_cat_1} — {safe_label}" data-value="{row.category_1_value:g}" />'
            f'<rect x="{_ROW_LABEL_WIDTH + seg1_width + gap:.1f}" y="{y}" '
            f'width="{seg2_width:.1f}" height="{_BAR_HEIGHT}" rx="4" fill="var(--categorical-2)" '
            f'tabindex="0" data-label="{safe_cat_2} — {safe_label}" '
            f'data-value="{row.category_2_value:g}" />'
        )

    return _svg_open(chart_id, _WIDTH, height) + "".join(parts) + _svg_close(chart_id)


@dataclass(frozen=True)
class LinePoint:
    """One point of a line_chart.

    Attributes:
        x_label: The x-axis label for this point (e.g. a match date).
        value: The y value.
    """

    x_label: str
    value: float


def line_chart(chart_id: str, title: str, points: list[LinePoint]) -> str:
    """Single-series line chart (e.g. a stat trending across matches).

    Uses per-point hover (each data point is its own hit target, per
    interaction.md's allowance for dense/scatter-like point layers) rather
    than a continuous mouse-tracking crosshair — every value stays reachable
    on hover/focus either way; this is the simpler of the two to implement
    correctly.

    Args:
        chart_id: Unique DOM id for this chart instance on its page.
        title: Chart title.
        points: Ordered points, oldest first.

    Returns:
        A self-contained HTML fragment.
    """
    width, height = _WIDTH, 200
    plot_left, plot_right = 40, width - 16
    plot_top, plot_bottom = 32, height - 32
    plot_width = plot_right - plot_left
    plot_height = plot_bottom - plot_top

    values = [p.value for p in points] or [0.0]
    min_value, max_value = min(values), max(values)
    if max_value == min_value:
        max_value = min_value + 1

    def x_at(i: int) -> float:
        if len(points) <= 1:
            return plot_left + plot_width / 2
        return plot_left + (i / (len(points) - 1)) * plot_width

    def y_at(value: float) -> float:
        return plot_bottom - ((value - min_value) / (max_value - min_value)) * plot_height

    coords = [(x_at(i), y_at(p.value)) for i, p in enumerate(points)]
    gridlines = "".join(
        f'<line x1="{plot_left}" x2="{plot_right}" y1="{plot_top + frac * plot_height:.1f}" '
        f'y2="{plot_top + frac * plot_height:.1f}" stroke="var(--gridline)" stroke-width="1" />'
        for frac in (0.0, 0.5, 1.0)
    )
    line = (
        '<polyline points="'
        + " ".join(f"{x:.1f},{y:.1f}" for x, y in coords)
        + '" fill="none" stroke="var(--sequential)" stroke-width="2" '
        'stroke-linejoin="round" stroke-linecap="round" />'
    )

    markers = []
    for (x, y), point in zip(coords, points):
        safe_label = html.escape(point.x_label)
        markers.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="var(--sequential)" '
            f'stroke="var(--surface)" stroke-width="2" />'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="12" fill="transparent" tabindex="0" '
            f'data-label="{safe_label}" data-value="{point.value:g}" />'
        )

    body = _title(title) + gridlines + line + "".join(markers)
    return _svg_open(chart_id, width, height) + body + _svg_close(chart_id)


def stat_tile(label: str, value: str) -> str:
    """A single stat tile: label + value, no chart.

    Per the dataviz skill's "is it even a chart?" table, a single current
    value doesn't need a chart form.

    Args:
        label: Sentence-case label, no trailing colon.
        value: Pre-formatted display value (e.g. "62.0%", "2.1").

    Returns:
        A small self-contained HTML fragment (no interactivity needed).
    """
    return (
        '<div class="viz-root viz-stat-tile">'
        f"<style>{palette.CSS_VARS}"
        ".viz-stat-tile { padding: 8px 12px; }"
        ".viz-stat-tile .viz-label { font: 12px system-ui, sans-serif; "
        "color: var(--ink-secondary); }"
        ".viz-stat-tile .viz-value { font: 600 24px system-ui, sans-serif; "
        "color: var(--ink-primary); }"
        "</style>"
        f'<div class="viz-label">{html.escape(label)}</div>'
        f'<div class="viz-value">{html.escape(value)}</div>'
        "</div>"
    )


def meter(chart_id: str, label: str, value_pct: float) -> str:
    """A single-ratio meter: a fill over a lighter track of the same hue.

    Args:
        chart_id: Unique DOM id for this chart instance on its page.
        label: What the ratio represents (e.g. "Net Success Rate").
        value_pct: 0-100; clamped into that range.

    Returns:
        A self-contained HTML fragment.
    """
    width, height = 320, 56
    clamped = max(0.0, min(100.0, value_pct))
    track_width = width - 16
    fill_width = track_width * clamped / 100
    safe_label = html.escape(label)

    body = (
        _title(label)
        + f'<rect x="0" y="26" width="{track_width}" height="12" rx="6" '
        'fill="var(--sequential-track)" />'
        f'<rect x="0" y="26" width="{fill_width:.1f}" height="12" rx="6" '
        f'fill="var(--sequential)" tabindex="0" data-label="{safe_label}" '
        f'data-value="{clamped:g}%" />'
    )
    return _svg_open(chart_id, width, height) + body + _svg_close(chart_id)


@dataclass(frozen=True)
class StatusEntry:
    """One entry of a status_strip.

    Attributes:
        label: What to show in the tooltip (e.g. "2026-08-06 vs. Alex").
        is_good: True for a win, False for a loss.
    """

    label: str
    is_good: bool


def status_strip(chart_id: str, title: str, entries: list[StatusEntry]) -> str:
    """A compact row of win/loss ticks, using the fixed status palette.

    Win/loss is a state, not an arbitrary category, so this uses the status
    good/critical colors rather than a categorical hue — per the dataviz
    skill's color-formula "the collision rule": a series that means
    good/bad wears status tokens, not categorical ones.

    Args:
        chart_id: Unique DOM id for this chart instance on its page.
        title: Chart title.
        entries: One entry per match, oldest first.

    Returns:
        A self-contained HTML fragment.
    """
    tick_size, gap = 16, 6
    width = max(_WIDTH, len(entries) * (tick_size + gap))
    height = 48

    ticks = []
    for i, entry in enumerate(entries):
        x = i * (tick_size + gap)
        color = "var(--status-good)" if entry.is_good else "var(--status-critical)"
        result_text = "Win" if entry.is_good else "Loss"
        ticks.append(
            f'<rect x="{x}" y="20" width="{tick_size}" height="{tick_size}" rx="3" '
            f'fill="{color}" tabindex="0" data-label="{html.escape(entry.label)}" '
            f'data-value="{result_text}" />'
        )

    body = _title(title) + "".join(ticks)
    return _svg_open(chart_id, width, height) + body + _svg_close(chart_id)
