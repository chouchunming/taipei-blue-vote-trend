import json
import unittest

from taipei_blue_vote.sources import (
    MayorVoteRow,
    parse_mayor_vote_csv,
    select_taipei_mayor_files,
)


MAYOR_FILES = [
    {
        "kind": "votes",
        "type": "縣市長",
        "year": 2002,
        "county": "臺北市",
        "file": "縣市長_2001-02_臺北市.csv",
    },
    {
        "kind": "votes",
        "type": "縣市長",
        "year": 2006,
        "county": "臺北市",
        "file": "縣市長_2005-06_臺北市.csv",
    },
    {
        "kind": "votes",
        "type": "縣市長",
        "year": 2010,
        "county": "臺北市",
        "file": "縣市長_2009-10_臺北市.csv",
    },
    {
        "kind": "votes",
        "type": "縣市長",
        "year": 2014,
        "county": "臺北市",
        "file": "縣市長_2014_臺北市.csv",
    },
    {
        "kind": "votes",
        "type": "縣市長",
        "year": 2018,
        "county": "臺北市",
        "file": "縣市長_2018_臺北市.csv",
    },
    {
        "kind": "votes",
        "type": "縣市長",
        "year": 2022,
        "county": "臺北市",
        "file": "縣市長_2022_臺北市.csv",
    },
]


def _index_payload(files):
    return json.dumps({"files": files}).encode()


class MayorSourceTests(unittest.TestCase):
    def test_select_taipei_mayor_files_returns_each_election(self):
        files = MAYOR_FILES + [
            {
                "kind": "votes",
                "type": "總統",
                "year": 2024,
                "county": "臺北市",
                "file": "總統_2024_臺北市.csv",
            },
            {
                "kind": "votes",
                "type": "縣市議員",
                "year": 2022,
                "county": "臺北市",
                "file": "縣市議員_2022_臺北市.csv",
            },
        ]

        self.assertEqual(
            select_taipei_mayor_files(_index_payload(files)),
            {
                2002: "縣市長_2001-02_臺北市.csv",
                2006: "縣市長_2005-06_臺北市.csv",
                2010: "縣市長_2009-10_臺北市.csv",
                2014: "縣市長_2014_臺北市.csv",
                2018: "縣市長_2018_臺北市.csv",
                2022: "縣市長_2022_臺北市.csv",
            },
        )

    def test_select_taipei_mayor_files_rejects_missing_year(self):
        files = [item for item in MAYOR_FILES if item["year"] != 2014]

        with self.assertRaisesRegex(ValueError, "2014"):
            select_taipei_mayor_files(_index_payload(files))

    def test_select_taipei_mayor_files_rejects_duplicate_year(self):
        files = MAYOR_FILES + [
            {
                "kind": "votes",
                "type": "縣市長",
                "year": 2018,
                "county": "臺北市",
                "file": "duplicate.csv",
            }
        ]

        with self.assertRaisesRegex(ValueError, "2018"):
            select_taipei_mayor_files(_index_payload(files))

    def test_parse_mayor_vote_csv_handles_utf8_bom(self):
        payload = (
            "\ufeff選舉名稱,屆期,縣市,鄉鎮市區,村里,選區,號次,候選人,政黨,得票數,當選註記\n"
            "2014年臺北市市長選舉,2014,臺北市, 信義區 , 三張里 ,市長,2, 柯文哲 , 無黨籍 ,956,\n"
        ).encode("utf-8")

        row = parse_mayor_vote_csv(payload)[0]

        self.assertEqual(
            row,
            MayorVoteRow(2014, "信義區", "三張里", "柯文哲", "無黨籍", 956),
        )

    def test_parse_mayor_vote_csv_normalizes_cross_year_election_term(self):
        payload = (
            "選舉名稱,屆期,縣市,鄉鎮市區,村里,選區,號次,候選人,政黨,得票數,當選註記\n"
            "2002年直轄市長選舉,2001/02,臺北市,北投區,建民里,臺北市,1,李應元,民主進步黨,1277,\n"
        ).encode()

        row = parse_mayor_vote_csv(payload)[0]

        self.assertEqual(row.year, 2002)

    def test_parse_mayor_vote_csv_rejects_missing_party_column(self):
        payload = "屆期,鄉鎮市區,村里,候選人,得票數\n2014,信義區,三張里,柯文哲,956\n".encode()

        with self.assertRaisesRegex(ValueError, "missing CSV columns: 政黨"):
            parse_mayor_vote_csv(payload)

    def test_parse_mayor_vote_csv_rejects_malformed_rows(self):
        payload = (
            "屆期,鄉鎮市區,村里,候選人,政黨,得票數\n"
            "2014,信義區,三張里,柯文哲,無黨籍,not-a-number\n"
        ).encode()

        with self.assertRaisesRegex(ValueError, "invalid mayor vote row:"):
            parse_mayor_vote_csv(payload)


if __name__ == "__main__":
    unittest.main()
