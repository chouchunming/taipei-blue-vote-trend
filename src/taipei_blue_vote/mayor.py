"""Taipei mayor candidate classification and election trend analysis."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from .sources import MAYOR_YEARS, MayorVoteRow


COALITION_BLUE = {
    2002: frozenset({"馬英九"}),
    2006: frozenset({"郝龍斌", "宋楚瑜"}),
    2010: frozenset({"郝龍斌"}),
    2014: frozenset({"連勝文"}),
    2018: frozenset({"丁守中"}),
    2022: frozenset({"蔣萬安"}),
}
COALITION_GREEN = {
    2002: frozenset({"李應元"}),
    2006: frozenset({"謝長廷", "周玉蔻"}),
    2010: frozenset({"蘇貞昌"}),
    2014: frozenset({"柯文哲"}),
    2018: frozenset({"姚文智"}),
    2022: frozenset({"陳時中"}),
}
OFFICIAL_BLUE = {
    2002: frozenset({"馬英九"}),
    2006: frozenset({"郝龍斌"}),
    2010: frozenset({"郝龍斌"}),
    2014: frozenset({"連勝文"}),
    2018: frozenset({"丁守中"}),
    2022: frozenset({"蔣萬安"}),
}
OFFICIAL_GREEN = {
    2002: frozenset({"李應元"}),
    2006: frozenset({"謝長廷"}),
    2010: frozenset({"蘇貞昌"}),
    2014: frozenset(),
    2018: frozenset({"姚文智"}),
    2022: frozenset({"陳時中"}),
}

_CLASSIFICATION_MAPS = {
    "coalition": (COALITION_BLUE, COALITION_GREEN),
    "official_nomination": (OFFICIAL_BLUE, OFFICIAL_GREEN),
}


@dataclass(frozen=True, slots=True)
class MayorVillageResult:
    classification: str
    year: int
    district: str
    village: str
    valid_votes: int
    blue_votes: int
    green_votes: int
    other_votes: int

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
class MayorElectionResult:
    classification: str
    year: int
    valid_votes: int
    blue_votes: int
    green_votes: int
    other_votes: int

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
class MayorCandidateTotal:
    classification: str
    year: int
    candidate: str
    party: str
    bloc: str
    votes: int
    share: float

    @property
    def vote_share(self) -> float:
        return self.share


@dataclass(frozen=True, slots=True)
class MayorBlocDelta:
    classification: str
    year: int
    blue_share_delta: float
    blue_vote_delta: int
    green_share_delta: float
    green_vote_delta: int
    other_share_delta: float
    other_vote_delta: int


@dataclass(frozen=True, slots=True)
class MayorVolatility:
    classification: str
    year: int
    volatility_pp: float
    vote_equivalent: int


MayorVillageKey = tuple[str, str]


@dataclass(frozen=True, slots=True)
class MayorScenarioAnalysis:
    classification: str
    villages: tuple[MayorVillageResult, ...]
    city: tuple[MayorElectionResult, ...]
    candidate_totals: tuple[MayorCandidateTotal, ...]
    deltas: tuple[MayorBlocDelta, ...]
    volatility: tuple[MayorVolatility, ...]


@dataclass(frozen=True, slots=True)
class MayorAnalysisBundle:
    coalition: MayorScenarioAnalysis
    official_nomination: MayorScenarioAnalysis
    deep_blue_keys: frozenset[MayorVillageKey]
    deep_blue: tuple[MayorElectionResult, ...]
    deep_green_keys: frozenset[MayorVillageKey]
    deep_green: tuple[MayorElectionResult, ...]

    @property
    def scenarios(self) -> tuple[MayorScenarioAnalysis, MayorScenarioAnalysis]:
        return (self.coalition, self.official_nomination)

    @property
    def cohort_keys(self) -> frozenset[MayorVillageKey]:
        return self.deep_blue_keys

    @property
    def cohort(self) -> tuple[MayorElectionResult, ...]:
        return self.deep_blue

    @property
    def green_cohort_keys(self) -> frozenset[MayorVillageKey]:
        return self.deep_green_keys

    @property
    def green_cohort(self) -> tuple[MayorElectionResult, ...]:
        return self.deep_green


def validate_mayor_bloc_configuration(
    blue: dict[int, frozenset[str]] | None = None,
    green: dict[int, frozenset[str]] | None = None,
) -> None:
    """Reject candidate names configured into both blocs in one election."""
    configurations = (
        tuple(_CLASSIFICATION_MAPS.values())
        if blue is None and green is None
        else ((blue, green),)
    )
    if any(item is None for pair in configurations for item in pair):
        raise ValueError("blue and green candidate maps must be provided together")

    for blue_map, green_map in configurations:
        overlaps = {
            year: sorted(blue_map[year] & green_map[year])
            for year in MAYOR_YEARS
            if blue_map[year] & green_map[year]
        }
        if overlaps:
            raise ValueError(f"blue/green candidate overlap: {overlaps}")


def bloc_for_candidate(year: int, candidate: str, classification: str) -> str:
    """Return the candidate's blue, green, or other bloc for one scenario."""
    try:
        blue, green = _CLASSIFICATION_MAPS[classification]
    except KeyError as error:
        raise ValueError(f"unsupported mayor classification: {classification}") from error
    if year not in MAYOR_YEARS:
        raise ValueError(f"unsupported mayor election year: {year}")
    if candidate in blue[year]:
        return "blue"
    if candidate in green[year]:
        return "green"
    return "other"


