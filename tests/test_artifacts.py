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
        for index, year in enumerate(ELECTION_YEARS):
            blue = _blue_candidate(year)
            green = _green_candidate(year)
            rows.extend(
                [
                    VoteRow(year, "信義區", "景新里", blue, 70 - index),
                    VoteRow(year, "信義區", "景新里", green, 30 + index),
                    VoteRow(year, "信義區", "綠里", blue, 55 - index),
                    VoteRow(year, "信義區", "綠里", green, 45 + index),
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
            self.assertIn("green_votes,green_share,other_votes,other_share", city.splitlines()[0])
            self.assertIn("2000,200,125,62.5000,75,37.5000,0,0.0000", city)
            self.assertTrue((root / "data/derived/deep_blue_cohort.csv").exists())
            green_cohort = (root / "data/derived/deep_green_cohort.csv").read_text()
            self.assertIn("2000,1,100,45,45.0000,0,0.0000", green_cohort)
            bloc_deltas = (root / "data/derived/bloc_deltas.csv").read_text()
            self.assertIn("2004,-1.00,-2,1.00,2,0.00,0", bloc_deltas)
            volatility = (root / "data/derived/electoral_volatility.csv").read_text()
            self.assertIn("2004,1.0000,2,200", volatility)
            self.assertTrue((root / "data/derived/military_village_proxies.csv").exists())
            self.assertTrue((root / "data/derived/election_deltas.csv").exists())
            self.assertTrue((root / "data/derived/young_replacement.csv").exists())
            manifest = json.loads((root / "data/derived/source_manifest.json").read_text())
            self.assertEqual(manifest["source"], "fixture")
            svg = (root / "charts/taipei-blue-election-deltas.svg").read_text()
            html = (root / "charts/taipei-blue-election-deltas.html").read_text()
            self.assertIn('role="img"', svg)
            self.assertTrue(html.startswith("<!doctype html>"))
            bloc_svg = (root / "charts/taipei-bloc-and-volatility.svg").read_text()
            bloc_html = (root / "charts/taipei-bloc-and-volatility.html").read_text()
            self.assertIn("泛綠", bloc_svg)
            self.assertIn("最低淨移動規模", bloc_svg)
            self.assertTrue(bloc_html.startswith("<!doctype html>"))


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


def _green_candidate(year):
    return {
        2000: "陳水扁",
        2004: "陳水扁",
        2008: "謝長廷",
        2012: "蔡英文",
        2016: "蔡英文",
        2020: "蔡英文",
        2024: "賴清德",
    }[year]


if __name__ == "__main__":
    unittest.main()
