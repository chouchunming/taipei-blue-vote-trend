import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from taipei_blue_vote.analysis import (
    BLUE_CANDIDATES,
    ELECTION_YEARS,
    GREEN_CANDIDATES,
    VillageResult,
)
from taipei_blue_vote.mayor import COALITION_BLUE, COALITION_GREEN
from taipei_blue_vote.rebuild import (
    PROXY_SPECS,
    prepare_mayor_from_payloads,
    rebuild,
    rebuild_age_from_payload,
    rebuild_from_payloads,
    rebuild_mayor_from_payloads,
)
from taipei_blue_vote.sources import MAYOR_YEARS, sha256_hex


class RebuildTests(unittest.TestCase):
    def test_huanmin_proxy_uses_official_daan_xuefu_location(self):
        self.assertIn(("煥民新村所在地", "大安區", "學府里", 2004), PROXY_SPECS)

    def test_rebuild_from_payloads_runs_end_to_end_without_network(self):
        filenames = {year: f"總統_{year}_臺北市.csv" for year in ELECTION_YEARS}
        index = {
            "schemaVersion": 3,
            "buildId": "fixture",
            "sourceRetrieved": "2026-07-04",
            "sourceModified": "2026-01-26",
            "sourceLicense": "fixture license",
            "compilationLicense": "fixture compilation license",
            "files": [
                {"kind": "votes", "type": "總統", "year": year, "county": "臺北市", "file": filename}
                for year, filename in filenames.items()
            ],
        }
        payloads = {year: _csv_payload(year) for year in ELECTION_YEARS}
        expected = {year: (100, 70, 30, 0) for year in ELECTION_YEARS}

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rebuild_from_payloads(
                root,
                json.dumps(index, ensure_ascii=False).encode(),
                filenames,
                payloads,
                expected_city_totals=expected,
                proxy_specs=(("四四南村所在地", "信義區", "景新里", 2000),),
            )

            city = (root / "data/derived/city_trend.csv").read_text()
            self.assertIn("2024,100,70,70.0000", city)
            manifest = json.loads((root / "data/derived/source_manifest.json").read_text())
            self.assertEqual(manifest["build_id"], "fixture")
            self.assertEqual(len(manifest["files"]), 7)
            self.assertTrue((root / "charts/taipei-blue-election-deltas.svg").exists())
            green_cohort = (root / "data/derived/deep_green_cohort.csv").read_text()
            self.assertEqual(
                green_cohort,
                "year,village_count,valid_votes,green_votes,green_share,"
                "green_vote_change_from_2000,share_point_change_from_2000\n",
            )

    def test_rebuild_age_from_payload_writes_joined_model_artifacts(self):
        votes = []
        population_rows = []
        for district_index, (district, district_code) in enumerate(
            (("信義區", "63000020"), ("大安區", "63000030"))
        ):
            for index in range(4):
                village = f"測試{district_index}{index}里"
                young = 180 + index * 20
                senior = 200 + ((index + district_index) % 3) * 30
                population_rows.append((district, district_code, village, young, senior))
                blue_share = 0.2 + 0.5 * (young / 1000) + 0.8 * (senior / 1000) + district_index * 0.05
                votes.append(
                    VillageResult(
                        2024,
                        district,
                        village,
                        700,
                        round(700 * blue_share),
                        100,
                    )
                )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rebuild_age_from_payload(
                root,
                votes,
                _population_snapshot(population_rows),
                source_url="file:///fixture.csv",
            )

            model = (root / "data/derived/age_model_2024.csv").read_text()
            self.assertIn("young_share", model)
            village = (root / "data/derived/village_age_structure_2024.csv").read_text()
            self.assertEqual(len(village.splitlines()), 9)

    def test_prepare_mayor_from_payloads_returns_analysis_and_manifest(self):
        filenames = {year: f"縣市長_{year}_臺北市.csv" for year in MAYOR_YEARS}
        index_payload = json.dumps(
            {
                "schemaVersion": 3,
                "buildId": "mayor-fixture",
                "sourceRetrieved": "2026-07-04",
                "sourceModified": "2026-01-26",
                "sourceLicense": "fixture license",
                "compilationLicense": "fixture compilation license",
                "files": [
                    {
                        "kind": "votes",
                        "type": "縣市長",
                        "year": year,
                        "county": "臺北市",
                        "file": filename,
                    }
                    for year, filename in filenames.items()
                ],
            },
            ensure_ascii=False,
        ).encode()
        payloads = {year: _mayor_csv_payload(year) for year in MAYOR_YEARS}
        expected = {
            "coalition": {
                year: (len(COALITION_BLUE[year] | COALITION_GREEN[year]),
                       len(COALITION_BLUE[year]),
                       len(COALITION_GREEN[year]),
                       0)
                for year in MAYOR_YEARS
            },
            "official_nomination": {
                2002: (2, 1, 1, 0),
                2006: (4, 1, 1, 2),
                2010: (2, 1, 1, 0),
                2014: (2, 1, 0, 1),
                2018: (2, 1, 1, 0),
                2022: (2, 1, 1, 0),
            },
        }

        analysis, manifest = prepare_mayor_from_payloads(
            index_payload,
            filenames,
            payloads,
            expected_city_totals=expected,
        )

        self.assertEqual(
            tuple(scenario.classification for scenario in analysis.scenarios),
            ("coalition", "official_nomination"),
        )
        self.assertEqual(manifest["dataset"], "TaiwanVotes normalized CEC Taipei mayor CSV")
        self.assertEqual(len(manifest["files"]), 6)
        self.assertEqual(
            [record["year"] for record in manifest["files"]],
            list(MAYOR_YEARS),
        )
        self.assertEqual(manifest["index_sha256"], sha256_hex(index_payload))
        self.assertEqual(
            [record["sha256"] for record in manifest["files"]],
            [sha256_hex(payloads[year]) for year in MAYOR_YEARS],
        )

    def test_prepare_mayor_from_payloads_rejects_internal_year_mismatch(self):
        filenames = {year: f"縣市長_{year}_臺北市.csv" for year in MAYOR_YEARS}
        payloads = {year: _mayor_csv_payload(year) for year in MAYOR_YEARS}
        payloads[2014] = _mayor_csv_payload(2014, internal_year=2018)

        with self.assertRaisesRegex(ValueError, filenames[2014]):
            prepare_mayor_from_payloads(b"{}", filenames, payloads)

    def test_rebuild_mayor_from_payloads_writes_all_mayor_tables(self):
        filenames = {year: f"縣市長_{year}_臺北市.csv" for year in MAYOR_YEARS}
        index_payload = json.dumps(
            {
                "schemaVersion": 3,
                "buildId": "mayor-fixture",
                "files": [
                    {
                        "kind": "votes",
                        "type": "縣市長",
                        "year": year,
                        "county": "臺北市",
                        "file": filename,
                    }
                    for year, filename in filenames.items()
                ],
            },
            ensure_ascii=False,
        ).encode()
        payloads = {year: _mayor_csv_payload(year) for year in MAYOR_YEARS}

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            analysis = rebuild_mayor_from_payloads(
                root,
                index_payload,
                filenames,
                payloads,
                expected_city_totals=_fixture_mayor_totals(),
            )

            self.assertEqual(
                tuple(scenario.classification for scenario in analysis.scenarios),
                ("coalition", "official_nomination"),
            )
            derived = root / "data/derived"
            self.assertTrue((derived / "mayor_candidate_totals.csv").exists())
            self.assertTrue((derived / "mayor_city_trend.csv").exists())
            manifest = json.loads(
                (derived / "mayor_source_manifest.json").read_text()
            )
            self.assertEqual(manifest["build_id"], "mayor-fixture")

    def test_full_rebuild_downloads_mayor_files_from_shared_index(self):
        presidential = {
            year: f"總統_{year}_臺北市.csv" for year in ELECTION_YEARS
        }
        mayor = {year: f"縣市長_{year}_臺北市.csv" for year in MAYOR_YEARS}
        index_payload = json.dumps(
            {
                "files": [
                    *(
                        {
                            "kind": "votes",
                            "type": "總統",
                            "year": year,
                            "county": "臺北市",
                            "file": filename,
                        }
                        for year, filename in presidential.items()
                    ),
                    *(
                        {
                            "kind": "votes",
                            "type": "縣市長",
                            "year": year,
                            "county": "臺北市",
                            "file": filename,
                        }
                        for year, filename in mayor.items()
                    ),
                ]
            },
            ensure_ascii=False,
        ).encode()

        def cached_fixture(_url, path, **_kwargs):
            if path.name == "index.json":
                return index_payload
            if path.name == "ris-village-single-age-population-11212-page1.json":
                return b"population"
            return path.name.encode()

        with tempfile.TemporaryDirectory() as directory, patch(
            "taipei_blue_vote.rebuild.cached_payload", side_effect=cached_fixture
        ), patch(
            "taipei_blue_vote.rebuild.rebuild_from_payloads"
        ) as presidential_rebuild, patch(
            "taipei_blue_vote.rebuild.rebuild_mayor_from_payloads"
        ) as mayor_rebuild, patch(
            "taipei_blue_vote.rebuild.rebuild_age_from_payload"
        ), patch(
            "taipei_blue_vote.rebuild.write_mayor_charts"
        ) as mayor_charts:
            presidential_rebuild.return_value.villages = ()
            presidential_rebuild.return_value.city = ()
            mayor_rebuild.return_value = object()
            root = Path(directory)
            rebuild(root, refresh=True)

            mayor_rebuild.assert_called_once_with(
                root,
                index_payload,
                mayor,
                {year: filename.encode() for year, filename in mayor.items()},
            )
            mayor_charts.assert_called_once_with(
                root,
                mayor_rebuild.return_value,
                presidential_rebuild.return_value.city,
            )


