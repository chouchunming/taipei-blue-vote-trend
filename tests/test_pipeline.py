import unittest

from taipei_blue_vote.analysis import ELECTION_YEARS, VoteRow
from taipei_blue_vote.pipeline import analyze_rows, proxy_results


class PipelineTests(unittest.TestCase):
    def test_analyze_rows_builds_city_cohort_and_deltas(self):
        rows = []
        for index, year in enumerate(ELECTION_YEARS):
            blue = _blue_candidate(year)
            green = _green_candidate(year)
            rows.extend(
                [
                    VoteRow(year, "甲區", "甲里", blue, 70 - index),
                    VoteRow(year, "甲區", "甲里", green, 25 + index),
                    VoteRow(year, "甲區", "甲里", "其他", 5),
                    VoteRow(year, "甲區", "乙里", blue, 60 - index),
                    VoteRow(year, "甲區", "乙里", green, 35 + index),
                    VoteRow(year, "甲區", "乙里", "其他", 5),
                    VoteRow(year, "甲區", "綠里", blue, 50 - index),
                    VoteRow(year, "甲區", "綠里", green, 45 + index),
                    VoteRow(year, "甲區", "綠里", "其他", 5),
                ]
            )

        analysis = analyze_rows(rows)

        self.assertEqual(analysis.cohort_keys, frozenset({("甲區", "甲里")}))
        self.assertEqual(analysis.green_cohort_keys, frozenset({("甲區", "綠里")}))
        self.assertEqual(analysis.city[0].blue_votes, 180)
        self.assertEqual(analysis.city[0].green_votes, 105)
        self.assertEqual(analysis.city[-1].blue_votes, 162)
        self.assertEqual(analysis.cohort[0].blue_share, 70.0)
        self.assertEqual(analysis.green_cohort[0].green_share, 45.0)
        self.assertEqual(analysis.deltas[-1], (2024, -1.0, -3))
        self.assertEqual(len(analysis.bloc_deltas), 6)
        self.assertEqual(len(analysis.volatility), 6)

    def test_proxy_results_labels_comparability(self):
        rows = [
            VoteRow(2000, "信義區", "景新里", "宋楚瑜", 70),
            VoteRow(2000, "信義區", "景新里", "其他", 30),
            VoteRow(2004, "信義區", "景新里", "連戰", 60),
            VoteRow(2004, "信義區", "景新里", "其他", 40),
        ]

        results = proxy_results(
            rows,
            [("四四南村所在地", "信義區", "景新里", 2000)],
        )

        self.assertEqual(results[0].proxy_name, "四四南村所在地")
        self.assertEqual(results[0].blue_share, 70.0)
        self.assertTrue(results[0].continuously_comparable)


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
