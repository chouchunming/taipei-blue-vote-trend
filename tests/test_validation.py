import unittest

from taipei_blue_vote.analysis import (
    BLUE_CANDIDATES,
    ELECTION_YEARS,
    GREEN_CANDIDATES,
    ElectionResult,
    VoteRow,
)
from taipei_blue_vote.validation import verify_candidate_coverage, verify_city_totals


class ValidationTests(unittest.TestCase):
    def test_candidate_coverage_accepts_all_configured_candidates(self):
        rows = [
            VoteRow(year, "區", "里", candidate, 1)
            for year in ELECTION_YEARS
            for candidate in BLUE_CANDIDATES[year] | GREEN_CANDIDATES[year]
        ]

        verify_candidate_coverage(rows)

    def test_candidate_coverage_rejects_missing_candidate(self):
        rows = [VoteRow(2024, "區", "里", "賴清德", 1)]

        with self.assertRaisesRegex(ValueError, "missing configured blue candidates"):
            verify_candidate_coverage(rows, years=(2024,))

    def test_candidate_coverage_rejects_missing_green_candidate(self):
        rows = [VoteRow(2024, "區", "里", "侯友宜", 1)]

        with self.assertRaisesRegex(ValueError, "missing configured green candidates"):
            verify_candidate_coverage(rows, years=(2024,))

    def test_city_total_check_detects_source_or_classification_drift(self):
        actual = [ElectionResult(2024, 100, 40, 30, 30, 30)]

        with self.assertRaisesRegex(ValueError, "city total mismatch"):
            verify_city_totals(actual, expected={2024: (100, 41, 30, 29)})

        verify_city_totals(actual, expected={2024: (100, 40, 30, 30)})


if __name__ == "__main__":
    unittest.main()
