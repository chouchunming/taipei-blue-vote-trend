import unittest

from taipei_blue_vote.analysis import (
    ELECTION_YEARS,
    VoteRow,
    aggregate_villages,
    election_deltas,
    estimate_young_votes,
    select_fixed_cohort,
    summarize,
)


class AnalysisTests(unittest.TestCase):
    def test_aggregate_villages_counts_only_configured_blue_candidates(self):
        rows = [
            VoteRow(2024, "信義區", "景新里", "侯友宜", 40),
            VoteRow(2024, "信義區", "景新里", "柯文哲", 30),
            VoteRow(2024, "信義區", "景新里", "賴清德", 30),
        ]

        result = aggregate_villages(rows)[0]

        self.assertEqual(result.valid_votes, 100)
        self.assertEqual(result.blue_votes, 40)
        self.assertEqual(result.ko_votes, 30)
        self.assertEqual(result.blue_share, 40.0)

    def test_aggregate_villages_rejects_negative_votes(self):
        rows = [VoteRow(2024, "信義區", "景新里", "侯友宜", -1)]

        with self.assertRaisesRegex(ValueError, "non-negative"):
            aggregate_villages(rows)

    def test_fixed_cohort_requires_threshold_minimum_and_every_year(self):
        rows = []
        for year in ELECTION_YEARS:
            rows.extend(
                [
                    VoteRow(year, "甲區", "甲里", _blue_candidate(year), 70),
                    VoteRow(year, "甲區", "甲里", "其他", 30),
                    VoteRow(year, "甲區", "乙里", _blue_candidate(year), 64),
                    VoteRow(year, "甲區", "乙里", "其他", 36),
                ]
            )
        rows.extend(
            [
                VoteRow(2000, "甲區", "丙里", "宋楚瑜", 80),
                VoteRow(2000, "甲區", "丙里", "其他", 20),
            ]
        )

        cohort = select_fixed_cohort(aggregate_villages(rows), threshold=65.0, minimum_valid=100)

        self.assertEqual(cohort, frozenset({("甲區", "甲里")}))

    def test_summarize_aggregates_selected_villages(self):
        rows = [
            VoteRow(2024, "甲區", "甲里", "侯友宜", 40),
            VoteRow(2024, "甲區", "甲里", "其他", 60),
            VoteRow(2024, "甲區", "乙里", "侯友宜", 30),
            VoteRow(2024, "甲區", "乙里", "其他", 20),
        ]

        result = summarize(aggregate_villages(rows), {("甲區", "甲里")})[0]

        self.assertEqual(result.valid_votes, 100)
        self.assertEqual(result.blue_votes, 40)
        self.assertEqual(result.blue_share, 40.0)

    def test_election_deltas_compare_adjacent_elections(self):
        rows = [(2000, 61.6887, 979102), (2004, 56.5321, 897870)]

        self.assertEqual(election_deltas(rows), [(2004, -5.16, -81232)])

    def test_young_estimate_returns_low_central_high(self):
        estimate = estimate_young_votes(571536, 0.715, 0.135, 0.15, 0.16)

        self.assertEqual(estimate, (55168, 61297, 65384))


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
