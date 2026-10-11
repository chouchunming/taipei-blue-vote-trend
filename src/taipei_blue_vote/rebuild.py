"""End-to-end rebuild of source manifest, derived tables, and charts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Mapping

from .analysis import VoteRow
from .artifacts import write_artifacts
from .pipeline import analyze_rows, proxy_results
from .sources import (
    INDEX_URL,
    cached_payload,
    csv_url,
    parse_vote_csv,
    select_taipei_presidential_files,
    sha256_hex,
)
from .validation import EXPECTED_CITY_TOTALS, verify_candidate_coverage, verify_city_totals


PROXY_SPECS = (
    ("四四南村所在地", "信義區", "景新里", 2000),
    ("四四西村／忠駝國宅所在地", "信義區", "西村里", 2000),
    ("中心新村所在地", "北投區", "林泉里", 2000),
    ("嘉禾新村所在地", "中正區", "富水里", 2000),
    ("煥民新村所在地", "大安區", "學府里", 2004),
)


def rebuild(root: Path, *, refresh: bool = False) -> None:
    raw = root / "data" / "raw"
    index_payload = cached_payload(
        INDEX_URL,
        raw / "index.json",
        refresh=refresh,
    )
    filenames = select_taipei_presidential_files(index_payload)
    payloads = {
        year: cached_payload(
            csv_url(filename),
            raw / filename,
            refresh=refresh,
        )
        for year, filename in filenames.items()
    }
    rebuild_from_payloads(root, index_payload, filenames, payloads)


def rebuild_from_payloads(
    root: Path,
    index_payload: bytes,
    filenames: Mapping[int, str],
    payloads: Mapping[int, bytes],
    *,
    expected_city_totals: Mapping[int, tuple[int, int]] = EXPECTED_CITY_TOTALS,
    proxy_specs: Iterable[tuple[str, str, str, int]] = PROXY_SPECS,
) -> None:
    rows: list[VoteRow] = []
    file_records = []
    for year, filename in sorted(filenames.items()):
        if year not in payloads:
            raise ValueError(f"missing payload for {year}")
        payload = payloads[year]
        parsed = parse_vote_csv(payload)
        if any(row.year != year for row in parsed):
            raise ValueError(f"unexpected election year inside {filename}")
        rows.extend(parsed)
        file_records.append(
            {
                "bytes": len(payload),
                "filename": filename,
                "rows": len(parsed),
                "sha256": sha256_hex(payload),
                "url": csv_url(filename),
                "year": year,
            }
        )

    verify_candidate_coverage(rows, years=sorted(filenames))
    analysis = analyze_rows(rows)
    verify_city_totals(analysis.city, expected=expected_city_totals)
    proxies = proxy_results(rows, proxy_specs)
    index = json.loads(index_payload.decode("utf-8-sig"))
    manifest = {
        "build_id": index.get("buildId"),
        "compilation_attribution": index.get("compilationAttribution"),
        "compilation_license": index.get("compilationLicense"),
        "dataset": "TaiwanVotes normalized CEC election CSV",
        "files": file_records,
        "index_sha256": sha256_hex(index_payload),
        "index_url": INDEX_URL,
        "schema_version": index.get("schemaVersion"),
        "source_license": index.get("sourceLicense"),
        "source_modified": index.get("sourceModified"),
        "source_retrieved": index.get("sourceRetrieved"),
        "source_sha256": index.get("sourceSha256"),
        "source_version": index.get("sourceVersion"),
    }
    write_artifacts(root, analysis, proxies, manifest)
