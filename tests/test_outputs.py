import tempfile
import unittest
from pathlib import Path

from taipei_blue_vote.outputs import write_csv, write_json


class OutputTests(unittest.TestCase):
    def test_write_csv_is_deterministic(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rows.csv"

            write_csv(path, ["year", "votes"], [[2024, 40]])

            self.assertEqual(path.read_text(), "year,votes\n2024,40\n")

    def test_write_json_preserves_chinese_and_sorts_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"

            write_json(path, {"z": 1, "名稱": "臺北市", "a": 2})

            self.assertEqual(
                path.read_text(),
                '{\n  "a": 2,\n  "z": 1,\n  "名稱": "臺北市"\n}\n',
            )


if __name__ == "__main__":
    unittest.main()
