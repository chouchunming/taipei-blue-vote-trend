import unittest

import taipei_blue_vote.chart as chart_module
from taipei_blue_vote.chart import render_html, render_svg


class ChartTests(unittest.TestCase):
    def setUp(self):
        self.rows = [
            (2004, -5.16, -81232),
            (2008, 6.50, 113676),
            (2012, -2.58, -41381),
            (2016, -12.41, -269870),
            (2020, -1.69, 56304),
            (2024, -8.26, -169341),
        ]

    def test_svg_contains_both_metrics_and_all_signed_values(self):
        svg = render_svg(self.rows)

        expected = (
            "得票率增減（百分點）",
            "選票增減（票）",
            "−5.16 pp",
            "+6.50 pp",
            "−12.41 pp",
            "−8.26 pp",
            "−81,232",
            "+113,676",
            "−269,870",
            "+56,304",
            "−169,341",
        )
        for label in expected:
            self.assertIn(label, svg)
        self.assertIn('role="img"', svg)
        self.assertIn("2000 年為基準", svg)
        self.assertEqual(svg.count('class="bar negative"'), 9)
        self.assertEqual(svg.count('class="bar positive"'), 3)

    def test_html_is_standalone_and_embeds_svg(self):
        html = render_html(render_svg(self.rows))

        self.assertTrue(html.startswith("<!doctype html>"))
        self.assertIn("<html lang=\"zh-Hant\">", html)
        self.assertIn("<svg", html)
        self.assertNotIn("window.openai", html)

    def test_svg_avoids_browser_only_system_colors(self):
        svg = render_svg(self.rows)

        for unsupported in ("Canvas", "CanvasText", "GrayText", "AccentColor", "LinkText"):
            self.assertNotIn(unsupported, svg)
        self.assertIn('fill="#ffffff"', svg)

    def test_bloc_svg_contains_shares_and_six_volatility_bars(self):
        blocs = [
            (2000, 61.69, 37.64, 0.67),
            (2004, 56.53, 43.47, 0.0),
            (2008, 63.03, 36.97, 0.0),
            (2012, 60.46, 39.54, 0.0),
            (2016, 48.04, 51.96, 0.0),
            (2020, 46.35, 53.65, 0.0),
            (2024, 38.08, 38.13, 23.79),
        ]
        volatility = [
            (2004, 5.82, 92_000),
            (2008, 6.50, 104_000),
            (2012, 2.58, 41_000),
            (2016, 12.41, 181_000),
            (2020, 1.69, 28_000),
            (2024, 23.79, 366_854),
        ]

        svg = chart_module.render_bloc_svg(blocs, volatility)

        for label in (
            "泛藍",
            "泛綠",
            "其他候選人",
            "最低淨移動規模",
            "23.79%",
            "23.79 pp",
            "366,854 票等值",
        ):
            self.assertIn(label, svg)
        self.assertEqual(svg.count('class="volatility-bar"'), 6)
        self.assertIn('role="img"', svg)

    def test_bloc_svg_handles_an_all_zero_volatility_series(self):
        blocs = [(2000, 70.0, 30.0, 0.0), (2004, 70.0, 30.0, 0.0)]

        svg = chart_module.render_bloc_svg(blocs, [(2004, 0.0, 0)])

        self.assertIn("0.00 pp", svg)
        self.assertEqual(svg.count('class="volatility-bar"'), 1)


if __name__ == "__main__":
    unittest.main()
