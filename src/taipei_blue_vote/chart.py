"""Dependency-free SVG and standalone HTML chart rendering."""

from __future__ import annotations

from html import escape
from math import ceil, floor
from typing import Sequence

from .age_structure import AgeModel


DeltaRow = tuple[int, float, int]
BlocShareRow = tuple[int, float, float, float]
VolatilityRow = tuple[int, float, int]

_BLOC_SERIES = (
    ("泛藍", 1, "blue"),
    ("泛綠", 2, "green"),
    ("其他候選人", 3, "other"),
)


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


def render_bloc_svg(
    bloc_rows: Sequence[BlocShareRow],
    volatility_rows: Sequence[VolatilityRow],
) -> str:
    """Render bloc shares and election-to-election three-bloc volatility."""
    if len(bloc_rows) < 2 or len(volatility_rows) != len(bloc_rows) - 1:
        raise ValueError("bloc chart requires one volatility row per election transition")

    share_left, share_top, share_width, share_height = 90.0, 120.0, 1020.0, 250.0
    share_max = 70.0
    share_step = share_width / (len(bloc_rows) - 1)

    def share_x(index: int) -> float:
        return share_left + index * share_step

    def share_y(value: float) -> float:
        return share_top + share_height - value / share_max * share_height

    series = (
        ("泛藍", 1, "blue"),
        ("泛綠", 2, "green"),
        ("其他候選人", 3, "other"),
    )
    share_series = []
    for label, value_index, color_class in series:
        points = " ".join(
            f"{share_x(index):.2f},{share_y(row[value_index]):.2f}"
            for index, row in enumerate(bloc_rows)
        )
        circles = "".join(
            f'<circle class="share-point {color_class}" cx="{share_x(index):.2f}" '
            f'cy="{share_y(row[value_index]):.2f}" r="4.5"><title>{row[0]} {label} '
            f'{row[value_index]:.2f}%</title></circle>'
            for index, row in enumerate(bloc_rows)
        )
        share_series.append(
            f'<polyline class="share-line {color_class}" points="{points}" />{circles}'
        )

    share_grid = []
    for value in (0, 20, 40, 60, 70):
        y = share_y(value)
        share_grid.extend(
            [
                f'<line class="grid" x1="{share_left:g}" y1="{y:.2f}" x2="{share_left + share_width:g}" y2="{y:.2f}" />',
                f'<text class="tick end" x="{share_left - 14:g}" y="{y + 5:.2f}">{value}%</text>',
            ]
        )
    for index, row in enumerate(bloc_rows):
        x = share_x(index)
        share_grid.append(
            f'<text class="tick center" x="{x:.2f}" y="{share_top + share_height + 28:g}">{row[0]}</text>'
        )

    last = bloc_rows[-1]
    legend = "".join(
        f'<g transform="translate({760 + index * 135} 71)">'
        f'<line class="legend-line {color_class}" x1="0" y1="0" x2="24" y2="0" />'
        f'<text class="legend" x="32" y="5">{label} {last[value_index]:.2f}%</text></g>'
        for index, (label, value_index, color_class) in enumerate(series)
    )

    volatility_left, volatility_top = 110.0, 470.0
    volatility_width, volatility_height = 980.0, 145.0
    volatility_max = max(1.0, max(row[1] for row in volatility_rows) * 1.12)
    bar_slot = volatility_width / len(volatility_rows)
    bar_width = min(90.0, bar_slot * 0.56)
    bars = []
    for index, (year, value, vote_equivalent) in enumerate(volatility_rows):
        x = volatility_left + index * bar_slot + (bar_slot - bar_width) / 2
        height = value / volatility_max * volatility_height
        y = volatility_top + volatility_height - height
        bars.extend(
            [
                f'<rect class="volatility-bar" x="{x:.2f}" y="{y:.2f}" width="{bar_width:.2f}" height="{height:.2f}" rx="5"><title>{year} {value:.2f} pp／{vote_equivalent:,} 票等值</title></rect>',
                f'<text class="bar-value center" x="{x + bar_width / 2:.2f}" y="{y - 10:.2f}">{value:.2f} pp</text>',
                f'<text class="tick center" x="{x + bar_width / 2:.2f}" y="{volatility_top + volatility_height + 24:g}">{year}</text>',
                f'<text class="vote-note center" x="{x + bar_width / 2:.2f}" y="{volatility_top + volatility_height + 43:g}">{vote_equivalent:,} 票等值</text>',
            ]
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 720" role="img" aria-labelledby="bloc-title bloc-desc">
  <title id="bloc-title">臺北市 2000–2024 藍綠與選票波動</title>
  <desc id="bloc-desc">上圖為泛藍、泛綠及其他候選人占有效票比例；下圖為相鄰選舉三類選票的最低淨移動規模。其他候選人票不等於所有中間選民，波動也不是可識別的個人轉投人數。</desc>
  <style>
    text {{ fill: #172033; font-family: -apple-system, BlinkMacSystemFont, "Noto Sans TC", sans-serif; font-size: 14px; }}
    .title {{ font-size: 25px; font-weight: 700; }}
    .panel-title {{ font-size: 18px; font-weight: 650; }}
    .subtitle, .tick, .vote-note, .note {{ fill: #596579; font-size: 12px; }}
    .center {{ text-anchor: middle; }}
    .end {{ text-anchor: end; }}
    .grid {{ stroke: #e2e8f0; stroke-width: 1; }}
    .share-line {{ fill: none; stroke-width: 3; stroke-linejoin: round; stroke-linecap: round; }}
    .share-line.blue, .share-point.blue, .legend-line.blue {{ stroke: #2870a7; }}
    .share-line.green, .share-point.green, .legend-line.green {{ stroke: #2f855a; }}
    .share-line.other, .share-point.other, .legend-line.other {{ stroke: #d97706; }}
    .share-point.blue {{ fill: #2870a7; }}
    .share-point.green {{ fill: #2f855a; }}
    .share-point.other {{ fill: #d97706; }}
    .legend-line {{ stroke-width: 4; }}
    .legend {{ font-weight: 600; }}
    .volatility-bar {{ fill: #7562a8; }}
    .bar-value {{ font-size: 14px; font-weight: 700; }}
  </style>
  <rect width="1200" height="720" fill="#ffffff" />
  <text class="title" x="50" y="42">臺北市 2000–2024 藍綠與選票波動</text>
  <text class="subtitle" x="50" y="70">票數與得票率是不同指標；波動票量為以當屆有效票換算的等值。</text>
  {legend}
  <g aria-label="三類候選人得票率">
    <text class="panel-title" x="50" y="105">候選人類別得票率</text>
    {''.join(share_grid)}
    {''.join(share_series)}
  </g>
  <g aria-label="最低淨移動規模">
    <text class="panel-title" x="50" y="440">相對前一屆的最低淨移動規模</text>
    <line class="grid" x1="{volatility_left:g}" y1="{volatility_top + volatility_height:g}" x2="{volatility_left + volatility_width:g}" y2="{volatility_top + volatility_height:g}" />
    {''.join(bars)}
  </g>
  <text class="note" x="50" y="700">「其他候選人」是可觀察選票類別，不是所有中間選民；波動是聚合淨變化，也可能包含投票率與選民結構變化。</text>
</svg>
'''


def render_mayor_bloc_svg(
    coalition_rows: Sequence[BlocShareRow],
    official_rows: Sequence[BlocShareRow],
    volatility_rows: Sequence[VolatilityRow],
) -> str:
    """Render mayor bloc shares under two classifications plus volatility."""
    if len(coalition_rows) < 2 or len(official_rows) != len(coalition_rows):
        raise ValueError("mayor chart requires matching coalition and official rows")
    if [row[0] for row in coalition_rows] != [row[0] for row in official_rows]:
        raise ValueError("mayor chart classifications must contain the same years")
    if len(volatility_rows) != len(coalition_rows) - 1:
        raise ValueError("mayor chart requires one volatility row per transition")

    plot_left, plot_top, plot_width, plot_height = 92.0, 154.0, 1010.0, 280.0
    share_max = 70.0
    step = plot_width / (len(coalition_rows) - 1)

    def x_position(index: int) -> float:
        return plot_left + index * step

    def y_position(value: float) -> float:
        return plot_top + plot_height - value / share_max * plot_height

    grid = []
    for value in (0, 10, 20, 30, 40, 50, 60, 70):
        y = y_position(value)
        grid.extend(
            (
                f'<line class="grid" x1="{plot_left:g}" y1="{y:.2f}" x2="{plot_left + plot_width:g}" y2="{y:.2f}" />',
                f'<text class="tick end" x="{plot_left - 14:g}" y="{y + 5:.2f}">{value}%</text>',
            )
        )
    for index, row in enumerate(coalition_rows):
        grid.append(
            f'<text class="tick center" x="{x_position(index):.2f}" y="{plot_top + plot_height + 28:g}">{row[0]}</text>'
        )

    lines = []
    for label, value_index, color_class in _BLOC_SERIES:
        coalition_points = " ".join(
            f"{x_position(index):.2f},{y_position(row[value_index]):.2f}"
            for index, row in enumerate(coalition_rows)
        )
        official_points = " ".join(
            f"{x_position(index):.2f},{y_position(row[value_index]):.2f}"
            for index, row in enumerate(official_rows)
        )
        coalition_dots = "".join(
            f'<circle class="mayor-point coalition {color_class}" cx="{x_position(index):.2f}" '
            f'cy="{y_position(row[value_index]):.2f}" r="4.5"><title>{row[0]} '
            f'聯盟口徑 {label} {row[value_index]:.2f}%</title></circle>'
            for index, row in enumerate(coalition_rows)
        )
        official_dots = "".join(
            f'<circle class="mayor-point official {color_class}" cx="{x_position(index):.2f}" '
            f'cy="{y_position(row[value_index]):.2f}" r="3.2"><title>{row[0]} '
            f'官方提名口徑 {label} {row[value_index]:.2f}%</title></circle>'
            for index, row in enumerate(official_rows)
        )
        lines.extend(
            (
                f'<polyline class="mayor-line coalition {color_class}" points="{coalition_points}" />{coalition_dots}',
                f'<polyline class="mayor-line official {color_class}" points="{official_points}" />{official_dots}',
            )
        )

    volatility_left, volatility_top = 125.0, 555.0
    volatility_width, volatility_height = 945.0, 125.0
    volatility_max = max(1.0, max(row[1] for row in volatility_rows) * 1.18)
    slot = volatility_width / len(volatility_rows)
    bar_width = min(92.0, slot * 0.52)
    bars = []
    for index, (year, value, vote_equivalent) in enumerate(volatility_rows):
        x = volatility_left + index * slot + (slot - bar_width) / 2
        height = value / volatility_max * volatility_height
        y = volatility_top + volatility_height - height
        bars.extend(
            (
                f'<rect class="mayor-volatility-bar" x="{x:.2f}" y="{y:.2f}" width="{bar_width:.2f}" height="{height:.2f}" rx="5"><title>{year} {value:.2f} pp／{vote_equivalent:,} 票等值</title></rect>',
                f'<text class="bar-value center" x="{x + bar_width / 2:.2f}" y="{y - 9:.2f}">{value:.2f} pp</text>',
                f'<text class="tick center" x="{x + bar_width / 2:.2f}" y="{volatility_top + volatility_height + 23:g}">{year}</text>',
                f'<text class="vote-note center" x="{x + bar_width / 2:.2f}" y="{volatility_top + volatility_height + 42:g}">{vote_equivalent:,} 票等值</text>',
            )
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 800" role="img" aria-labelledby="mayor-title mayor-desc">
  <title id="mayor-title">2002–2022 臺北市長藍綠與選票波動</title>
  <desc id="mayor-desc">上圖以實線呈現聯盟口徑，以較細虛線呈現官方提名口徑的泛藍、泛綠及其他候選人得票率；下圖呈現聯盟口徑相鄰選舉的最低淨移動規模。2014 年兩種分類因民進黨支持柯文哲但未正式提名候選人而明顯分歧。</desc>
  <style>
    text {{ fill: #172033; font-family: -apple-system, BlinkMacSystemFont, "Noto Sans TC", sans-serif; font-size: 14px; }}
    .title {{ font-size: 25px; font-weight: 500; }}
    .panel-title {{ font-size: 18px; font-weight: 500; }}
    .subtitle, .tick, .vote-note, .note {{ fill: #596579; font-size: 12px; }}
    .center {{ text-anchor: middle; }}
    .end {{ text-anchor: end; }}
    .grid {{ stroke: #e2e8f0; stroke-width: 1; }}
    .mayor-line {{ fill: none; stroke-linejoin: round; stroke-linecap: round; }}
    .mayor-line.coalition {{ stroke-width: 3.5; }}
    .mayor-line.official {{ stroke-width: 2; stroke-dasharray: 8 6; }}
    .mayor-line.blue, .mayor-point.blue, .legend-line.blue {{ stroke: #2870a7; }}
    .mayor-line.green, .mayor-point.green, .legend-line.green {{ stroke: #2f855a; }}
    .mayor-line.other, .mayor-point.other, .legend-line.other {{ stroke: #d97706; }}
    .mayor-point.blue {{ fill: #2870a7; }}
    .mayor-point.green {{ fill: #2f855a; }}
    .mayor-point.other {{ fill: #d97706; }}
    .mayor-point.official {{ fill: #ffffff; stroke-width: 2; }}
    .legend-line {{ stroke-width: 4; }}
    .style-solid {{ stroke: #475569; stroke-width: 3.5; }}
    .style-dashed {{ stroke: #475569; stroke-width: 2; stroke-dasharray: 8 6; }}
    .legend {{ font-weight: 500; }}
    .mayor-volatility-bar {{ fill: #7562a8; }}
    .bar-value {{ font-weight: 500; }}
    .annotation {{ fill: #7c4d13; font-size: 12px; font-weight: 500; }}
  </style>
  <rect width="1200" height="800" fill="#ffffff" />
  <text class="title" x="50" y="43">2002–2022 臺北市長藍綠與選票波動</text>
  <text class="subtitle" x="50" y="70">同一批官方票數，以兩種候選人分類檢查聯盟邊界的敏感度。</text>
  <g aria-label="顏色圖例">
    <g transform="translate(655 45)"><line class="legend-line blue" x1="0" y1="0" x2="24" y2="0" /><text class="legend" x="32" y="5">泛藍</text></g>
    <g transform="translate(760 45)"><line class="legend-line green" x1="0" y1="0" x2="24" y2="0" /><text class="legend" x="32" y="5">泛綠</text></g>
    <g transform="translate(865 45)"><line class="legend-line other" x1="0" y1="0" x2="24" y2="0" /><text class="legend" x="32" y="5">其他候選人</text></g>
  </g>
  <g aria-label="線型圖例">
    <g transform="translate(655 76)"><line class="style-solid" x1="0" y1="0" x2="30" y2="0" /><text x="39" y="5">聯盟口徑</text></g>
    <g transform="translate(815 76)"><line class="style-dashed" x1="0" y1="0" x2="30" y2="0" /><text x="39" y="5">官方提名口徑</text></g>
  </g>
  <g aria-label="市長候選人類別得票率">
    <text class="panel-title" x="50" y="125">候選人類別得票率</text>
    {''.join(grid)}
    {''.join(lines)}
    <text class="annotation center" x="{x_position(3):.2f}" y="{plot_top + plot_height + 51:g}">2014 分類差異：柯文哲列入聯盟泛綠，官方提名口徑列為其他</text>
  </g>
  <g aria-label="聯盟口徑最低淨移動規模">
    <text class="panel-title" x="50" y="525">聯盟口徑：相對前一屆的最低淨移動規模</text>
    <line class="grid" x1="{volatility_left:g}" y1="{volatility_top + volatility_height:g}" x2="{volatility_left + volatility_width:g}" y2="{volatility_top + volatility_height:g}" />
    {''.join(bars)}
  </g>
  <text class="note" x="50" y="778">「其他候選人」不是所有中間選民；最低淨移動規模是三類聚合得票率變化的一半，也包含投票率與選民結構變化。</text>
</svg>
'''


def render_presidential_mayor_comparison_svg(
    presidential_rows: Sequence[BlocShareRow],
    mayor_rows: Sequence[BlocShareRow],
) -> str:
    """Render presidential and mayor bloc trends as shared-scale panels."""
    if len(presidential_rows) < 2 or len(mayor_rows) < 2:
        raise ValueError("comparison chart requires at least two elections per panel")

    plot_top, plot_height, plot_width = 145.0, 350.0, 455.0
    share_max = 70.0

    def render_panel(
        rows: Sequence[BlocShareRow],
        *,
        left: float,
        title: str,
        accessible_label: str,
    ) -> str:
        step = plot_width / (len(rows) - 1)

        def x_position(index: int) -> float:
            return left + index * step

        def y_position(value: float) -> float:
            return plot_top + plot_height - value / share_max * plot_height

        parts = [
            f'<text class="panel-title" x="{left:g}" y="112">{escape(title)}</text>',
        ]
        for value in (0, 10, 20, 30, 40, 50, 60, 70):
            y = y_position(value)
            parts.append(
                f'<line class="grid" x1="{left:g}" y1="{y:.2f}" x2="{left + plot_width:g}" y2="{y:.2f}" />'
            )
            if left < 100:
                parts.append(
                    f'<text class="tick end" x="{left - 12:g}" y="{y + 5:.2f}">{value}%</text>'
                )
        for index, row in enumerate(rows):
            parts.append(
                f'<text class="tick center" x="{x_position(index):.2f}" y="{plot_top + plot_height + 27:g}">{row[0]}</text>'
            )
        for label, value_index, color_class in _BLOC_SERIES:
            points = " ".join(
                f"{x_position(index):.2f},{y_position(row[value_index]):.2f}"
                for index, row in enumerate(rows)
            )
            parts.append(
                f'<polyline class="comparison-line {color_class}" points="{points}" />'
            )
            parts.extend(
                f'<circle class="comparison-point {color_class}" cx="{x_position(index):.2f}" cy="{y_position(row[value_index]):.2f}" r="4.5"><title>{row[0]} {label} {row[value_index]:.2f}%</title></circle>'
                for index, row in enumerate(rows)
            )
        last = rows[-1]
        parts.append(
            f'<text class="last-values" x="{left:g}" y="{plot_top + plot_height + 61:g}">{last[0]}：泛藍 {last[1]:.2f}%　泛綠 {last[2]:.2f}%　其他 {last[3]:.2f}%</text>'
        )
        return (
            f'<g class="comparison-panel" aria-label="{escape(accessible_label)}">'
            + "".join(parts)
            + "</g>"
        )

    presidential_panel = render_panel(
        presidential_rows,
        left=70.0,
        title="總統選舉 2000–2024",
        accessible_label="總統選舉候選人類別得票率",
    )
    mayor_panel = render_panel(
        mayor_rows,
        left=675.0,
        title="市長選舉 2002–2022",
        accessible_label="市長選舉聯盟口徑候選人類別得票率",
    )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 620" role="img" aria-labelledby="comparison-title comparison-desc">
  <title id="comparison-title">臺北市總統與市長選舉候選人類別得票率比較</title>
  <desc id="comparison-desc">總統選舉 2000 至 2024 年與市長選舉 2002 至 2022 年分成兩個不相連的面板；兩個面板使用相同的 0–70% 縱軸，並以相同顏色表示泛藍、泛綠和其他候選人。市長選舉採聯盟口徑。</desc>
  <style>
    text {{ fill: #172033; font-family: -apple-system, BlinkMacSystemFont, "Noto Sans TC", sans-serif; font-size: 14px; }}
    .title {{ font-size: 25px; font-weight: 500; }}
    .panel-title {{ font-size: 18px; font-weight: 500; }}
    .subtitle, .tick, .note {{ fill: #596579; font-size: 12px; }}
    .center {{ text-anchor: middle; }}
    .end {{ text-anchor: end; }}
    .grid {{ stroke: #e2e8f0; stroke-width: 1; }}
    .comparison-line {{ fill: none; stroke-width: 3.2; stroke-linejoin: round; stroke-linecap: round; }}
    .comparison-line.blue, .comparison-point.blue, .legend-line.blue {{ stroke: #2870a7; }}
    .comparison-line.green, .comparison-point.green, .legend-line.green {{ stroke: #2f855a; }}
    .comparison-line.other, .comparison-point.other, .legend-line.other {{ stroke: #d97706; }}
    .comparison-point.blue {{ fill: #2870a7; }}
    .comparison-point.green {{ fill: #2f855a; }}
    .comparison-point.other {{ fill: #d97706; }}
    .legend-line {{ stroke-width: 4; }}
    .legend, .last-values {{ font-weight: 500; }}
    .last-values {{ font-size: 12px; }}
  </style>
  <rect width="1200" height="620" fill="#ffffff" />
  <text class="title" x="50" y="43">臺北市總統與市長選舉得票結構比較</text>
  <text class="subtitle" x="50" y="70">兩種選舉分開連線；市長選舉採聯盟口徑，兩圖共用 0–70% 比例尺。</text>
  <g aria-label="候選人類別圖例">
    <g transform="translate(745 46)"><line class="legend-line blue" x1="0" y1="0" x2="24" y2="0" /><text class="legend" x="32" y="5">泛藍</text></g>
    <g transform="translate(850 46)"><line class="legend-line green" x1="0" y1="0" x2="24" y2="0" /><text class="legend" x="32" y="5">泛綠</text></g>
    <g transform="translate(955 46)"><line class="legend-line other" x1="0" y1="0" x2="24" y2="0" /><text class="legend" x="32" y="5">其他候選人</text></g>
  </g>
  {presidential_panel}
  {mayor_panel}
  <text class="note" x="50" y="596">線段只連接同一選舉類型的相鄰年份；「其他候選人」是選票分類，不等同所有中間選民。</text>
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
