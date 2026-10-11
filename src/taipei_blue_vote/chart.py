"""Dependency-free SVG and standalone HTML chart rendering."""

from __future__ import annotations

from html import escape
from math import ceil, floor
from typing import Sequence

from .age_structure import AgeModel


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


def render_age_model_svg(model: AgeModel) -> str:
    """Render model fit and age-share effect sizes as a dependency-free SVG."""
    if not model.predictions:
        raise ValueError("age model chart requires predictions")
    shares = [
        value * 100
        for row in model.predictions
        for value in (row.observation.blue_share, row.predicted_blue_share)
    ]
    lower = floor((min(shares) - 2) / 5) * 5
    upper = ceil((max(shares) + 2) / 5) * 5
    if lower == upper:
        upper = lower + 5
    plot_left, plot_top, plot_size = 90.0, 110.0, 460.0

    def x_position(value: float) -> float:
        return _position(value * 100, (lower, upper), plot_left, plot_size)

    def y_position(value: float) -> float:
        return plot_top + plot_size - (value * 100 - lower) / (upper - lower) * plot_size

    points = "\n    ".join(
        f'<circle class="village-point" cx="{x_position(row.predicted_blue_share):.2f}" '
        f'cy="{y_position(row.observation.blue_share):.2f}" r="3.2">'
        f'<title>{escape(row.observation.district + row.observation.village)}：'
        f'實際 {row.observation.blue_share * 100:.1f}%／預測 {row.predicted_blue_share * 100:.1f}%</title></circle>'
        for row in model.predictions
    )
    ticks = []
    for index in range(6):
        value = lower + (upper - lower) * index / 5
        x = _position(value, (lower, upper), plot_left, plot_size)
        y = plot_top + plot_size - (value - lower) / (upper - lower) * plot_size
        ticks.extend(
            [
                f'<line class="grid" x1="{x:.2f}" y1="{plot_top:g}" x2="{x:.2f}" y2="{plot_top + plot_size:g}" />',
                f'<line class="grid" x1="{plot_left:g}" y1="{y:.2f}" x2="{plot_left + plot_size:g}" y2="{y:.2f}" />',
                f'<text class="tick center" x="{x:.2f}" y="{plot_top + plot_size + 26:g}">{value:.0f}%</text>',
                f'<text class="tick end" x="{plot_left - 12:g}" y="{y + 5:.2f}">{value:.0f}%</text>',
            ]
        )

    effects = {row.name: row.effect_for_10pp for row in model.coefficients}
    young = effects.get("young_share")
    senior = effects.get("senior_share")
    if young is None or senior is None:
        raise ValueError("age model chart requires young_share and senior_share effects")
    effect_limit = max(1.0, abs(young), abs(senior)) * 1.15
    effect_zero = 925.0
    effect_half_width = 195.0

    def effect_bar(label: str, value: float, y: float) -> str:
        width = abs(value) / effect_limit * effect_half_width
        x = effect_zero if value >= 0 else effect_zero - width
        color_class = "positive" if value >= 0 else "negative"
        return (
            f'<text class="effect-label" x="680" y="{y - 12:g}">{escape(label)}</text>'
            f'<rect class="effect {color_class}" x="{x:.2f}" y="{y:g}" width="{width:.2f}" height="30" rx="4" />'
            f'<text class="effect-value {color_class}" x="{effect_zero:g}" y="{y + 53:g}">{_signed(value, 2)} pp</text>'
        )

    tick_markup = "\n    ".join(ticks)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 650" role="img" aria-labelledby="age-title age-desc">
  <title id="age-title">臺北市 2024 里級人口年齡結構模型</title>
  <desc id="age-desc">比較各里侯友宜得票率的實際值與年齡結構加行政區固定效果模型的預測值，並顯示青年及長者人口占比增加十個百分點的模型關聯。</desc>
  <style>
    text {{ fill: #172033; font-family: -apple-system, BlinkMacSystemFont, "Noto Sans TC", sans-serif; font-size: 15px; }}
    .title {{ font-size: 25px; font-weight: 700; }}
    .subtitle, .tick, .note {{ fill: #596579; font-size: 13px; }}
    .axis-title, .effect-label {{ font-size: 16px; font-weight: 600; }}
    .center {{ text-anchor: middle; }}
    .end {{ text-anchor: end; }}
    .grid {{ stroke: #e2e8f0; stroke-width: 1; }}
    .identity {{ stroke: #52627a; stroke-width: 2; stroke-dasharray: 7 6; }}
    .village-point {{ fill: #2870a7; fill-opacity: 0.46; stroke: #174668; stroke-width: 0.6; }}
    .effect.negative {{ fill: #c2413b; }}
    .effect.positive {{ fill: #2870a7; }}
    .effect-value {{ font-size: 22px; font-weight: 700; text-anchor: middle; }}
    .effect-value.negative {{ fill: #a33531; }}
    .effect-value.positive {{ fill: #1f5d8b; }}
    .zero {{ stroke: #475569; stroke-width: 1.2; }}
  </style>
  <rect width="1200" height="650" fill="#ffffff" />
  <text class="title" x="50" y="48">臺北市 2024 里級年齡結構模型</text>
  <text class="subtitle" x="50" y="76">{len(model.predictions)} 里加權生態迴歸；R² = {model.weighted_r2:.3f}；每點為一里</text>
  <g aria-label="實際與預測得票率">
    {tick_markup}
    <line class="identity" x1="{plot_left:g}" y1="{plot_top + plot_size:g}" x2="{plot_left + plot_size:g}" y2="{plot_top:g}" />
    {points}
    <text class="axis-title center" x="{plot_left + plot_size / 2:g}" y="620">模型預測侯友宜得票率</text>
    <text class="axis-title" transform="translate(26 {plot_top + plot_size / 2:g}) rotate(-90)" text-anchor="middle">實際侯友宜得票率</text>
  </g>
  <g aria-label="年齡占比模型關聯">
    <text class="axis-title" x="680" y="138">其他變數相同時的模型關聯</text>
    <text class="subtitle" x="680" y="165">人口占比每增加 10 個百分點</text>
    <line class="zero" x1="{effect_zero:g}" y1="196" x2="{effect_zero:g}" y2="462" />
    {effect_bar("青年占比 +10pp（20–39 歲）", young, 230)}
    {effect_bar("長者占比 +10pp（65 歲以上）", senior, 370)}
    <text class="note" x="680" y="505">模型含行政區固定效果，以有效票加權。</text>
    <text class="note" x="680" y="532">這是里級關聯，不是個人投票行為或因果效果。</text>
  </g>
</svg>
'''


def render_html(svg: str, *, title: str = "台北市泛藍總統票每屆增減") -> str:
    """Wrap an SVG as a self-contained responsive HTML document."""
    return f'''<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <title>{escape(title)}</title>
  <style>
    body {{ margin: 0; padding: 24px; background: Canvas; color: CanvasText; }}
    svg {{ display: block; width: 100%; height: auto; max-width: 1200px; margin: 0 auto; }}
  </style>
</head>
<body>
{svg}</body>
</html>
'''
