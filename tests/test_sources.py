import json
import tempfile
import unittest
from pathlib import Path

from taipei_blue_vote.sources import (
    cached_payload,
    csv_url,
    fetch_bytes,
    parse_vote_csv,
    select_taipei_presidential_files,
    sha256_hex,
)


class SourceTests(unittest.TestCase):
    def test_parse_vote_csv_handles_utf8_bom(self):
        payload = (
            "\ufeff選舉名稱,屆期,縣市,鄉鎮市區,村里,選區,號次,候選人,政黨,得票數,當選註記\n"
            "2024年總統副總統選舉,2024,臺北市,信義區,景新里,總統,3,侯友宜,中國國民黨,40,\n"
        ).encode("utf-8")

        row = parse_vote_csv(payload)[0]

        self.assertEqual((row.year, row.district, row.village), (2024, "信義區", "景新里"))
        self.assertEqual((row.candidate, row.votes), ("侯友宜", 40))

    def test_parse_vote_csv_rejects_missing_columns(self):
        payload = "屆期,鄉鎮市區\n2024,信義區\n".encode()

        with self.assertRaisesRegex(ValueError, "missing CSV columns"):
            parse_vote_csv(payload)

    def test_select_files_returns_one_file_for_each_election(self):
        files = [
            {"kind": "votes", "type": "總統", "year": year, "county": "臺北市", "file": f"總統_{year}_臺北市.csv"}
            for year in (2000, 2004, 2008, 2012, 2016, 2020, 2024)
        ]
        files.append({"kind": "votes", "type": "總統", "year": 2024, "county": "新北市", "file": "ignored.csv"})
        payload = json.dumps({"files": files}).encode()

        selected = select_taipei_presidential_files(payload)

        self.assertEqual(tuple(selected), (2000, 2004, 2008, 2012, 2016, 2020, 2024))
        self.assertEqual(selected[2024], "總統_2024_臺北市.csv")

    def test_sha256_hex_is_stable(self):
        self.assertEqual(
            sha256_hex(b"taipei"),
            "8dcbf68858775c8d2546a06eb90ee0e3360742bd5bdef2475ee4892ba73be7f9",
        )

    def test_csv_url_percent_encodes_chinese_filename(self):
        self.assertEqual(
            csv_url("總統_2024_臺北市.csv"),
            "https://taiwanvotes.tw/data/csv/%E7%B8%BD%E7%B5%B1_2024_%E8%87%BA%E5%8C%97%E5%B8%82.csv",
        )

    def test_cached_payload_reuses_cache_until_refresh(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.csv"
            cache = root / "cache" / "source.csv"
            source.write_bytes(b"first")

            self.assertEqual(fetch_bytes(source.as_uri()), b"first")
            self.assertEqual(cached_payload(source.as_uri(), cache), b"first")
            source.write_bytes(b"second")
            self.assertEqual(cached_payload(source.as_uri(), cache), b"first")
            self.assertEqual(cached_payload(source.as_uri(), cache, refresh=True), b"second")


if __name__ == "__main__":
    unittest.main()
