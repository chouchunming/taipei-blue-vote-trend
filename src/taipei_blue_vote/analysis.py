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

GREEN_CANDIDATES = {
    2000: frozenset({"陳水扁"}),
    2004: frozenset({"陳水扁"}),
    2008: frozenset({"謝長廷"}),
    2012: frozenset({"蔡英文"}),
    2016: frozenset({"蔡英文"}),
    2020: frozenset({"蔡英文"}),
    2024: frozenset({"賴清德"}),
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
    green_votes: int = 0
    other_votes: int = 0

    @property
    def blue_share(self) -> float:
        if self.valid_votes <= 0:
            raise ValueError("valid votes must be positive")
        return round(self.blue_votes / self.valid_votes * 100, 4)

    @property
    def green_share(self) -> float:
        if self.valid_votes <= 0:
            raise ValueError("valid votes must be positive")
        return round(self.green_votes / self.valid_votes * 100, 4)

    @property
    def other_share(self) -> float:
        if self.valid_votes <= 0:
            raise ValueError("valid votes must be positive")
        return round(self.other_votes / self.valid_votes * 100, 4)


@dataclass(frozen=True, slots=True)
class ElectionResult:
    year: int
    valid_votes: int
    blue_votes: int
    ko_votes: int
    green_votes: int = 0
    other_votes: int = 0

    @property
    def blue_share(self) -> float:
        if self.valid_votes <= 0:
            raise ValueError("valid votes must be positive")
        return round(self.blue_votes / self.valid_votes * 100, 4)

    @property
    def green_share(self) -> float:
        if self.valid_votes <= 0:
            raise ValueError("valid votes must be positive")
        return round(self.green_votes / self.valid_votes * 100, 4)

    @property
    def other_share(self) -> float:
        if self.valid_votes <= 0:
            raise ValueError("valid votes must be positive")
        return round(self.other_votes / self.valid_votes * 100, 4)


@dataclass(frozen=True, slots=True)
class BlocDelta:
    year: int
    blue_share_delta: float
    blue_vote_delta: int
    green_share_delta: float
    green_vote_delta: int
    other_share_delta: float
    other_vote_delta: int


@dataclass(frozen=True, slots=True)
class VolatilityResult:
    year: int
    volatility_pp: float
    vote_equivalent: int


VillageKey = tuple[str, str]


def validate_bloc_configuration(
    blue: dict[int, frozenset[str]] = BLUE_CANDIDATES,
    green: dict[int, frozenset[str]] = GREEN_CANDIDATES,
) -> None:
    """Reject candidate names configured into both blocs in one election."""
    overlaps = {
        year: sorted(blue[year] & green[year])
        for year in ELECTION_YEARS
        if blue[year] & green[year]
    }
    if overlaps:
        raise ValueError(f"blue/green candidate overlap: {overlaps}")


def aggregate_villages(rows: Iterable[VoteRow]) -> tuple[VillageResult, ...]:
    """Aggregate normalized candidate rows to one result per village and year."""
    validate_bloc_configuration()
    grouped: dict[tuple[int, str, str], list[int]] = defaultdict(lambda: [0, 0, 0, 0])
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
        if row.candidate in GREEN_CANDIDATES[row.year]:
            totals[3] += row.votes

    results = []
    for (year, district, village), totals in sorted(grouped.items()):
        valid_votes, blue_votes, ko_votes, green_votes = totals
        other_votes = valid_votes - blue_votes - green_votes
        if other_votes < 0:
            raise ValueError(f"computed other votes must be non-negative: {year} {district} {village}")
        results.append(
            VillageResult(
                year,
                district,
                village,
                valid_votes,
                blue_votes,
                ko_votes,
                green_votes,
                other_votes,
            )
        )
    results = tuple(results)
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
    bloc: str = "blue",
) -> frozenset[VillageKey]:
    """Select 2000 high-share bloc villages present in every election year."""
    if bloc not in {"blue", "green"}:
        raise ValueError(f"unsupported cohort bloc: {bloc}")
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
            and (baseline.blue_share if bloc == "blue" else baseline.green_share) >= threshold
        ):
            selected.add(key)
    return frozenset(selected)


def summarize(
    results: Iterable[VillageResult],
    selected: Iterable[VillageKey] | None = None,
) -> tuple[ElectionResult, ...]:
    """Sum village results by election, optionally for selected village keys."""
    selected_set = None if selected is None else set(selected)
    grouped: dict[int, list[int]] = defaultdict(lambda: [0, 0, 0, 0, 0])
    for result in results:
        if selected_set is not None and (result.district, result.village) not in selected_set:
            continue
        totals = grouped[result.year]
        totals[0] += result.valid_votes
        totals[1] += result.blue_votes
        totals[2] += result.ko_votes
        totals[3] += result.green_votes
        totals[4] += result.other_votes
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


def bloc_deltas(rows: Sequence[ElectionResult]) -> tuple[BlocDelta, ...]:
    """Return signed current-minus-previous changes for all three blocs."""
    return tuple(
        BlocDelta(
            year=current.year,
            blue_share_delta=round(current.blue_share - previous.blue_share, 2),
            blue_vote_delta=current.blue_votes - previous.blue_votes,
            green_share_delta=round(current.green_share - previous.green_share, 2),
            green_vote_delta=current.green_votes - previous.green_votes,
            other_share_delta=round(current.other_share - previous.other_share, 2),
            other_vote_delta=current.other_votes - previous.other_votes,
        )
        for previous, current in zip(rows, rows[1:])
    )


def electoral_volatility(rows: Sequence[ElectionResult]) -> tuple[VolatilityResult, ...]:
    """Calculate three-bloc total variation and its current-vote equivalent."""
    output = []
    for previous, current in zip(rows, rows[1:]):
        volatility_pp = round(
            (
                abs(current.blue_share - previous.blue_share)
                + abs(current.green_share - previous.green_share)
                + abs(current.other_share - previous.other_share)
            )
            / 2,
            4,
        )
        output.append(
            VolatilityResult(
                year=current.year,
                volatility_pp=volatility_pp,
                vote_equivalent=round(current.valid_votes * volatility_pp / 100),
            )
        )
    return tuple(output)


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
