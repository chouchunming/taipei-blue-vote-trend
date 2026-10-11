"""Source discovery, download, hashing, and CSV normalization."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

from .analysis import ELECTION_YEARS, VoteRow


INDEX_URL = "https://taiwanvotes.tw/data/csv/index.json"
CSV_BASE_URL = "https://taiwanvotes.tw/data/csv/"
USER_AGENT = "taipei-blue-vote-trend/1.0 (+https://github.com/chouchunming/taipei-blue-vote-trend)"

REQUIRED_COLUMNS = frozenset({"屆期", "鄉鎮市區", "村里", "候選人", "得票數"})
MAYOR_REQUIRED_COLUMNS = REQUIRED_COLUMNS | {"政黨"}
MAYOR_YEARS = (2002, 2006, 2010, 2014, 2018, 2022)


@dataclass(frozen=True, slots=True)
class MayorVoteRow:
    year: int
    district: str
    village: str
    candidate: str
    party: str
    votes: int


def parse_vote_csv(payload: bytes) -> tuple[VoteRow, ...]:
    """Parse one normalized TaiwanVotes presidential CSV."""
    reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig")))
    columns = set(reader.fieldnames or ())
    missing = sorted(REQUIRED_COLUMNS - columns)
    if missing:
        raise ValueError(f"missing CSV columns: {', '.join(missing)}")

    rows = []
    for source in reader:
        try:
            rows.append(
                VoteRow(
                    year=int(source["屆期"]),
                    district=source["鄉鎮市區"].strip(),
                    village=source["村里"].strip(),
                    candidate=source["候選人"].strip(),
                    votes=int(source["得票數"]),
                )
            )
        except (AttributeError, TypeError, ValueError) as error:
            raise ValueError(f"invalid vote row: {source}") from error
    return tuple(rows)


def parse_mayor_vote_csv(payload: bytes) -> tuple[MayorVoteRow, ...]:
    """Parse one normalized TaiwanVotes mayor CSV."""
    reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig")))
    columns = set(reader.fieldnames or ())
    missing = sorted(MAYOR_REQUIRED_COLUMNS - columns)
    if missing:
        raise ValueError(f"missing CSV columns: {', '.join(missing)}")

    rows = []
    for source in reader:
        try:
            rows.append(
                MayorVoteRow(
                    year=_mayor_election_year(source["屆期"]),
                    district=source["鄉鎮市區"].strip(),
                    village=source["村里"].strip(),
                    candidate=source["候選人"].strip(),
                    party=source["政黨"].strip(),
                    votes=int(source["得票數"]),
                )
            )
        except (AttributeError, TypeError, ValueError) as error:
            raise ValueError(f"invalid mayor vote row: {source}") from error
    return tuple(rows)


def _mayor_election_year(term: str) -> int:
    """Normalize TaiwanVotes terms such as ``2001/02`` to election year 2002."""
    value = term.strip()
    if "/" not in value:
        return int(value)
    start, end = value.split("/", 1)
    if len(start) != 4 or len(end) != 2:
        raise ValueError(f"invalid mayor election term: {term}")
    return int(start[:2] + end)


def select_taipei_presidential_files(index_payload: bytes) -> dict[int, str]:
    """Return the single Taipei presidential CSV filename for each target year."""
    index = json.loads(index_payload.decode("utf-8-sig"))
    selected: dict[int, str] = {}
    for item in index.get("files", []):
        if (
            item.get("kind") == "votes"
            and item.get("type") == "總統"
            and item.get("county") == "臺北市"
            and item.get("year") in ELECTION_YEARS
        ):
            year = int(item["year"])
            if year in selected:
                raise ValueError(f"multiple Taipei presidential files for {year}")
            selected[year] = str(item["file"])

    missing = [year for year in ELECTION_YEARS if year not in selected]
    if missing:
        raise ValueError(f"missing Taipei presidential files for: {missing}")
    return dict(sorted(selected.items()))


def select_taipei_mayor_files(index_payload: bytes) -> dict[int, str]:
    """Return the single Taipei mayor CSV filename for each target year."""
    index = json.loads(index_payload.decode("utf-8-sig"))
    selected: dict[int, str] = {}
    for item in index.get("files", []):
        if (
            item.get("kind") == "votes"
            and item.get("type") == "縣市長"
            and item.get("county") == "臺北市"
            and item.get("year") in MAYOR_YEARS
        ):
            year = int(item["year"])
            if year in selected:
                raise ValueError(f"multiple Taipei mayor files for {year}")
            selected[year] = str(item["file"])

    missing = [year for year in MAYOR_YEARS if year not in selected]
    if missing:
        raise ValueError(f"missing Taipei mayor files for: {missing}")
    return dict(sorted(selected.items()))


def sha256_hex(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def fetch_bytes(url: str, timeout: float = 30.0) -> bytes:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        return response.read()


def csv_url(filename: str) -> str:
    return CSV_BASE_URL + quote(filename)


def cached_payload(
    url: str,
    path: Path,
    *,
    refresh: bool = False,
    timeout: float = 30.0,
) -> bytes:
    """Read a cache entry or download and replace it."""
    if path.exists() and not refresh:
        return path.read_bytes()
    payload = fetch_bytes(url, timeout=timeout)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(payload)
    temporary.replace(path)
    return payload
