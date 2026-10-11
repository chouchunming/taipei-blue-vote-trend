"""Village age-structure parsing, joining, and ecological modeling."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterable, Sequence

from .analysis import VillageResult


@dataclass(frozen=True, slots=True)
class PopulationRow:
    district: str
    village: str
    total: int
    age_20_39: int
    age_40_64: int
    age_65_plus: int
    age_75_plus: int


@dataclass(frozen=True, slots=True)
class AgeObservation:
    district: str
    village: str
    population: int
    young_share: float
    middle_share: float
    senior_share: float
    age_75_plus_share: float
    valid_votes: int
    blue_votes: int
    blue_share: float


@dataclass(frozen=True, slots=True)
class ModelCoefficient:
    name: str
    coefficient: float
    effect_for_10pp: float | None


@dataclass(frozen=True, slots=True)
class AgePrediction:
    observation: AgeObservation
    predicted_blue_share: float
    residual: float
    actual_rank: int
    predicted_rank: int


@dataclass(frozen=True, slots=True)
class AgeModel:
    coefficients: tuple[ModelCoefficient, ...]
    predictions: tuple[AgePrediction, ...]
    weighted_r2: float
    baseline_district: str


def parse_population_api_json(
    payload: bytes,
    *,
    expected_yyymm: str,
) -> tuple[PopulationRow, ...]:
    """Parse the official RIS village single-age API and keep Taipei rows."""
    document = json.loads(payload.decode("utf-8-sig"))
    if document.get("responseCode") != "OD-0101-S":
        raise ValueError(f"population API error: {document.get('responseMessage', 'unknown')}")
    if str(document.get("page")) != "1":
        raise ValueError("population API payload must be page 1")
    snapshot = document.get("responseData")
    if not isinstance(snapshot, list):
        raise ValueError("population API responseData must be a list")

    output = []
    seen = set()
    for source in snapshot:
        site_id = source.get("site_id", "").strip()
        if source.get("statistic_yyymm") != expected_yyymm or not site_id.startswith("臺北市"):
            continue
        district = site_id.removeprefix("臺北市")
        village = source.get("village", "").strip()
        if not district.endswith("區") or not village.endswith("里"):
            raise ValueError(f"unexpected Taipei population location: {site_id} {village}")
        key = (district, village)
        if key in seen:
            raise ValueError(f"duplicate population village: {district} {village}")
        seen.add(key)

        try:
            ages = [
                int(source[f"people_age_{age:03d}_m"])
                + int(source[f"people_age_{age:03d}_f"])
                for age in range(100)
            ]
            age_100_plus = int(source["people_age_100up_m"]) + int(
                source["people_age_100up_f"]
            )
            total = int(source["people_total"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"invalid population fields: {district} {village}") from error
        if sum(ages) + age_100_plus != total:
            raise ValueError(f"age counts do not sum to total: {district} {village}")
        output.append(
            PopulationRow(
                district=district,
                village=village,
                total=total,
                age_20_39=sum(ages[20:40]),
                age_40_64=sum(ages[40:65]),
                age_65_plus=sum(ages[65:]) + age_100_plus,
                age_75_plus=sum(ages[75:]) + age_100_plus,
            )
        )
    if not output:
        raise ValueError(f"no Taipei village population rows for {expected_yyymm}")
    return tuple(sorted(output, key=lambda row: (row.district, row.village)))


def join_age_and_votes(
    population: Iterable[PopulationRow],
    votes: Iterable[VillageResult],
) -> tuple[tuple[AgeObservation, ...], tuple[int, int]]:
    """Exact-key join of one population snapshot to 2024 village votes."""
    population_by_key = {(row.district, row.village): row for row in population}
    vote_rows = [row for row in votes if row.year == 2024]
    output = []
    for vote in vote_rows:
        person = population_by_key.get((vote.district, vote.village))
        if person is None:
            continue
        if person.total <= 0:
            raise ValueError(f"population total must be positive: {person.district} {person.village}")
        output.append(
            AgeObservation(
                district=vote.district,
                village=vote.village,
                population=person.total,
                young_share=person.age_20_39 / person.total,
                middle_share=person.age_40_64 / person.total,
                senior_share=person.age_65_plus / person.total,
                age_75_plus_share=person.age_75_plus / person.total,
                valid_votes=vote.valid_votes,
                blue_votes=vote.blue_votes,
                blue_share=vote.blue_votes / vote.valid_votes,
            )
        )
    output.sort(key=lambda row: (row.district, row.village))
    return tuple(output), (len(output), len(vote_rows))


def weighted_least_squares(
    rows: Sequence[Sequence[float]],
    targets: Sequence[float],
    weights: Sequence[float],
) -> tuple[float, ...]:
    """Solve (X'WX)b = X'Wy without a third-party linear-algebra dependency."""
    if not rows or len(rows) != len(targets) or len(rows) != len(weights):
        raise ValueError("rows, targets, and weights must have equal non-zero length")
    width = len(rows[0])
    if width == 0 or any(len(row) != width for row in rows):
        raise ValueError("design rows must have equal non-zero width")
    if any(weight <= 0 for weight in weights):
        raise ValueError("weights must be positive")

    xtwx = [
        [
            sum(weight * row[left] * row[right] for row, weight in zip(rows, weights))
            for right in range(width)
        ]
        for left in range(width)
    ]
    xtwy = [
        sum(
            weight * row[column] * target
            for row, target, weight in zip(rows, targets, weights)
        )
        for column in range(width)
    ]
    return _solve_linear_system(xtwx, xtwy)


def fit_age_model(observations: Iterable[AgeObservation]) -> AgeModel:
    """Fit weighted age shares plus district fixed effects to 2024 blue share."""
    data = tuple(sorted(observations, key=lambda row: (row.district, row.village)))
    districts = sorted({row.district for row in data})
    if len(districts) < 2:
        raise ValueError("age model requires at least two districts")
    baseline_district = districts[0]
    fixed_effect_districts = districts[1:]
    names = ["intercept", "young_share", "senior_share"]
    names.extend(f"district:{district}" for district in fixed_effect_districts)
    design = [
        [
            1.0,
            row.young_share,
            row.senior_share,
            *(1.0 if row.district == district else 0.0 for district in fixed_effect_districts),
        ]
        for row in data
    ]
    targets = [row.blue_share for row in data]
    weights = [float(row.valid_votes) for row in data]
    beta = weighted_least_squares(design, targets, weights)
    predicted = [sum(value * coefficient for value, coefficient in zip(row, beta)) for row in design]

    weight_total = sum(weights)
    weighted_mean = sum(weight * target for weight, target in zip(weights, targets)) / weight_total
    residual_sum = sum(
        weight * (target - estimate) ** 2
        for weight, target, estimate in zip(weights, targets, predicted)
    )
    total_sum = sum(weight * (target - weighted_mean) ** 2 for weight, target in zip(weights, targets))
    if total_sum <= 0:
        raise ValueError("age model target has no weighted variation")
    weighted_r2 = 1.0 - residual_sum / total_sum

    actual_ranks = _descending_ranks(data, targets)
    predicted_ranks = _descending_ranks(data, predicted)
    predictions = tuple(
        AgePrediction(
            observation=observation,
            predicted_blue_share=estimate,
            residual=target - estimate,
            actual_rank=actual_ranks[(observation.district, observation.village)],
            predicted_rank=predicted_ranks[(observation.district, observation.village)],
        )
        for observation, target, estimate in zip(data, targets, predicted)
    )
    coefficients = tuple(
        ModelCoefficient(
            name=name,
            coefficient=value,
            effect_for_10pp=value * 10 if name in {"young_share", "senior_share"} else None,
        )
        for name, value in zip(names, beta)
    )
    return AgeModel(coefficients, predictions, weighted_r2, baseline_district)


def _solve_linear_system(
    coefficients: Sequence[Sequence[float]],
    targets: Sequence[float],
) -> tuple[float, ...]:
    size = len(coefficients)
    if size == 0 or len(targets) != size or any(len(row) != size for row in coefficients):
        raise ValueError("linear system must be square")
    matrix = [list(row) + [target] for row, target in zip(coefficients, targets)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(matrix[row][column]))
        if abs(matrix[pivot][column]) < 1e-12:
            raise ValueError("singular design matrix")
        matrix[column], matrix[pivot] = matrix[pivot], matrix[column]
        divisor = matrix[column][column]
        matrix[column] = [value / divisor for value in matrix[column]]
        for row in range(size):
            if row == column:
                continue
            factor = matrix[row][column]
            matrix[row] = [
                value - factor * pivot_value
                for value, pivot_value in zip(matrix[row], matrix[column])
            ]
    return tuple(matrix[row][-1] for row in range(size))


def _descending_ranks(
    observations: Sequence[AgeObservation],
    values: Sequence[float],
) -> dict[tuple[str, str], int]:
    ordered = sorted(
        zip(observations, values),
        key=lambda item: (-item[1], item[0].district, item[0].village),
    )
    return {
        (observation.district, observation.village): rank
        for rank, (observation, _) in enumerate(ordered, start=1)
    }
