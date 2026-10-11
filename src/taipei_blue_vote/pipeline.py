"""Composition of tested analysis primitives into report-ready results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .analysis import (
    VoteRow,
    BlocDelta,
    VillageKey,
    VillageResult,
    ElectionResult,
    VolatilityResult,
    aggregate_villages,
    bloc_deltas,
    electoral_volatility,
    election_deltas,
    select_fixed_cohort,
    summarize,
)


@dataclass(frozen=True, slots=True)
class AnalysisBundle:
    villages: tuple[VillageResult, ...]
    city: tuple[ElectionResult, ...]
    cohort_keys: frozenset[VillageKey]
    cohort: tuple[ElectionResult, ...]
    deltas: tuple[tuple[int, float, int], ...]
    green_cohort_keys: frozenset[VillageKey]
    green_cohort: tuple[ElectionResult, ...]
    green_deltas: tuple[tuple[int, float, int], ...]
    bloc_deltas: tuple[BlocDelta, ...]
    volatility: tuple[VolatilityResult, ...]


@dataclass(frozen=True, slots=True)
class ProxyResult:
    proxy_name: str
    district: str
    village: str
    year: int
    valid_votes: int
    blue_votes: int
    blue_share: float
    continuously_comparable: bool


def analyze_rows(rows: Iterable[VoteRow]) -> AnalysisBundle:
    villages = aggregate_villages(rows)
    city = summarize(villages)
    cohort_keys = select_fixed_cohort(villages)
    cohort = summarize(villages, cohort_keys)
    deltas = tuple(
        election_deltas([(row.year, row.blue_share, row.blue_votes) for row in city])
    )
    green_cohort_keys = select_fixed_cohort(villages, threshold=45.0, bloc="green")
    green_cohort = summarize(villages, green_cohort_keys)
    green_deltas = tuple(
        election_deltas([(row.year, row.green_share, row.green_votes) for row in city])
    )
    all_bloc_deltas = bloc_deltas(city)
    volatility = electoral_volatility(city)
    return AnalysisBundle(
        villages,
        city,
        cohort_keys,
        cohort,
        deltas,
        green_cohort_keys,
        green_cohort,
        green_deltas,
        all_bloc_deltas,
        volatility,
    )


def proxy_results(
    rows: Iterable[VoteRow],
    specs: Iterable[tuple[str, str, str, int]],
) -> tuple[ProxyResult, ...]:
    villages = aggregate_villages(rows)
    by_key: dict[VillageKey, list[VillageResult]] = {}
    for result in villages:
        by_key.setdefault((result.district, result.village), []).append(result)

    output = []
    for proxy_name, district, village, start_year in specs:
        key = (district, village)
        if key not in by_key:
            raise ValueError(f"proxy village not found: {district} {village}")
        for result in by_key[key]:
            if result.year >= start_year:
                output.append(
                    ProxyResult(
                        proxy_name=proxy_name,
                        district=district,
                        village=village,
                        year=result.year,
                        valid_votes=result.valid_votes,
                        blue_votes=result.blue_votes,
                        blue_share=result.blue_share,
                        continuously_comparable=start_year == 2000,
                    )
                )
    return tuple(output)
