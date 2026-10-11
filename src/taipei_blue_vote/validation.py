"""Release checks that detect source-schema or classification drift."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable, Mapping

from .analysis import (
    BLUE_CANDIDATES,
    ELECTION_YEARS,
    GREEN_CANDIDATES,
    ElectionResult,
    VoteRow,
)
from .mayor import (
    COALITION_BLUE,
    COALITION_GREEN,
    OFFICIAL_BLUE,
    OFFICIAL_GREEN,
    MayorAnalysisBundle,
)
from .sources import MAYOR_YEARS, MayorVoteRow


EXPECTED_CITY_TOTALS = {
    2000: (1_587_166, 979_102, 597_465, 10_599),
    2004: (1_588_249, 897_870, 690_379, 0),
    2008: (1_604_802, 1_011_546, 593_256, 0),
    2012: (1_604_730, 970_165, 634_565, 0),
    2016: (1_457_678, 700_295, 757_383, 0),
    2020: (1_632_453, 756_599, 875_854, 0),
    2024: (1_542_011, 587_258, 587_899, 366_854),
}

EXPECTED_MAYOR_CITY_TOTALS = {
    "coalition": {
        2002: (1_361_913, 873_102, 488_811, 0),
        2006: (1_286_089, 745_366, 529_241, 11_482),
        2010: (1_433_736, 797_865, 628_129, 7_742),
        2014: (1_494_046, 609_932, 853_983, 30_131),
        2018: (1_413_870, 577_096, 244_342, 592_432),
        2022: (1_360_951, 575_590, 434_558, 350_803),
    },
    "official_nomination": {
        2002: (1_361_913, 873_102, 488_811, 0),
        2006: (1_286_089, 692_085, 525_869, 68_135),
        2010: (1_433_736, 797_865, 628_129, 7_742),
        2014: (1_494_046, 609_932, 0, 884_114),
        2018: (1_413_870, 577_096, 244_342, 592_432),
        2022: (1_360_951, 575_590, 434_558, 350_803),
    },
}

_MAYOR_CANDIDATE_MAPS = {
    "coalition": (COALITION_BLUE, COALITION_GREEN),
    "official_nomination": (OFFICIAL_BLUE, OFFICIAL_GREEN),
}


def verify_candidate_coverage(
    rows: Iterable[VoteRow],
    *,
    years: Iterable[int] = ELECTION_YEARS,
) -> None:
    observed: dict[int, set[str]] = defaultdict(set)
    for row in rows:
        observed[row.year].add(row.candidate)
    missing_blue = {
        year: sorted(BLUE_CANDIDATES[year] - observed[year])
        for year in years
        if BLUE_CANDIDATES[year] - observed[year]
    }
    if missing_blue:
        raise ValueError(f"missing configured blue candidates: {missing_blue}")
    missing_green = {
        year: sorted(GREEN_CANDIDATES[year] - observed[year])
        for year in years
        if GREEN_CANDIDATES[year] - observed[year]
    }
    if missing_green:
        raise ValueError(f"missing configured green candidates: {missing_green}")


def verify_city_totals(
    results: Iterable[ElectionResult],
    *,
    expected: Mapping[int, tuple[int, int, int, int]] = EXPECTED_CITY_TOTALS,
) -> None:
    observed = {
        row.year: (row.valid_votes, row.blue_votes, row.green_votes, row.other_votes)
        for row in results
    }
    mismatches = {
        year: {"expected": totals, "observed": observed.get(year)}
        for year, totals in expected.items()
        if observed.get(year) != totals
    }
    if mismatches:
        raise ValueError(f"city total mismatch: {mismatches}")


def verify_mayor_candidate_coverage(
    rows: Iterable[MayorVoteRow],
    *,
    years: Iterable[int] = MAYOR_YEARS,
) -> None:
    observed: dict[int, set[str]] = defaultdict(set)
    for row in rows:
        observed[row.year].add(row.candidate)

    missing = {}
    for scenario, (blue, green) in _MAYOR_CANDIDATE_MAPS.items():
        scenario_missing = {
            year: sorted((blue[year] | green[year]) - observed[year])
            for year in years
            if (blue[year] | green[year]) - observed[year]
        }
        if scenario_missing:
            missing[scenario] = scenario_missing
    if missing:
        raise ValueError(f"missing configured mayor candidates: {missing}")


def verify_mayor_city_totals(
    analysis: MayorAnalysisBundle,
    *,
    expected: Mapping[
        str, Mapping[int, tuple[int, int, int, int]]
    ] = EXPECTED_MAYOR_CITY_TOTALS,
) -> None:
    observed = {
        scenario.classification: {
            row.year: (
                row.valid_votes,
                row.blue_votes,
                row.green_votes,
                row.other_votes,
            )
            for row in scenario.city
        }
        for scenario in analysis.scenarios
    }
    mismatches = {
        scenario: {
            year: {"expected": totals, "observed": observed.get(scenario, {}).get(year)}
            for year, totals in yearly.items()
            if observed.get(scenario, {}).get(year) != totals
        }
        for scenario, yearly in expected.items()
    }
    mismatches = {scenario: yearly for scenario, yearly in mismatches.items() if yearly}
    if mismatches:
        raise ValueError(f"mayor city total mismatch: {mismatches}")
