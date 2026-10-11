import json
import tempfile
import unittest
from pathlib import Path

from taipei_blue_vote.artifacts import write_artifacts
from taipei_blue_vote.pipeline import analyze_rows, proxy_results
from taipei_blue_vote.analysis import ELECTION_YEARS, VoteRow


class ArtifactTests(unittest.TestCase):
    def test_write_artifacts_creates_data_manifest_and_charts(self):
        rows = []
        for year in ELECTION_YEARS:
            blue = _blue_candidate(year)
            rows.extend(
                [
                    VoteRow(year, "信義區", "景新里", blue, 70),
                    VoteRow(year, "信義區", "景新里", "其他", 30),
                ]
            )
        analysis = analyze_rows(rows)
        proxies = proxy_results(
            rows,
            [("四四南村所在地", "信義區", "景新里", 2000)],
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_artifacts(
                root,
                analysis,
                proxies,
                {"source": "fixture", "files": []},
            )

            city = (root / "data/derived/city_trend.csv").read_text()
            self.assertIn("year,valid_votes,blue_votes,blue_share", city)
            self.assertIn("2000,100,70,70.0000", city)
            self.assertTrue((root / "data/derived/deep_blue_cohort.csv").exists())
            self.assertTrue((root / "data/derived/military_village_proxies.csv").exists())
            self.assertTrue((root / "data/derived/election_deltas.csv").exists())
            self.assertTrue((root / "data/derived/young_replacement.csv").exists())
            manifest = json.loads((root / "data/derived/source_manifest.json").read_text())
            self.assertEqual(manifest["source"], "fixture")
            svg = (root / "charts/taipei-blue-election-deltas.svg").read_text()
            html = (root / "charts/taipei-blue-election-deltas.html").read_text()
            self.assertIn('role="img"', svg)
            self.assertTrue(html.startswith("<!doctype html>"))


def _blue_candidate(year):
    return {
        2000: "宋楚瑜",
        2004: "連戰",
        2008: "馬英九",
        2012: "馬英九",
        2016: "朱立倫",
        2020: "韓國瑜",
        2024: "侯友宜",
    }[year]


if __name__ == "__main__":
    unittest.main()
