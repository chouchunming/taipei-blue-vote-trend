import unittest

from taipei_blue_vote.age_structure import (
    AgeObservation,
    fit_age_model,
    weighted_least_squares,
)


class AgeModelTests(unittest.TestCase):
    def test_weighted_least_squares_recovers_exact_line(self):
        coefficients = weighted_least_squares(
            [[1.0, 0.0], [1.0, 1.0], [1.0, 2.0]],
            [1.0, 3.0, 5.0],
            [1.0, 2.0, 1.0],
        )

        self.assertAlmostEqual(coefficients[0], 1.0)
        self.assertAlmostEqual(coefficients[1], 2.0)

    def test_weighted_least_squares_rejects_singular_design(self):
        with self.assertRaisesRegex(ValueError, "singular"):
            weighted_least_squares(
                [[1.0, 1.0], [1.0, 1.0]],
                [1.0, 2.0],
                [1.0, 1.0],
            )

    def test_age_model_recovers_age_effects_with_district_fixed_effect(self):
        observations = []
        specifications = [
            ("信義區", 0.18, 0.20),
            ("信義區", 0.22, 0.25),
            ("信義區", 0.27, 0.18),
            ("信義區", 0.31, 0.28),
            ("大安區", 0.19, 0.22),
            ("大安區", 0.24, 0.30),
            ("大安區", 0.29, 0.19),
            ("大安區", 0.33, 0.26),
        ]
        for index, (district, young, senior) in enumerate(specifications):
            district_effect = 0.10 if district == "大安區" else 0.0
            blue_share = 0.20 + 0.50 * young + 0.80 * senior + district_effect
            observations.append(
                AgeObservation(
                    district=district,
                    village=f"第{index}里",
                    population=1000,
                    young_share=young,
                    middle_share=1 - young - senior,
                    senior_share=senior,
                    age_75_plus_share=senior / 2,
                    valid_votes=700 + index,
                    blue_votes=round((700 + index) * blue_share),
                    blue_share=blue_share,
                )
            )

        model = fit_age_model(observations)
        coefficients = {row.name: row for row in model.coefficients}

        self.assertAlmostEqual(coefficients["young_share"].coefficient, 0.50, places=9)
        self.assertAlmostEqual(coefficients["senior_share"].coefficient, 0.80, places=9)
        self.assertAlmostEqual(coefficients["young_share"].effect_for_10pp, 5.0, places=9)
        self.assertAlmostEqual(coefficients["senior_share"].effect_for_10pp, 8.0, places=9)
        self.assertAlmostEqual(model.weighted_r2, 1.0, places=9)
        self.assertEqual(len(model.predictions), 8)


if __name__ == "__main__":
    unittest.main()