def aggregate_mayor_villages(
    rows: Iterable[MayorVoteRow],
    classification: str,
) -> tuple[MayorVillageResult, ...]:
    """Aggregate candidate rows to village results for one classification."""
    try:
        blue, green = _CLASSIFICATION_MAPS[classification]
    except KeyError as error:
        raise ValueError(f"unsupported mayor classification: {classification}") from error
    validate_mayor_bloc_configuration(blue, green)

    grouped: dict[tuple[int, str, str], list[int]] = defaultdict(lambda: [0, 0, 0])
    for row in rows:
        if row.year not in MAYOR_YEARS:
            raise ValueError(f"unsupported mayor election year: {row.year}")
        if row.votes < 0:
            raise ValueError("votes must be non-negative")
        totals = grouped[(row.year, row.district, row.village)]
        totals[0] += row.votes
        if row.candidate in blue[row.year]:
            totals[1] += row.votes
        elif row.candidate in green[row.year]:
            totals[2] += row.votes

    output = []
    for (year, district, village), totals in sorted(grouped.items()):
        valid_votes, blue_votes, green_votes = totals
        if valid_votes <= 0:
            raise ValueError(
                f"valid votes must be positive: {year} {district} {village}"
            )
        other_votes = valid_votes - blue_votes - green_votes
        if other_votes < 0:
            raise ValueError(
                f"computed other votes must be non-negative: {year} {district} {village}"
            )
        output.append(
            MayorVillageResult(
                classification=classification,
                year=year,
                district=district,
                village=village,
                valid_votes=valid_votes,
                blue_votes=blue_votes,
                green_votes=green_votes,
                other_votes=other_votes,
            )
        )
    return tuple(output)


def summarize_mayor(
    results: Iterable[MayorVillageResult],
    selected: Iterable[MayorVillageKey] | None = None,
) -> tuple[MayorElectionResult, ...]:
    """Sum village results by classification and election year."""
    selected_set = None if selected is None else set(selected)
    grouped: dict[tuple[str, int], list[int]] = defaultdict(lambda: [0, 0, 0, 0])
    for result in results:
        if (
            selected_set is not None
            and (result.district, result.village) not in selected_set
        ):
            continue
        totals = grouped[(result.classification, result.year)]
        totals[0] += result.valid_votes
        totals[1] += result.blue_votes
        totals[2] += result.green_votes
        totals[3] += result.other_votes
    return tuple(
        MayorElectionResult(classification, year, *grouped[(classification, year)])
        for classification, year in sorted(grouped)
    )


def select_mayor_cohort(
    results: Iterable[MayorVillageResult],
    bloc: str,
    threshold: float,
    minimum_valid: int = 100,
) -> frozenset[MayorVillageKey]:
    """Select 2002 threshold villages present under the same key in all years."""
    if bloc not in {"blue", "green"}:
        raise ValueError(f"unsupported mayor cohort bloc: {bloc}")
    by_key: dict[MayorVillageKey, dict[int, MayorVillageResult]] = defaultdict(dict)
    for result in results:
        by_key[(result.district, result.village)][result.year] = result

    required_years = set(MAYOR_YEARS)
    selected = set()
    for key, yearly in by_key.items():
        baseline = yearly.get(2002)
        if baseline is None:
            continue
        baseline_votes = (
            baseline.blue_votes if bloc == "blue" else baseline.green_votes
        )
        if (
            set(yearly) == required_years
            and baseline.valid_votes >= minimum_valid
            and _raw_share(baseline_votes, baseline.valid_votes) >= threshold
        ):
            selected.add(key)
    return frozenset(selected)


