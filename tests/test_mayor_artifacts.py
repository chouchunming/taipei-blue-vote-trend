import json
import tempfile
import unittest
from pathlib import Path

from taipei_blue_vote.mayor import (
    COALITION_BLUE,
    COALITION_GREEN,
    MayorAnalysisBundle,
    analyze_mayor_rows,
)
from taipei_blue_vote.mayor_artifacts import write_mayor_artifacts
from taipei_blue_vote.sources import MAYOR_YEARS, MayorVoteRow


class MayorArtifactTests(unittest.TestCase):
    def test_writer_creates_deterministic_mayor_tables_and_manifest(self):
        analysis = analyze_mayor_rows(_six_year_rows())

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_mayor_artifacts(
                root,
                analysis,
                {"source": "fixture", "files": []},
            )

            derived = root / "data/derived"
            expected_files = {
                "mayor_candidate_totals.csv",
                "mayor_city_trend.csv",
                "mayor_bloc_deltas.csv",
                "mayor_electoral_volatility.csv",
                "mayor_deep_blue_cohort.csv",
                "mayor_deep_green_cohort.csv",
                "mayor_source_manifest.json",
            }
            self.assertEqual(
                {path.name for path in derived.iterdir()},
                expected_files,
            )

            city_lines = (derived / "mayor_city_trend.csv").read_text().splitlines()
            self.assertEqual(
                city_lines[0],
                "classification,year,valid_votes,blue_votes,blue_share,"
                "green_votes,green_share,other_votes,other_share",
            )
            self.assertEqual(
                [line.split(",", 1)[0] for line in city_lines[1:7]],
                ["coalition"] * 6,
            )
            self.assertEqual(
                [line.split(",", 1)[0] for line in city_lines[7:]],
                ["official_nomination"] * 6,
            )
            self.assertIn("coalition,2002,200,115,57.5000,75,37.5000,10,5.0000", city_lines)

            candidate_lines = (
                derived / "mayor_candidate_totals.csv"
            ).read_text().splitlines()
            self.assertEqual(
                candidate_lines[0],
                "classification,year,candidate,party,bloc,votes,vote_share",
            )
            self.assertEqual(candidate_lines[1], "coalition,2002,其他候選人,無黨籍,other,10,5.0000")

            delta = (derived / "mayor_bloc_deltas.csv").read_text()
            self.assertIn("coalition,2006,0.00,0,0.00,0,0.00,0", delta)
            volatility = (derived / "mayor_electoral_volatility.csv").read_text()
            self.assertIn("coalition,2006,0.0000,0,200", volatility)

            blue_cohort = (derived / "mayor_deep_blue_cohort.csv").read_text()
            green_cohort = (derived / "mayor_deep_green_cohort.csv").read_text()
            self.assertIn("coalition,2002,1,100,65,65.0000,0,0.0000", blue_cohort)
            self.assertIn("coalition,2002,1,100,45,45.0000,0,0.0000", green_cohort)
            self.assertNotIn("official_nomination", blue_cohort)
            self.assertNotIn("official_nomination", green_cohort)

            manifest = json.loads(
                (derived / "mayor_source_manifest.json").read_text()
            )
            self.assertEqual(manifest, {"files": [], "source": "fixture"})

    def test_empty_cohorts_produce_header_only_csv_files(self):
        populated = analyze_mayor_rows(_six_year_rows())
        analysis = MayorAnalysisBundle(
            coalition=populated.coalition,
            official_nomination=populated.official_nomination,
            deep_blue_keys=frozenset(),
            deep_blue=(),
            deep_green_keys=frozenset(),
            deep_green=(),
        )

        with tempfile.TemporaryDirectory() as directory:
            derived = Path(directory) / "data/derived"
            write_mayor_artifacts(Path(directory), analysis, {})

            self.assertEqual(
                (derived / "mayor_deep_blue_cohort.csv").read_text(),
                "classification,year,village_count,valid_votes,blue_votes,"
                "blue_share,blue_vote_change_from_2002,"
                "share_point_change_from_2002\n",
            )
            self.assertEqual(
                (derived / "mayor_deep_green_cohort.csv").read_text(),
                "classification,year,village_count,valid_votes,green_votes,"
                "green_share,green_vote_change_from_2002,"
                "share_point_change_from_2002\n",
            )


def _six_year_rows():
    rows = []
    parties = {"blue": "中國國民黨", "green": "民主進步黨", "other": "無黨籍"}
    for year in MAYOR_YEARS:
        blue = sorted(COALITION_BLUE[year])[0]
        green = sorted(COALITION_GREEN[year])[0]
        for village, blue_votes, green_votes in (
            ("藍里", 65, 30),
            ("綠里", 50, 45),
        ):
            rows.extend(
                (
                    MayorVoteRow(year, "測試區", village, blue, parties["blue"], blue_votes),
                    MayorVoteRow(year, "測試區", village, green, parties["green"], green_votes),
                    MayorVoteRow(year, "測試區", village, "其他候選人", parties["other"], 5),
                )
            )
    return rows


if __name__ == "__main__":
    unittest.main()
