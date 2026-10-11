"""Dependency-free SVG and standalone HTML chart rendering."""

from __future__ import annotations

from html import escape
from typing import Sequence


DeltaRow = tuple[int, float, int]


def _signed(value: float | int, digits: int = 0) -> str:
    sign = "+" if value > 0 else "−" if value < 0 else ""
    return f"{sign}{abs(value):,.{digits}f}"


def _position(value: float, domain: tuple[float, float], left: float, width: float) -> float:
    minimum, maximum = domain
    return left + (value - minimum) / (maximum - minimum) * width


def _panel(
    rows: Sequence[DeltaRow],
    *,
    offset: float,
    title: str,
    domain: tuple[float, float],
    ticks: tuple[str, str, str],
    value_index: int,
    formatter,
) -> str:
    plot_left = offset + 90
    plot_width = 330
    value_x = offset + 515
    zero_x = _position(0, domain, plot_left, plot_width)
    parts = [
        f'<text class="panel-title" x="{offset + 20:g}" y="54">{escape(title)}</text>',
        f'<text class="axis-label" x="{plot_left:g}" y="86">{escape(ticks[0])}</text>',
        f'<text class="axis-label center" x="{zero_x:g}" y="86">{escape(ticks[1])}</text>',
        f'<text class="axis-label end" x="{plot_left + plot_width:g}" y="86">{escape(ticks[2])}</text>',
        f'<line class="zero" x1="{zero_x:g}" y1="96" x2="{zero_x:g}" y2="438" />',
    ]
    for index, row in enumerate(rows):
        year = row[0]
        value = row[value_index]
        y = 122 + index * 54
        value_position = _position(value, domain, plot_left, plot_width)
        bar_x = min(zero_x, value_position)
        bar_width = max(2.0, abs(value_position - zero_x))
        direction = "positive" if value > 0 else "negative"
        label = formatter(value)
        parts.extend(
            [
                f'<text class="year" x="{offset + 20:g}" y="{y + 14:g}">{year}</text>',
                f'<line class="guide" x1="{plot_left:g}" y1="{y + 8:g}" x2="{plot_left + plot_width:g}" y2="{y + 8:g}" />',
                f'<rect class="bar {direction}" x="{bar_x:.2f}" y="{y:g}" width="{bar_width:.2f}" height="16" rx="3" />',
                f'<text class="value end" x="{value_x:g}" y="{y + 14:g}">{escape(label)}</text>',
            ]
        )
    return "\n    ".join(parts)


def render_svg(rows: Sequence[DeltaRow]) -> str:
    """Render aligned share-point and vote-delta panels."""
    share_panel = _panel(
        rows,
        offset=0,
        title="得票率增減（百分點）",
        domain=(-13, 7),
        ticks=("−13", "0", "+7"),
        value_index=1,
        formatter=lambda value: f"{_signed(value, 2)} pp",
    )
    vote_panel = _panel(
        rows,
        offset=610,
        title="選票增減（票）",
        domain=(-300000, 130000),
        ticks=("−30萬", "0", "+13萬"),
        value_index=2,
        formatter=lambda value: _signed(value),
    )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 500" role="img" aria-labelledby="chart-title chart-desc">
  <title id="chart-title">台北市泛藍總統票每屆增減</title>
  <desc id="chart-desc">2004 至 2024 年各次總統選舉相對前一屆的泛藍得票率百分點與票數變化。2016 年降幅最大，2008 年明顯反彈，2020 年票數增加但得票率仍下降。</desc>
  <style>
    text {{ fill: #172033; font-family: -apple-system, BlinkMacSystemFont, "Noto Sans TC", sans-serif; font-size: 15px; }}
    .panel-title {{ font-size: 20px; font-weight: 600; }}
    .axis-label, .note {{ fill: #596579; font-size: 13px; }}
    .year, .value {{ font-variant-numeric: tabular-nums; }}
    .value {{ font-weight: 600; }}
    .center {{ text-anchor: middle; }}
    .end {{ text-anchor: end; }}
    .guide {{ stroke: #cbd5e1; stroke-width: 1; }}
    .zero {{ stroke: #475569; stroke-opacity: 0.72; stroke-width: 1; }}
    .bar.negative {{ fill: #c2413b; }}
    .bar.positive {{ fill: #2870a7; }}
  </style>
  <rect width="1200" height="500" fill="#ffffff" />
  <g aria-label="得票率增減">
    {share_panel}
  </g>
  <g aria-label="選票增減">
    {vote_panel}
  </g>
  <text class="note" x="20" y="478">2000 年為基準；每列皆與前一次總統選舉相比。負值與正值同時以方向、正負號及位置區分。</text>
</svg>
'''


def render_html(svg: str) -> str:
    """Wrap an SVG as a self-contained responsive HTML document."""
    return f'''<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <title>台北市泛藍總統票每屆增減</title>
  <style>
    body {{ margin: 0; padding: 24px; background: Canvas; color: CanvasText; }}
    svg {{ display: block; width: 100%; height: auto; max-width: 1200px; margin: 0 auto; }}
  </style>
</head>
<body>
{svg}</body>
</html>
'''