def _csv_payload(year):
    header = "屆期,鄉鎮市區,村里,候選人,得票數\n"
    candidates = sorted(BLUE_CANDIDATES[year])
    blue_votes = [70] if len(candidates) == 1 else [35, 35]
    rows = [
        f"{year},信義區,景新里,{candidate},{votes}\n"
        for candidate, votes in zip(candidates, blue_votes)
    ]
    rows.append(f"{year},信義區,景新里,{next(iter(GREEN_CANDIDATES[year]))},30\n")
    return (header + "".join(rows)).encode()


def _mayor_csv_payload(year, *, internal_year=None):
    header = "選舉名稱,屆期,縣市,鄉鎮市區,村里,選區,號次,候選人,政黨,得票數,當選註記\n"
    row_year = year if internal_year is None else internal_year
    candidates = sorted(COALITION_BLUE[year] | COALITION_GREEN[year])
    rows = [
        f"{year}年臺北市市長選舉,{row_year},臺北市,測試區,測試里,市長,{number},"
        f"{candidate},測試政黨,1,\n"
        for number, candidate in enumerate(candidates, start=1)
    ]
    return (header + "".join(rows)).encode()


def _fixture_mayor_totals():
    return {
        "coalition": {
            year: (
                len(COALITION_BLUE[year] | COALITION_GREEN[year]),
                len(COALITION_BLUE[year]),
                len(COALITION_GREEN[year]),
                0,
            )
            for year in MAYOR_YEARS
        },
        "official_nomination": {
            2002: (2, 1, 1, 0),
            2006: (4, 1, 1, 2),
            2010: (2, 1, 1, 0),
            2014: (2, 1, 0, 1),
            2018: (2, 1, 1, 0),
            2022: (2, 1, 1, 0),
        },
    }


def _population_snapshot(specifications):
    rows = []
    for sequence, (district, code, village, young, senior) in enumerate(specifications, start=1):
        ages = {
            f"people_age_{age:03d}_{sex}": "0"
            for age in range(100)
            for sex in ("m", "f")
        }
        ages["people_age_020_m"] = str(young)
        ages["people_age_040_m"] = str(1000 - young - senior)
        ages["people_age_065_m"] = str(senior)
        ages["people_age_100up_m"] = "0"
        ages["people_age_100up_f"] = "0"
        rows.append(
            {
                "statistic_yyymm": "11212",
                "district_code": f"{code}{sequence:03d}",
                "site_id": f"臺北市{district}",
                "village": village,
                "people_total": "1000",
                **ages,
            }
        )
    return json.dumps(
        {
            "responseCode": "OD-0101-S",
            "totalPage": "1",
            "page": "1",
            "responseData": rows,
        },
        ensure_ascii=False,
    ).encode()


if __name__ == "__main__":
    unittest.main()
