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


EXPECTED_CITY_TOTALS = {
    2000: (1_587_166, 979_102, 597_465, 10_599),
    2004: (1_588_249, 897_870, 690_379, 0),
    2008: (1_604_802, 1_011_546, 593_256, 0),
    2012: (1_604_730, 970_165, 634_565, 0),
    2016: (1_457_678, 700_295, 757_383, 0),
    2020: (1_632_453, 756_599, 875_854, 0),
    2024: (1_542_011, 587_258, 587_899, 366_854),
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
