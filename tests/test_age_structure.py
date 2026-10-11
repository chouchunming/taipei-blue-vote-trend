import json
import unittest

from taipei_blue_vote.age_structure import (
    PopulationRow,
    join_age_and_votes,
    parse_population_api_json,
)
from taipei_blue_vote.analysis import VillageResult


class AgeStructureTests(unittest.TestCase):
    def test_parse_ris_population_snapshot_and_age_bands(self):
        population = parse_population_api_json(_population_payload(), expected_yyymm="11212")

        self.assertEqual(len(population), 1)
        row = population[0]
        self.assertEqual((row.district, row.village), ("信義區", "景新里"))
        self.assertEqual(row.total, 41)
        self.assertEqual(row.age_20_39, 20)
        self.assertEqual(row.age_40_64, 10)
        self.assertEqual(row.age_65_plus, 11)
        self.assertEqual(row.age_75_plus, 6)

    def test_join_uses_exact_district_and_village_key(self):
        population = [
            PopulationRow("信義區", "景新里", 100, 20, 50, 30, 10),
            PopulationRow("大安區", "景新里", 200, 60, 100, 40, 15),
        ]
        votes = [VillageResult(2024, "信義區", "景新里", 100, 40, 30)]

        observations, coverage = join_age_and_votes(population, votes)

        self.assertEqual(coverage, (1, 1))
        self.assertEqual(len(observations), 1)
        self.assertEqual(observations[0].district, "信義區")
        self.assertAlmostEqual(observations[0].young_share, 0.2)
        self.assertAlmostEqual(observations[0].senior_share, 0.3)
        self.assertAlmostEqual(observations[0].blue_share, 0.4)

    def test_join_reports_unmatched_vote_villages(self):
        population = [PopulationRow("信義區", "景新里", 100, 20, 50, 30, 10)]
        votes = [
            VillageResult(2024, "信義區", "景新里", 100, 40, 30),
            VillageResult(2024, "信義區", "不存在里", 100, 50, 20),
        ]

        observations, coverage = join_age_and_votes(population, votes)

        self.assertEqual(len(observations), 1)
        self.assertEqual(coverage, (1, 2))


def _population_payload():
    ages = {f"people_age_{age:03d}_{sex}": "0" for age in range(100) for sex in ("m", "f")}
    ages.update({"people_age_100up_m": "0", "people_age_100up_f": "0"})
    ages.update(
        {
            "people_age_020_m": "10",
            "people_age_039_f": "10",
            "people_age_040_m": "10",
            "people_age_065_f": "5",
            "people_age_075_m": "5",
            "people_age_100up_f": "1",
        }
    )
    payload = {
        "responseCode": "OD-0101-S",
        "totalPage": "4",
        "page": "1",
        "responseData": [
            {
                "statistic_yyymm": "11212",
                "district_code": "63000020028",
                "site_id": "臺北市信義區",
                "village": "景新里",
                "people_total": "41",
                **ages,
            },
            {
                "statistic_yyymm": "11212",
                "district_code": "65000010001",
                "site_id": "新北市板橋區",
                "village": "留侯里",
                "people_total": "1",
                **{key: "0" for key in ages},
                "people_age_000_m": "1",
            },
        ],
    }
    return json.dumps(payload, ensure_ascii=False).encode()


if __name__ == "__main__":
    unittest.main()
