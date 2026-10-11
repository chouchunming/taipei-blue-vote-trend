"""Write deterministic Taipei mayor analysis tables."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence

from .analysis import ElectionResult
from .chart import (
    render_html,
    render_mayor_bloc_svg,
    render_presidential_mayor_comparison_svg,
)
from .mayor import MayorAnalysisBundle, MayorElectionResult
from .outputs import write_csv, write_json


def write_mayor_artifacts(
    root: Path,
    analysis: MayorAnalysisBundle,
    source_manifest: Mapping[str, object],
) -> None:
    """Write mayor candidate, bloc, cohort, and provenance artifacts."""
    derived = root / "data" / "derived"
    scenarios = sorted(analysis.scenarios, key=lambda scenario: scenario.classification)

    write_csv(
        derived / "mayor_candidate_totals.csv",
        [
            "classification",
            "year",
            "candidate",
            "party",
            "bloc",
            "votes",
            "vote_share",
        ],
        [
            [
                row.classification,
                row.year,
                row.candidate,
                row.party,
                row.bloc,
                row.votes,
                f"{row.vote_share:.4f}",
            ]
            for scenario in scenarios
            for row in sorted(
                scenario.candidate_totals,
                key=lambda item: (item.year, item.candidate, item.party),
            )
        ],
    )

    write_csv(
        derived / "mayor_city_trend.csv",
        [
            "classification",
            "year",
            "valid_votes",
            "blue_votes",
            "blue_share",
            "green_votes",
            "green_share",
            "other_votes",
            "other_share",
        ],
        [
            [
                row.classification,
                row.year,
                row.valid_votes,
                row.blue_votes,
                f"{row.blue_share:.4f}",
                row.green_votes,
                f"{row.green_share:.4f}",
                row.other_votes,
                f"{row.other_share:.4f}",
            ]
            for scenario in scenarios
            for row in sorted(scenario.city, key=lambda item: item.year)
        ],
    )

    write_csv(
        derived / "mayor_bloc_deltas.csv",
        [
            "classification",
            "year",
            "blue_share_point_delta",
            "blue_vote_delta",
            "green_share_point_delta",
            "green_vote_delta",
            "other_share_point_delta",
            "other_vote_delta",
        ],
        [
            [
                row.classification,
                row.year,
                f"{row.blue_share_delta:.2f}",
                row.blue_vote_delta,
                f"{row.green_share_delta:.2f}",
                row.green_vote_delta,
                f"{row.other_share_delta:.2f}",
                row.other_vote_delta,
            ]
            for scenario in scenarios
            for row in sorted(scenario.deltas, key=lambda item: item.year)
        ],
    )

    volatility_rows = []
    for scenario in scenarios:
        valid_by_year = {row.year: row.valid_votes for row in scenario.city}
        for row in sorted(scenario.volatility, key=lambda item: item.year):
            volatility_rows.append(
                [
                    row.classification,
                    row.year,
                    f"{row.volatility_pp:.4f}",
                    row.vote_equivalent,
                    valid_by_year[row.year],
                ]
            )

    write_csv(
        derived / "mayor_electoral_volatility.csv",
        [
            "classification",
            "year",
            "volatility_pp",
            "vote_equivalent",
            "valid_votes",
        ],
        volatility_rows,
    )

    _write_cohort(
        derived / "mayor_deep_blue_cohort.csv",
        analysis.deep_blue,
        village_count=len(analysis.deep_blue_keys),
        bloc="blue",
    )
    _write_cohort(
        derived / "mayor_deep_green_cohort.csv",
        analysis.deep_green,
        village_count=len(analysis.deep_green_keys),
        bloc="green",
    )
    write_json(derived / "mayor_source_manifest.json", source_manifest)


def write_mayor_charts(
    root: Path,
    analysis: MayorAnalysisBundle,
    presidential_city: Sequence[ElectionResult],
) -> None:
    """Write mayor and cross-election comparison charts."""
    charts = root / "charts"
    charts.mkdir(parents=True, exist_ok=True)

    def bloc_rows(rows):
        return [
            (row.year, row.blue_share, row.green_share, row.other_share)
            for row in rows
        ]

    coalition_rows = bloc_rows(analysis.coalition.city)
    official_rows = bloc_rows(analysis.official_nomination.city)
    volatility_rows = [
        (row.year, row.volatility_pp, row.vote_equivalent)
        for row in analysis.coalition.volatility
    ]
    mayor_svg = render_mayor_bloc_svg(
        coalition_rows,
        official_rows,
        volatility_rows,
    )
    (charts / "taipei-mayor-bloc-and-volatility.svg").write_text(
        mayor_svg,
        encoding="utf-8",
    )
    (charts / "taipei-mayor-bloc-and-volatility.html").write_text(
        render_html(mayor_svg, title="2002–2022 臺北市長藍綠與選票波動"),
        encoding="utf-8",
    )

    comparison_svg = render_presidential_mayor_comparison_svg(
        bloc_rows(presidential_city),
        coalition_rows,
    )
    (charts / "taipei-presidential-mayor-comparison.svg").write_text(
        comparison_svg,
        encoding="utf-8",
    )
    (charts / "taipei-presidential-mayor-comparison.html").write_text(
        render_html(comparison_svg, title="臺北市總統與市長選舉得票結構比較"),
        encoding="utf-8",
    )


def _write_cohort(
    path: Path,
    rows: tuple[MayorElectionResult, ...],
    *,
    village_count: int,
    bloc: str,
) -> None:
    vote_field = f"{bloc}_votes"
    share_field = f"{bloc}_share"
    baseline = rows[0] if rows else None
    write_csv(
        path,
        [
            "classification",
            "year",
            "village_count",
            "valid_votes",
            vote_field,
            share_field,
            f"{bloc}_vote_change_from_2002",
            "share_point_change_from_2002",
        ],
        [
            [
                row.classification,
                row.year,
                village_count,
                row.valid_votes,
                getattr(row, vote_field),
                f"{getattr(row, share_field):.4f}",
                getattr(row, vote_field) - getattr(baseline, vote_field),
                f"{getattr(row, share_field) - getattr(baseline, share_field):.4f}",
            ]
            for row in sorted(rows, key=lambda item: item.year)
        ],
    )
