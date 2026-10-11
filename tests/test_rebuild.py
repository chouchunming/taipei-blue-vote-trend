import json
import tempfile
import unittest
from pathlib import Path

from taipei_blue_vote.analysis import BLUE_CANDIDATES, ELECTION_YEARS
from taipei_blue_vote.rebuild import PROXY_SPECS, rebuild_from_payloads


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
        expected = {year: (100, 70) for year in ELECTION_YEARS}

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


def _csv_payload(year):
    header = "屆期,鄉鎮市區,村里,候選人,得票數\n"
    candidates = sorted(BLUE_CANDIDATES[year])
    blue_votes = [70] if len(candidates) == 1 else [35, 35]
    rows = [
        f"{year},信義區,景新里,{candidate},{votes}\n"
        for candidate, votes in zip(candidates, blue_votes)
    ]
    rows.append(f"{year},信義區,景新里,其他,30\n")
    return (header + "".join(rows)).encode()


if __name__ == "__main__":
    unittest.main()
