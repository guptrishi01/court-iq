from __future__ import annotations

from reports import charts


def test_bar_chart_sorts_descending_and_uses_rounded_data_ends():
    data = [
        charts.BarDatum("Unforced errors", 3),
        charts.BarDatum("Winners", 8),
        charts.BarDatum("Aces", 1),
    ]

    svg = charts.bar_chart("point-outcomes", "Point Outcomes", data)

    # 3 categories -> 3 bars, each with a 4px rounded data-end.
    assert svg.count('rx="4"') == 3
    winners_idx = svg.index("Winners")
    unforced_idx = svg.index("Unforced errors")
    assert winners_idx < unforced_idx  # higher value rendered first


def test_bar_chart_labels_values_at_the_tip():
    svg = charts.bar_chart("c1", "t", [charts.BarDatum("Aces", 5)])

    assert 'data-value="5"' in svg
    assert ">5<" in svg  # the tip label text node


def test_bar_chart_escapes_html_unsafe_labels():
    malicious_label = '<script>alert(1)</script>"'

    svg = charts.bar_chart("c1", "t", [charts.BarDatum(malicious_label, 1)])

    assert "<script>alert(1)</script>" not in svg
    assert "&lt;script&gt;" in svg


def test_stacked_bar_chart_has_a_legend_and_two_segments_per_row():
    rows = [charts.StackedBarRow("1st serve", 6, 4)]

    svg = charts.stacked_bar_chart("serve", "Serve", "In", "Out", rows)

    assert "var(--categorical-1)" in svg
    assert "var(--categorical-2)" in svg
    assert svg.count('data-value="6"') == 1
    assert svg.count('data-value="4"') == 1


def test_line_chart_renders_one_marker_pair_per_point():
    points = [charts.LinePoint("2026-08-01", 50.0), charts.LinePoint("2026-08-08", 60.0)]

    svg = charts.line_chart("fs-trend", "FS% Trend", points)

    assert svg.count("<circle") == 4  # visible marker + hit target per point
    assert "<polyline" in svg


def test_line_chart_handles_a_single_point_without_dividing_by_zero():
    svg = charts.line_chart("c1", "t", [charts.LinePoint("2026-08-01", 50.0)])

    assert "<circle" in svg


def test_line_chart_handles_zero_points():
    svg = charts.line_chart("c1", "t", [])

    assert "<svg" in svg


def test_line_chart_handles_flat_data_without_dividing_by_zero():
    points = [charts.LinePoint("d1", 50.0), charts.LinePoint("d2", 50.0)]

    svg = charts.line_chart("c1", "t", points)

    assert svg.count("<circle") == 4


def test_stat_tile_escapes_and_renders_label_and_value():
    tile = charts.stat_tile("First Serve %", "62.0%")

    assert "First Serve %" in tile
    assert "62.0%" in tile


def test_meter_clamps_values_outside_zero_to_one_hundred():
    over = charts.meter("m1", "Net Success", 150.0)
    under = charts.meter("m2", "Net Success", -20.0)

    assert 'data-value="100%"' in over
    assert 'data-value="0%"' in under


def test_status_strip_uses_the_status_palette_not_categorical():
    entries = [
        charts.StatusEntry("2026-08-01 vs. Alex", True),
        charts.StatusEntry("2026-08-08 vs. Jordan", False),
    ]

    svg = charts.status_strip("results", "Match Results", entries)

    assert "var(--status-good)" in svg
    assert "var(--status-critical)" in svg
    assert "var(--categorical-1)" not in svg


def test_every_chart_hover_script_uses_textcontent_never_innerhtml():
    charts_html = [
        charts.bar_chart("c1", "t", [charts.BarDatum("a", 1)]),
        charts.stacked_bar_chart("c2", "t", "In", "Out", [charts.StackedBarRow("r", 1, 1)]),
        charts.line_chart("c3", "t", [charts.LinePoint("d", 1)]),
        charts.meter("c4", "t", 50.0),
        charts.status_strip("c5", "t", [charts.StatusEntry("l", True)]),
    ]

    for html_fragment in charts_html:
        assert "innerHTML" not in html_fragment
        assert "textContent" in html_fragment


def test_chart_id_is_safe_in_both_the_html_attribute_and_the_js_string_literal():
    # A chart_id containing a quote must not break out of either the HTML
    # id="..." attribute or the JS getElementById("...") string literal.
    hostile_id = '"><img src=x>'

    svg = charts.bar_chart(hostile_id, "t", [charts.BarDatum("a", 1)])

    # The id="..." attribute's own value must contain no raw quote - a raw
    # quote there would let the payload terminate the attribute early.
    id_attr_start = svg.index('id="') + len('id="')
    id_attr_value = svg[id_attr_start : svg.index('"', id_attr_start)]
    assert '"' not in id_attr_value

    # The getElementById(...) argument must be the properly JSON-escaped,
    # syntactically-balanced string - not a raw splice of the hostile id.
    assert 'getElementById("\\"><img src=x>")' in svg
