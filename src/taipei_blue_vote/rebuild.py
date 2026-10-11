"""End-to-end rebuild of source manifest, derived tables, and charts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Mapping

from .age_structure import fit_age_model, join_age_and_votes, parse_population_api_json
from .analysis import VillageResult, VoteRow
from .artifacts import write_age_artifacts, write_artifacts
from .mayor import MayorAnalysisBundle, analyze_mayor_rows
from .mayor_artifacts import write_mayor_artifacts, write_mayor_charts
from .pipeline import AnalysisBundle, analyze_rows, proxy_results
from .sources import (
    INDEX_URL,
    cached_payload,
    csv_url,
    parse_mayor_vote_csv,
    parse_vote_csv,
    select_taipei_mayor_files,
    select_taipei_presidential_files,
    sha256_hex,
)
from .validation import (
    EXPECTED_CITY_TOTALS,
    EXPECTED_MAYOR_CITY_TOTALS,
    verify_candidate_coverage,
    verify_city_totals,
    verify_mayor_candidate_coverage,
    verify_mayor_city_totals,
)


PROXY_SPECS = (
    ("四四南村所在地", "信義區", "景新里", 2000),
    ("四四西村／忠駝國宅所在地", "信義區", "西村里", 2000),
    ("中心新村所在地", "北投區", "林泉里", 2000),
    ("嘉禾新村所在地", "中正區", "富水里", 2000),
    ("煥民新村所在地", "大安區", "學府里", 2004),
)

POPULATION_DATASET_URL = "https://data.gov.tw/dataset/77132"
POPULATION_SNAPSHOT_YYYMM = "11212"
POPULATION_API_URL = (
    "https://www.ris.gov.tw/rs-opendata/api/v1/datastore/ODRP014/"
    f"{POPULATION_SNAPSHOT_YYYMM}?page=1"
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
    analysis = rebuild_from_payloads(root, index_payload, filenames, payloads)
    mayor_filenames = select_taipei_mayor_files(index_payload)
    mayor_payloads = {
        year: cached_payload(
            csv_url(filename),
            raw / filename,
            refresh=refresh,
        )
        for year, filename in mayor_filenames.items()
    }
    mayor_analysis = rebuild_mayor_from_payloads(
        root,
        index_payload,
        mayor_filenames,
        mayor_payloads,
    )
    write_mayor_charts(root, mayor_analysis, analysis.city)
    population_payload = cached_payload(
        POPULATION_API_URL,
        raw / "ris-village-single-age-population-11212-page1.json",
        refresh=refresh,
        timeout=90.0,
    )
    rebuild_age_from_payload(
        root,
        analysis.villages,
        population_payload,
        source_url=POPULATION_API_URL,
    )


def rebuild_from_payloads(
    root: Path,
    index_payload: bytes,
    filenames: Mapping[int, str],
    payloads: Mapping[int, bytes],
    *,
    expected_city_totals: Mapping[int, tuple[int, int]] = EXPECTED_CITY_TOTALS,
    proxy_specs: Iterable[tuple[str, str, str, int]] = PROXY_SPECS,
) -> AnalysisBundle:
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
    return analysis


def prepare_mayor_from_payloads(
    index_payload: bytes,
    filenames: Mapping[int, str],
    payloads: Mapping[int, bytes],
    *,
    expected_city_totals=EXPECTED_MAYOR_CITY_TOTALS,
) -> tuple[MayorAnalysisBundle, dict[str, object]]:
    rows = []
    file_records = []
    for year, filename in sorted(filenames.items()):
        if year not in payloads:
            raise ValueError(f"missing payload for {year}")
        payload = payloads[year]
        parsed = parse_mayor_vote_csv(payload)
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

    verify_mayor_candidate_coverage(rows, years=sorted(filenames))
    analysis = analyze_mayor_rows(rows)
    verify_mayor_city_totals(analysis, expected=expected_city_totals)
    index = json.loads(index_payload.decode("utf-8-sig"))
    manifest = {
        "build_id": index.get("buildId"),
        "compilation_attribution": index.get("compilationAttribution"),
        "compilation_license": index.get("compilationLicense"),
        "dataset": "TaiwanVotes normalized CEC Taipei mayor CSV",
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
    return analysis, manifest


def rebuild_mayor_from_payloads(
    root: Path,
    index_payload: bytes,
    filenames: Mapping[int, str],
    payloads: Mapping[int, bytes],
    *,
    expected_city_totals=EXPECTED_MAYOR_CITY_TOTALS,
) -> MayorAnalysisBundle:
    """Validate in-memory mayor payloads and write their derived tables."""
    analysis, manifest = prepare_mayor_from_payloads(
        index_payload,
        filenames,
        payloads,
        expected_city_totals=expected_city_totals,
    )
    write_mayor_artifacts(root, analysis, manifest)
    return analysis


def rebuild_age_from_payload(
    root: Path,
    votes: Iterable[VillageResult],
    population_payload: bytes,
    *,
    source_url: str,
) -> None:
    population = parse_population_api_json(
        population_payload,
        expected_yyymm=POPULATION_SNAPSHOT_YYYMM,
    )
    observations, coverage = join_age_and_votes(population, votes)
    if coverage[0] != coverage[1]:
        vote_keys = {(row.district, row.village) for row in votes if row.year == 2024}
        population_keys = {(row.district, row.village) for row in population}
        missing = sorted(vote_keys - population_keys)
        raise ValueError(f"population join did not cover every 2024 vote village: {missing}")
    model = fit_age_model(observations)
    manifest = {
        "bytes": len(population_payload),
        "dataset_page_url": POPULATION_DATASET_URL,
        "encoding": "utf-8",
        "resource": "村里戶數、單一年齡人口（新增區域代碼） API",
        "roc_yyymm": POPULATION_SNAPSHOT_YYYMM,
        "sha256": sha256_hex(population_payload),
        "snapshot": "2023-12",
        "scope": "API page 1; filtered to 臺北市 rows",
        "source_url": source_url,
    }
    write_age_artifacts(root, model, coverage=coverage, source_manifest=manifest)
