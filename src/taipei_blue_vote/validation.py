"""Release checks that detect source-schema or classification drift."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable, Mapping

from .analysis import BLUE_CANDIDATES, ELECTION_YEARS, ElectionResult, VoteRow


EXPECTED_CITY_TOTALS = {
    2000: (1_587_166, 979_102),
    2004: (1_588_249, 897_870),
    2008: (1_604_802, 1_011_546),
    2012: (1_604_730, 970_165),
    2016: (1_457_678, 700_295),
    2020: (1_632_453, 756_599),
    2024: (1_542_011, 587_258),
}


def verify_candidate_coverage(
    rows: Iterable[VoteRow],
    *,
    years: Iterable[int] = ELECTION_YEARS,
) -> None:
    observed: dict[int, set[str]] = defaultdict(set)
    for row in rows:
        observed[row.year].add(row.candidate)
    missing = {
        year: sorted(BLUE_CANDIDATES[year] - observed[year])
        for year in years
        if BLUE_CANDIDATES[year] - observed[year]
    }
    if missing:
        raise ValueError(f"missing configured blue candidates: {missing}")


def verify_city_totals(
    results: Iterable[ElectionResult],
    *,
    expected: Mapping[int, tuple[int, int]] = EXPECTED_CITY_TOTALS,
) -> None:
    observed = {row.year: (row.valid_votes, row.blue_votes) for row in results}
    mismatches = {
        year: {"expected": totals, "observed": observed.get(year)}
        for year, totals in expected.items()
        if observed.get(year) != totals
    }
    if mismatches:
        raise ValueError(f"city total mismatch: {mismatches}")
