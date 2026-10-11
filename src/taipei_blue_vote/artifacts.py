"""Write the compact, committed analysis artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence

from .age_structure import AgeModel
from .analysis import estimate_young_votes
from .chart import render_age_model_svg, render_bloc_svg, render_html, render_svg
from .outputs import write_csv, write_json
from .pipeline import AnalysisBundle, ProxyResult


YOUNG_ELIGIBLE_20_39 = 571_536
YOUNG_TURNOUT = 0.715
YOUNG_SUPPORT_RANGE = (0.135, 0.15, 0.16)


def write_artifacts(
    root: Path,
    analysis: AnalysisBundle,
    proxies: Sequence[ProxyResult],
    source_manifest: Mapping[str, object],
) -> None:
    """Write derived CSV/JSON plus SVG and standalone HTML charts."""
    derived = root / "data" / "derived"
    charts = root / "charts"
    baseline_city = analysis.city[0]
    baseline_cohort = analysis.cohort[0]

    write_csv(
        derived / "city_trend.csv",
        [
            "year",
            "valid_votes",
            "blue_votes",
            "blue_share",
            "green_votes",
            "green_share",
            "other_votes",
            "other_share",
            "ko_votes",
            "ko_share",
            "blue_vote_change_from_2000",
            "blue_share_point_change_from_2000",
            "green_vote_change_from_2000",
            "green_share_point_change_from_2000",
            "other_vote_change_from_2000",
            "other_share_point_change_from_2000",
        ],
        [
            [
                row.year,
                row.valid_votes,
                row.blue_votes,
                f"{row.blue_share:.4f}",
                row.green_votes,
                f"{row.green_share:.4f}",
                row.other_votes,
                f"{row.other_share:.4f}",
                row.ko_votes,
                f"{row.ko_votes / row.valid_votes * 100:.4f}",
                row.blue_votes - baseline_city.blue_votes,
                f"{row.blue_share - baseline_city.blue_share:.4f}",
                row.green_votes - baseline_city.green_votes,
                f"{row.green_share - baseline_city.green_share:.4f}",
                row.other_votes - baseline_city.other_votes,
                f"{row.other_share - baseline_city.other_share:.4f}",
            ]
            for row in analysis.city
        ],
    )

    green_cohort_rows: list[list[object]] = []
    if analysis.green_cohort:
        baseline_green_cohort = analysis.green_cohort[0]
        green_cohort_rows = [
            [
                row.year,
                len(analysis.green_cohort_keys),
                row.valid_votes,
                row.green_votes,
                f"{row.green_share:.4f}",
                row.green_votes - baseline_green_cohort.green_votes,
                f"{row.green_share - baseline_green_cohort.green_share:.4f}",
            ]
            for row in analysis.green_cohort
        ]

    write_csv(
        derived / "deep_green_cohort.csv",
        [
            "year",
            "village_count",
            "valid_votes",
            "green_votes",
            "green_share",
            "green_vote_change_from_2000",
            "share_point_change_from_2000",
        ],
        green_cohort_rows,
    )

    write_csv(
        derived / "deep_blue_cohort.csv",
        [
            "year",
            "village_count",
            "valid_votes",
            "blue_votes",
            "blue_share",
            "blue_vote_change_from_2000",
            "share_point_change_from_2000",
        ],
        [
            [
                row.year,
                len(analysis.cohort_keys),
                row.valid_votes,
                row.blue_votes,
                f"{row.blue_share:.4f}",
                row.blue_votes - baseline_cohort.blue_votes,
                f"{row.blue_share - baseline_cohort.blue_share:.4f}",
            ]
            for row in analysis.cohort
        ],
    )

    write_csv(
        derived / "election_deltas.csv",
        ["year", "share_point_delta", "blue_vote_delta"],
        [[year, f"{share_delta:.2f}", vote_delta] for year, share_delta, vote_delta in analysis.deltas],
    )

    write_csv(
        derived / "bloc_deltas.csv",
        [
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
                row.year,
                f"{row.blue_share_delta:.2f}",
                row.blue_vote_delta,
                f"{row.green_share_delta:.2f}",
                row.green_vote_delta,
                f"{row.other_share_delta:.2f}",
                row.other_vote_delta,
            ]
            for row in analysis.bloc_deltas
        ],
    )

    valid_by_year = {row.year: row.valid_votes for row in analysis.city}
    write_csv(
        derived / "electoral_volatility.csv",
        ["year", "volatility_pp", "vote_equivalent", "valid_votes"],
        [
            [
                row.year,
                f"{row.volatility_pp:.4f}",
                row.vote_equivalent,
                valid_by_year[row.year],
            ]
            for row in analysis.volatility
        ],
    )

    write_csv(
        derived / "military_village_proxies.csv",
        [
            "proxy_name",
            "district",
            "village",
            "year",
            "valid_votes",
            "blue_votes",
            "blue_share",
            "continuously_comparable_from_2000",
        ],
        [
            [
                row.proxy_name,
                row.district,
                row.village,
                row.year,
                row.valid_votes,
                row.blue_votes,
                f"{row.blue_share:.4f}",
                str(row.continuously_comparable).lower(),
            ]
            for row in proxies
        ],
    )

    low, central, high = estimate_young_votes(
        YOUNG_ELIGIBLE_20_39,
        YOUNG_TURNOUT,
        *YOUNG_SUPPORT_RANGE,
    )
    city_loss = baseline_city.blue_votes - analysis.city[-1].blue_votes
    write_csv(
        derived / "young_replacement.csv",
        [
            "eligible_age_20_39",
            "turnout_assumption",
            "estimated_ballots",
            "hou_support_low",
            "hou_support_central",
            "hou_support_high",
            "estimated_hou_votes_low",
            "estimated_hou_votes_central",
            "estimated_hou_votes_high",
            "citywide_blue_vote_loss_2000_2024",
            "offset_share_low",
            "offset_share_central",
            "offset_share_high",
        ],
        [
            [
                YOUNG_ELIGIBLE_20_39,
                f"{YOUNG_TURNOUT:.3f}",
                round(YOUNG_ELIGIBLE_20_39 * YOUNG_TURNOUT),
                *(f"{rate:.3f}" for rate in YOUNG_SUPPORT_RANGE),
                low,
                central,
                high,
                city_loss,
                *_offsets((low, central, high), city_loss),
            ]
        ],
    )

    write_json(derived / "source_manifest.json", source_manifest)

    svg = render_svg(analysis.deltas)
    charts.mkdir(parents=True, exist_ok=True)
    (charts / "taipei-blue-election-deltas.svg").write_text(svg, encoding="utf-8")
    (charts / "taipei-blue-election-deltas.html").write_text(
        render_html(svg), encoding="utf-8"
    )

    bloc_svg = render_bloc_svg(
        [
            (row.year, row.blue_share, row.green_share, row.other_share)
            for row in analysis.city
        ],
        [
            (row.year, row.volatility_pp, row.vote_equivalent)
            for row in analysis.volatility
        ],
    )
    (charts / "taipei-bloc-and-volatility.svg").write_text(
        bloc_svg,
        encoding="utf-8",
    )
    (charts / "taipei-bloc-and-volatility.html").write_text(
        render_html(bloc_svg, title="臺北市藍綠與選票波動"),
        encoding="utf-8",
    )


def _offsets(estimates: Sequence[int], city_loss: int) -> tuple[str, str, str]:
    if city_loss <= 0:
        return ("", "", "")
    return tuple(f"{estimate / city_loss:.4f}" for estimate in estimates)


def write_age_artifacts(
    root: Path,
    model: AgeModel,
    *,
    coverage: tuple[int, int],
    source_manifest: Mapping[str, object],
) -> None:
    """Write village predictions, model coefficients, and population provenance."""
    derived = root / "data" / "derived"
    write_csv(
        derived / "village_age_structure_2024.csv",
        [
            "district",
            "village",
            "population",
            "age_20_39_share",
            "age_40_64_share",
            "age_65_plus_share",
            "age_75_plus_share",
            "valid_votes",
            "blue_votes",
            "actual_blue_share",
            "predicted_blue_votes",
            "predicted_blue_share",
            "vote_residual",
            "residual_percentage_points",
            "actual_rank",
            "predicted_rank",
        ],
        [
            [
                prediction.observation.district,
                prediction.observation.village,
                prediction.observation.population,
                f"{prediction.observation.young_share * 100:.4f}",
                f"{prediction.observation.middle_share * 100:.4f}",
                f"{prediction.observation.senior_share * 100:.4f}",
                f"{prediction.observation.age_75_plus_share * 100:.4f}",
                prediction.observation.valid_votes,
                prediction.observation.blue_votes,
                f"{prediction.observation.blue_share * 100:.4f}",
                round(prediction.predicted_blue_share * prediction.observation.valid_votes),
                f"{prediction.predicted_blue_share * 100:.4f}",
                prediction.observation.blue_votes
                - round(prediction.predicted_blue_share * prediction.observation.valid_votes),
                f"{prediction.residual * 100:.4f}",
                prediction.actual_rank,
                prediction.predicted_rank,
            ]
            for prediction in model.predictions
        ],
    )

    matched, total = coverage
    write_csv(
        derived / "age_model_2024.csv",
        [
            "term",
            "coefficient",
            "effect_for_10pp",
            "weighted_r2",
            "baseline_district",
            "observation_count",
            "matched_vote_villages",
            "total_vote_villages",
            "match_rate",
        ],
        [
            [
                coefficient.name,
                f"{coefficient.coefficient:.6f}",
                "" if coefficient.effect_for_10pp is None else f"{coefficient.effect_for_10pp:.4f}",
                f"{model.weighted_r2:.6f}",
                model.baseline_district,
                len(model.predictions),
                matched,
                total,
                f"{matched / total:.6f}",
            ]
            for coefficient in model.coefficients
        ],
    )
    write_json(derived / "age_source_manifest.json", source_manifest)

    charts = root / "charts"
    charts.mkdir(parents=True, exist_ok=True)
    svg = render_age_model_svg(model)
    (charts / "village-age-model-2024.svg").write_text(svg, encoding="utf-8")
    (charts / "village-age-model-2024.html").write_text(
        render_html(svg, title="臺北市 2024 里級年齡結構模型"),
        encoding="utf-8",
    )
