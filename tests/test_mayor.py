import unittest

import taipei_blue_vote.mayor as mayor_module
from taipei_blue_vote.mayor import (
    MayorElectionResult,
    MayorVillageResult,
    aggregate_mayor_villages,
    analyze_mayor_rows,
    bloc_for_candidate,
    mayor_bloc_deltas,
    mayor_electoral_volatility,
    select_mayor_cohort,
    summarize_mayor,
)
from taipei_blue_vote.sources import MAYOR_YEARS, MayorVoteRow


class MayorAnalysisTests(unittest.TestCase):
    def test_candidate_classification(self):
        self.assertEqual(bloc_for_candidate(2006, "宋楚瑜", "coalition"), "blue")
        self.assertEqual(bloc_for_candidate(2006, "周玉蔻", "coalition"), "green")
        self.assertEqual(
            bloc_for_candidate(2006, "宋楚瑜", "official_nomination"),
            "other",
        )
        self.assertEqual(bloc_for_candidate(2014, "柯文哲", "coalition"), "green")
        self.assertEqual(
            bloc_for_candidate(2014, "柯文哲", "official_nomination"),
            "other",
        )
        self.assertEqual(bloc_for_candidate(2018, "柯文哲", "coalition"), "other")
        self.assertEqual(bloc_for_candidate(2022, "黃珊珊", "coalition"), "other")

        with self.assertRaisesRegex(ValueError, "classification"):
            bloc_for_candidate(2022, "黃珊珊", "unknown")

    def test_configuration_rejects_overlap(self):
        blue = {
            year: frozenset({"same"})
            for year in (2002, 2006, 2010, 2014, 2018, 2022)
        }
        green = {
            year: frozenset({"same"})
            for year in (2002, 2006, 2010, 2014, 2018, 2022)
        }

        with self.assertRaisesRegex(ValueError, "overlap"):
            mayor_module.validate_mayor_bloc_configuration(blue, green)

    def test_aggregate_mayor_villages_applies_requested_classification(self):
        rows = [
            MayorVoteRow(2014, "信義區", "三張里", "連勝文", "中國國民黨", 40),
            MayorVoteRow(2014, "信義區", "三張里", "柯文哲", "無黨籍", 55),
            MayorVoteRow(2014, "信義區", "三張里", "次要候選人", "無黨籍", 5),
        ]

        coalition = aggregate_mayor_villages(rows, "coalition")[0]
        official = aggregate_mayor_villages(rows, "official_nomination")[0]

        self.assertEqual(coalition.classification, "coalition")
        self.assertEqual(
            (coalition.blue_votes, coalition.green_votes, coalition.other_votes),
            (40, 55, 5),
        )
        self.assertEqual((coalition.blue_share, coalition.green_share, coalition.other_share), (40.0, 55.0, 5.0))
        self.assertEqual(
            (official.blue_votes, official.green_votes, official.other_votes),
            (40, 0, 60),
        )

    def test_result_shares_require_positive_valid_votes(self):
        village = MayorVillageResult(
            classification="coalition",
            year=2014,
            district="信義區",
            village="三張里",
            valid_votes=0,
            blue_votes=0,
            green_votes=0,
            other_votes=0,
        )
        election = MayorElectionResult(
            classification="coalition",
            year=2014,
            valid_votes=0,
            blue_votes=0,
            green_votes=0,
            other_votes=0,
        )

        for result in (village, election):
            with self.assertRaisesRegex(ValueError, "positive"):
                _ = result.blue_share
            with self.assertRaisesRegex(ValueError, "positive"):
                _ = result.green_share
            with self.assertRaisesRegex(ValueError, "positive"):
                _ = result.other_share

    def test_aggregate_mayor_villages_rejects_invalid_rows(self):
        invalid_rows = (
            (
                MayorVoteRow(2014, "信義區", "三張里", "連勝文", "中國國民黨", -1),
                "non-negative",
            ),
            (
                MayorVoteRow(2024, "信義區", "三張里", "侯友宜", "中國國民黨", 1),
                "unsupported",
            ),
            (
                MayorVoteRow(2014, "信義區", "三張里", "連勝文", "中國國民黨", 0),
                "positive",
            ),
        )

        for row, message in invalid_rows:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    aggregate_mayor_villages([row], "coalition")

    def test_summarize_mayor_aggregates_selected_villages(self):
        rows = [
            MayorVoteRow(2014, "甲區", "甲里", "連勝文", "中國國民黨", 40),
            MayorVoteRow(2014, "甲區", "甲里", "柯文哲", "無黨籍", 60),
            MayorVoteRow(2014, "甲區", "乙里", "連勝文", "中國國民黨", 30),
            MayorVoteRow(2014, "甲區", "乙里", "柯文哲", "無黨籍", 20),
        ]

        result = summarize_mayor(
            aggregate_mayor_villages(rows, "coalition"),
            {('甲區', '甲里')},
        )[0]

        self.assertEqual(result.classification, "coalition")
        self.assertEqual(result.valid_votes, 100)
        self.assertEqual(result.blue_votes, 40)
        self.assertEqual(result.green_votes, 60)
        self.assertEqual(result.other_votes, 0)

    def test_fixed_cohorts_include_threshold_boundaries(self):
        villages = aggregate_mayor_villages(_six_year_rows(), "coalition")

        deep_blue = select_mayor_cohort(villages, "blue", 65.0)
        deep_green = select_mayor_cohort(villages, "green", 45.0)

        self.assertEqual(deep_blue, frozenset({("甲區", "深藍里")}))
        self.assertEqual(deep_green, frozenset({("甲區", "深綠里")}))

    def test_mayor_deltas_and_volatility_measure_three_bloc_change(self):
        city = [
            MayorElectionResult("coalition", 2002, 1000, 600, 350, 50),
            MayorElectionResult("coalition", 2006, 1000, 500, 400, 100),
        ]

        delta = mayor_bloc_deltas(city)[0]
        volatility = mayor_electoral_volatility(city)[0]

        self.assertEqual(delta.classification, "coalition")
        self.assertEqual(delta.blue_share_delta, -10.0)
        self.assertEqual(delta.green_share_delta, 5.0)
        self.assertEqual(delta.other_share_delta, 5.0)
        self.assertEqual(volatility.classification, "coalition")
        self.assertEqual(volatility.volatility_pp, 10.0)
        self.assertEqual(volatility.vote_equivalent, 100)

    def test_analyze_mayor_rows_composes_scenarios_cohorts_and_candidates(self):
        analysis = analyze_mayor_rows(_six_year_rows())

        self.assertEqual(analysis.coalition.classification, "coalition")
        self.assertEqual(
            analysis.official_nomination.classification,
            "official_nomination",
        )
        self.assertEqual(len(analysis.scenarios), 2)
        self.assertEqual(len(analysis.coalition.city), len(MAYOR_YEARS))
        self.assertEqual(len(analysis.coalition.deltas), len(MAYOR_YEARS) - 1)
        self.assertEqual(len(analysis.coalition.volatility), len(MAYOR_YEARS) - 1)
        self.assertEqual(analysis.deep_blue_keys, frozenset({("甲區", "深藍里")}))
        self.assertEqual(analysis.deep_green_keys, frozenset({("甲區", "深綠里")}))
        self.assertEqual(len(analysis.deep_blue), len(MAYOR_YEARS))
        self.assertEqual(len(analysis.deep_green), len(MAYOR_YEARS))

        coalition_ko = next(
            total
            for total in analysis.coalition.candidate_totals
            if total.year == 2014 and total.candidate == "柯文哲"
        )
        official_ko = next(
            total
            for total in analysis.official_nomination.candidate_totals
            if total.year == 2014 and total.candidate == "柯文哲"
        )
        self.assertEqual(
            (coalition_ko.party, coalition_ko.bloc, coalition_ko.votes, coalition_ko.vote_share),
            ("無黨籍", "green", 80, 40.0),
        )
        self.assertEqual(official_ko.bloc, "other")
        official_2014 = next(
            row for row in analysis.official_nomination.city if row.year == 2014
        )
        self.assertEqual(
            (
                official_2014.blue_votes,
                official_2014.green_votes,
                official_2014.other_votes,
            ),
            (120, 0, 80),
        )


def _six_year_rows():
    rows = []
    for year in MAYOR_YEARS:
        blue = _blue_candidate(year)
        green = _green_candidate(year)
        rows.extend(
            [
                MayorVoteRow(year, "甲區", "深藍里", blue, "藍黨", 65),
                MayorVoteRow(year, "甲區", "深藍里", green, _green_party(year), 35),
                MayorVoteRow(year, "甲區", "深綠里", blue, "藍黨", 55),
                MayorVoteRow(year, "甲區", "深綠里", green, _green_party(year), 45),
            ]
        )
    return rows


def _blue_candidate(year):
    return {
        2002: "馬英九",
        2006: "郝龍斌",
        2010: "郝龍斌",
        2014: "連勝文",
        2018: "丁守中",
        2022: "蔣萬安",
    }[year]


def _green_candidate(year):
    return {
        2002: "李應元",
        2006: "謝長廷",
        2010: "蘇貞昌",
        2014: "柯文哲",
        2018: "姚文智",
        2022: "陳時中",
    }[year]


def _green_party(year):
    return "無黨籍" if year == 2014 else "綠黨"


if __name__ == "__main__":
    unittest.main()
