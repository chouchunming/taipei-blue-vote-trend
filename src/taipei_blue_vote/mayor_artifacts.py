"""Write deterministic Taipei mayor analysis tables."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

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
