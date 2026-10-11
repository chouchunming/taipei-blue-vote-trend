import unittest

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


if __name__ == "__main__":
    unittest.main()
