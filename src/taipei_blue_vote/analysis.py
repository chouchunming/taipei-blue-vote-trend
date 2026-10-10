"""Pure election aggregation and estimation functions."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable, Sequence


ELECTION_YEARS = (2000, 2004, 2008, 2012, 2016, 2020, 2024)

BLUE_CANDIDATES = {
    2000: frozenset({"宋楚瑜", "連戰"}),
    2004: frozenset({"連戰"}),
    2008: frozenset({"馬英九"}),
    2012: frozenset({"馬英九", "宋楚瑜"}),
    2016: frozenset({"朱立倫", "宋楚瑜"}),
    2020: frozenset({"韓國瑜", "宋楚瑜"}),
    2024: frozenset({"侯友宜"}),
}


@dataclass(frozen=True, slots=True)
class VoteRow:
    year: int
    district: str
    village: str
    candidate: str
    votes: int


@dataclass(frozen=True, slots=True)
class VillageResult:
    year: int
    district: str
    village: str
    valid_votes: int
    blue_votes: int
    ko_votes: int

    @property
    def blue_share(self) -> float:
        if self.valid_votes <= 0:
            raise ValueError("valid votes must be positive")
        return round(self.blue_votes / self.valid_votes * 100, 4)


@dataclass(frozen=True, slots=True)
class ElectionResult:
    year: int
    valid_votes: int
    blue_votes: int
    ko_votes: int

    @property
    def blue_share(self) -> float:
        if self.valid_votes <= 0:
            raise ValueError("valid votes must be positive")
        return round(self.blue_votes / self.valid_votes * 100, 4)


VillageKey = tuple[str, str]


def aggregate_villages(rows: Iterable[VoteRow]) -> tuple[VillageResult, ...]:
    """Aggregate normalized candidate rows to one result per village and year."""
    grouped: dict[tuple[int, str, str], list[int]] = defaultdict(lambda: [0, 0, 0])
    for row in rows:
        if row.year not in BLUE_CANDIDATES:
            raise ValueError(f"unsupported election year: {row.year}")
        if row.votes < 0:
            raise ValueError("votes must be non-negative")
        totals = grouped[(row.year, row.district, row.village)]
        totals[0] += row.votes
        if row.candidate in BLUE_CANDIDATES[row.year]:
            totals[1] += row.votes
        if row.year == 2024 and row.candidate == "柯文哲":
            totals[2] += row.votes

    results = tuple(
        VillageResult(year, district, village, *totals)
        for (year, district, village), totals in sorted(grouped.items())
    )
    for result in results:
        if result.valid_votes <= 0:
            raise ValueError(
                f"valid votes must be positive: {result.year} {result.district} {result.village}"
            )
    return results


def select_fixed_cohort(
    results: Iterable[VillageResult],
    *,
    threshold: float = 65.0,
    minimum_valid: int = 100,
) -> frozenset[VillageKey]:
    """Select 2000 deep-blue villages present in every election year."""
    by_key: dict[VillageKey, dict[int, VillageResult]] = defaultdict(dict)
    for result in results:
        by_key[(result.district, result.village)][result.year] = result

    required_years = set(ELECTION_YEARS)
    selected = set()
    for key, yearly in by_key.items():
        baseline = yearly.get(2000)
        if (
            baseline is not None
            and required_years.issubset(yearly)
            and baseline.valid_votes >= minimum_valid
            and baseline.blue_share >= threshold
        ):
            selected.add(key)
    return frozenset(selected)


def summarize(
    results: Iterable[VillageResult],
    selected: Iterable[VillageKey] | None = None,
) -> tuple[ElectionResult, ...]:
    """Sum village results by election, optionally for selected village keys."""
    selected_set = None if selected is None else set(selected)
    grouped: dict[int, list[int]] = defaultdict(lambda: [0, 0, 0])
    for result in results:
        if selected_set is not None and (result.district, result.village) not in selected_set:
            continue
        totals = grouped[result.year]
        totals[0] += result.valid_votes
        totals[1] += result.blue_votes
        totals[2] += result.ko_votes
    return tuple(ElectionResult(year, *grouped[year]) for year in sorted(grouped))


def election_deltas(
    rows: Sequence[tuple[int, float, int]],
) -> list[tuple[int, float, int]]:
    """Return current-minus-previous share-point and vote deltas."""
    return [
        (
            current[0],
            round(current[1] - previous[1], 2),
            current[2] - previous[2],
        )
        for previous, current in zip(rows, rows[1:])
    ]


def estimate_young_votes(
    eligible: int,
    turnout: float,
    low_share: float,
    central_share: float,
    high_share: float,
) -> tuple[int, int, int]:
    """Estimate young blue votes from electorate, turnout, and support bounds."""
    if eligible < 0:
        raise ValueError("eligible voters must be non-negative")
    rates = (turnout, low_share, central_share, high_share)
    if any(rate < 0 or rate > 1 for rate in rates):
        raise ValueError("turnout and support shares must be between zero and one")
    if not low_share <= central_share <= high_share:
        raise ValueError("support shares must be ordered low, central, high")
    ballots = eligible * turnout
    return tuple(round(ballots * share) for share in (low_share, central_share, high_share))
