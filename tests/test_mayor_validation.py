import unittest

from taipei_blue_vote.mayor import analyze_mayor_rows
from taipei_blue_vote.sources import MayorVoteRow
from taipei_blue_vote.validation import (
    EXPECTED_MAYOR_CITY_TOTALS,
    verify_mayor_candidate_coverage,
    verify_mayor_city_totals,
)


EXPECTED_TOTALS = {
    "coalition": {
        2002: (1_361_913, 873_102, 488_811, 0),
        2006: (1_286_089, 745_366, 529_241, 11_482),
        2010: (1_433_736, 797_865, 628_129, 7_742),
        2014: (1_494_046, 609_932, 853_983, 30_131),
        2018: (1_413_870, 577_096, 244_342, 592_432),
        2022: (1_360_951, 575_590, 434_558, 350_803),
    },
    "official_nomination": {
        2002: (1_361_913, 873_102, 488_811, 0),
        2006: (1_286_089, 692_085, 525_869, 68_135),
        2010: (1_433_736, 797_865, 628_129, 7_742),
        2014: (1_494_046, 609_932, 0, 884_114),
        2018: (1_413_870, 577_096, 244_342, 592_432),
        2022: (1_360_951, 575_590, 434_558, 350_803),
    },
}


class MayorValidationTests(unittest.TestCase):
    def test_expected_mayor_city_totals_match_official_results(self):
        self.assertEqual(EXPECTED_MAYOR_CITY_TOTALS, EXPECTED_TOTALS)
        verify_mayor_city_totals(analyze_mayor_rows(_official_total_rows()))

    def test_mayor_city_total_check_names_scenario_and_year(self):
        expected = {
            scenario: dict(totals)
            for scenario, totals in EXPECTED_MAYOR_CITY_TOTALS.items()
        }
        valid, blue, green, other = expected["coalition"][2014]
        expected["coalition"][2014] = (valid, blue, green + 1, other)

        with self.assertRaisesRegex(ValueError, "coalition.*2014"):
            verify_mayor_city_totals(
                analyze_mayor_rows(_official_total_rows()),
                expected=expected,
            )

    def test_mayor_candidate_coverage_names_missing_configured_candidate(self):
        rows = [row for row in _official_total_rows() if row.candidate != "宋楚瑜"]

        with self.assertRaisesRegex(ValueError, "coalition.*2006.*宋楚瑜"):
            verify_mayor_candidate_coverage(rows)


def _official_total_rows():
    votes = {
        2002: (("馬英九", 873_102), ("李應元", 488_811)),
        2006: (
            ("郝龍斌", 692_085),
            ("宋楚瑜", 53_281),
            ("謝長廷", 525_869),
            ("周玉蔻", 3_372),
            ("其他候選人", 11_482),
        ),
        2010: (("郝龍斌", 797_865), ("蘇貞昌", 628_129), ("其他候選人", 7_742)),
        2014: (("連勝文", 609_932), ("柯文哲", 853_983), ("其他候選人", 30_131)),
        2018: (("丁守中", 577_096), ("姚文智", 244_342), ("柯文哲", 592_432)),
        2022: (("蔣萬安", 575_590), ("陳時中", 434_558), ("黃珊珊", 350_803)),
    }
    return [
        MayorVoteRow(year, "測試區", "測試里", candidate, "測試政黨", count)
        for year, candidates in votes.items()
        for candidate, count in candidates
    ]


if __name__ == "__main__":
    unittest.main()
