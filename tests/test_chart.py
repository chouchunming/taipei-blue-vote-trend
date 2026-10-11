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

    def test_mayor_svg_compares_coalition_and_official_classifications(self):
        coalition = [
            (2002, 64.06, 35.89, 0.05),
            (2006, 57.94, 41.15, 0.89),
            (2010, 55.65, 43.81, 0.54),
            (2014, 40.82, 57.16, 2.02),
            (2018, 40.82, 17.28, 41.90),
            (2022, 42.29, 31.93, 25.78),
        ]
        official = [
            (2002, 64.06, 35.89, 0.05),
            (2006, 53.81, 40.89, 5.30),
            (2010, 55.65, 43.81, 0.54),
            (2014, 40.82, 0.00, 59.18),
            (2018, 40.82, 17.28, 41.90),
            (2022, 42.29, 31.93, 25.78),
        ]
        volatility = [
            (2006, 6.12, 78_700),
            (2010, 2.66, 38_100),
            (2014, 16.13, 241_000),
            (2018, 39.88, 563_800),
            (2022, 16.12, 219_400),
        ]

        svg = chart_module.render_mayor_bloc_svg(
            coalition,
            official,
            volatility,
        )

        for label in (
            "2002–2022 臺北市長",
            "聯盟口徑",
            "官方提名口徑",
            "泛藍",
            "泛綠",
            "其他候選人",
            "最低淨移動規模",
            "2014",
        ):
            self.assertIn(label, svg)
        self.assertEqual(svg.count('class="mayor-volatility-bar"'), 5)
        self.assertIn('role="img"', svg)
        self.assertIn("分類差異", svg)

    def test_mayor_svg_handles_an_all_zero_volatility_series(self):
        coalition = [(2002, 60.0, 40.0, 0.0), (2006, 60.0, 40.0, 0.0)]

        svg = chart_module.render_mayor_bloc_svg(
            coalition,
            coalition,
            [(2006, 0.0, 0)],
        )

        self.assertIn("0.00 pp", svg)
        self.assertEqual(svg.count('class="mayor-volatility-bar"'), 1)

    def test_presidential_mayor_comparison_uses_aligned_separate_panels(self):
        presidential = [
            (2000, 61.69, 37.64, 0.67),
            (2004, 56.53, 43.47, 0.00),
            (2008, 63.03, 36.97, 0.00),
            (2012, 60.46, 39.54, 0.00),
            (2016, 48.04, 51.96, 0.00),
            (2020, 46.35, 53.65, 0.00),
            (2024, 38.08, 38.13, 23.79),
        ]
        mayor = [
            (2002, 64.06, 35.89, 0.05),
            (2006, 57.94, 41.15, 0.89),
            (2010, 55.65, 43.81, 0.54),
            (2014, 40.82, 57.16, 2.02),
            (2018, 40.82, 17.28, 41.90),
            (2022, 42.29, 31.93, 25.78),
        ]

        svg = chart_module.render_presidential_mayor_comparison_svg(
            presidential,
            mayor,
        )

        for label in (
            "總統選舉 2000–2024",
            "市長選舉 2002–2022",
            "泛藍",
            "泛綠",
            "其他候選人",
            "2000",
            "2024",
            "2002",
            "2022",
        ):
            self.assertIn(label, svg)
        self.assertIn('role="img"', svg)
        self.assertIn("兩個面板使用相同的 0–70% 縱軸", svg)
        self.assertEqual(svg.count('class="comparison-panel"'), 2)
        for unsupported in ("Canvas", "CanvasText", "GrayText", "AccentColor", "LinkText"):
            self.assertNotIn(unsupported, svg)
        self.assertIn('fill="#ffffff"', svg)


if __name__ == "__main__":
    unittest.main()