def mayor_bloc_deltas(
    rows: Iterable[MayorElectionResult],
) -> tuple[MayorBlocDelta, ...]:
    """Return signed current-minus-previous changes for all three blocs."""
    data = tuple(rows)
    output = []
    for previous, current in zip(data, data[1:]):
        if current.classification != previous.classification:
            raise ValueError("mayor delta rows must use one classification")
        blue_share_delta = _raw_share(
            current.blue_votes, current.valid_votes
        ) - _raw_share(previous.blue_votes, previous.valid_votes)
        green_share_delta = _raw_share(
            current.green_votes, current.valid_votes
        ) - _raw_share(previous.green_votes, previous.valid_votes)
        other_share_delta = _raw_share(
            current.other_votes, current.valid_votes
        ) - _raw_share(previous.other_votes, previous.valid_votes)
        output.append(
            MayorBlocDelta(
                classification=current.classification,
                year=current.year,
                blue_share_delta=round(blue_share_delta, 2),
                blue_vote_delta=current.blue_votes - previous.blue_votes,
                green_share_delta=round(green_share_delta, 2),
                green_vote_delta=current.green_votes - previous.green_votes,
                other_share_delta=round(other_share_delta, 2),
                other_vote_delta=current.other_votes - previous.other_votes,
            )
        )
    return tuple(output)


def mayor_electoral_volatility(
    rows: Iterable[MayorElectionResult],
) -> tuple[MayorVolatility, ...]:
    """Calculate three-bloc total variation and current-vote equivalent."""
    data = tuple(rows)
    output = []
    for previous, current in zip(data, data[1:]):
        if current.classification != previous.classification:
            raise ValueError("mayor volatility rows must use one classification")
        raw_volatility_pp = (
            abs(
                _raw_share(current.blue_votes, current.valid_votes)
                - _raw_share(previous.blue_votes, previous.valid_votes)
            )
            + abs(
                _raw_share(current.green_votes, current.valid_votes)
                - _raw_share(previous.green_votes, previous.valid_votes)
            )
            + abs(
                _raw_share(current.other_votes, current.valid_votes)
                - _raw_share(previous.other_votes, previous.valid_votes)
            )
        ) / 2
        output.append(
            MayorVolatility(
                classification=current.classification,
                year=current.year,
                volatility_pp=round(raw_volatility_pp, 4),
                vote_equivalent=round(
                    current.valid_votes * raw_volatility_pp / 100
                ),
            )
        )
    return tuple(output)


def _raw_share(votes: int, valid_votes: int) -> float:
    if valid_votes <= 0:
        raise ValueError("valid votes must be positive")
    return votes / valid_votes * 100


def analyze_mayor_rows(rows: Iterable[MayorVoteRow]) -> MayorAnalysisBundle:
    """Compose both classifications and coalition-only fixed cohorts."""
    source_rows = tuple(rows)
    scenarios = {}
    for classification in ("coalition", "official_nomination"):
        villages = aggregate_mayor_villages(source_rows, classification)
        city = summarize_mayor(villages)
        scenarios[classification] = MayorScenarioAnalysis(
            classification=classification,
            villages=villages,
            city=city,
            candidate_totals=_candidate_totals(source_rows, city, classification),
            deltas=mayor_bloc_deltas(city),
            volatility=mayor_electoral_volatility(city),
        )

    coalition = scenarios["coalition"]
    deep_blue_keys = select_mayor_cohort(coalition.villages, "blue", 65.0)
    deep_green_keys = select_mayor_cohort(coalition.villages, "green", 45.0)
    return MayorAnalysisBundle(
        coalition=coalition,
        official_nomination=scenarios["official_nomination"],
        deep_blue_keys=deep_blue_keys,
        deep_blue=summarize_mayor(coalition.villages, deep_blue_keys),
        deep_green_keys=deep_green_keys,
        deep_green=summarize_mayor(coalition.villages, deep_green_keys),
    )


def _candidate_totals(
    rows: tuple[MayorVoteRow, ...],
    city: tuple[MayorElectionResult, ...],
    classification: str,
) -> tuple[MayorCandidateTotal, ...]:
    valid_by_year = {result.year: result.valid_votes for result in city}
    grouped: dict[tuple[int, str, str], int] = defaultdict(int)
    for row in rows:
        grouped[(row.year, row.candidate, row.party)] += row.votes
    return tuple(
        MayorCandidateTotal(
            classification=classification,
            year=year,
            candidate=candidate,
            party=party,
            bloc=bloc_for_candidate(year, candidate, classification),
            votes=votes,
            share=round(votes / valid_by_year[year] * 100, 4),
        )
        for (year, candidate, party), votes in sorted(grouped.items())
    )
