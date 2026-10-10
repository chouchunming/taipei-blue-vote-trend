# Taipei Blue Vote Trend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and publish a tested, reproducible Taipei presidential-vote analysis with derived CSV data and GitHub-previewable charts.

**Architecture:** Keep election arithmetic in pure functions over typed records, isolate downloading and CSV parsing at the boundary, and generate committed derived artifacts through one CLI. Render a static SVG for GitHub and a standalone HTML companion from the same computed delta rows.

**Tech Stack:** Python 3.11+ standard library, `unittest`, CSV/JSON, SVG/HTML, GitHub Actions.

## Global Constraints

- Count only the candidates listed in the approved design as pan-blue.
- Never count 柯文哲 as pan-blue; report him only as a separate non-green comparison.
- Use exact `(district, village)` keys for longitudinal matching.
- Treat military-village rows as geographic proxies, not resident ancestry.
- Treat candidate-by-age output as an estimate with an explicit range.
- Keep runtime dependencies at zero.
- Commit compact derived outputs; keep downloaded raw CSV files out of Git.

---

### Task 1: Pure election analysis

**Files:**
- Create: `src/taipei_blue_vote/__init__.py`
- Create: `src/taipei_blue_vote/analysis.py`
- Create: `tests/test_analysis.py`

**Interfaces:**
- Consumes: normalized `VoteRow(year, district, village, candidate, votes)` records.
- Produces: `aggregate_geography`, `election_deltas`, `select_fixed_cohort`, and `estimate_young_votes`.

- [ ] **Step 1: Write failing tests for classification, totals, cohort matching, deltas, and the youth range**

```python
import unittest

from taipei_blue_vote.analysis import (
    VoteRow,
    aggregate_geography,
    election_deltas,
    estimate_young_votes,
    select_fixed_cohort,
)


class AnalysisTests(unittest.TestCase):
    def test_aggregate_geography_sums_only_configured_blue_candidates(self):
        rows = [
            VoteRow(2024, "信義區", "景新里", "侯友宜", 40),
            VoteRow(2024, "信義區", "景新里", "柯文哲", 30),
            VoteRow(2024, "信義區", "景新里", "賴清德", 30),
        ]
        result = aggregate_geography(rows)
        self.assertEqual(result[0].valid_votes, 100)
        self.assertEqual(result[0].blue_votes, 40)
        self.assertEqual(result[0].blue_share, 40.0)

    def test_fixed_cohort_requires_threshold_and_all_years(self):
        village_years = {
            ("甲區", "甲里"): {2000: (70, 100), 2004: (60, 100)},
            ("甲區", "乙里"): {2000: (64, 100), 2004: (55, 100)},
            ("甲區", "丙里"): {2000: (80, 100)},
        }
        self.assertEqual(
            select_fixed_cohort(village_years, [2000, 2004], 65.0, 100),
            {("甲區", "甲里")},
        )

    def test_election_deltas_compare_adjacent_elections(self):
        rows = [(2000, 61.69, 979102), (2004, 56.53, 897870)]
        self.assertEqual(election_deltas(rows), [(2004, -5.16, -81232)])

    def test_young_estimate_returns_low_central_high(self):
        estimate = estimate_young_votes(571536, 0.715, 0.135, 0.15, 0.16)
        self.assertEqual(estimate, (55168, 61297, 65384))
```

- [ ] **Step 2: Run the test and verify RED**

Run: `PYTHONPATH=src caffeinate -i -m python3 -m unittest tests.test_analysis -v`

Expected: import failure because `taipei_blue_vote.analysis` does not exist.

- [ ] **Step 3: Implement the minimal typed analysis functions**

```python
from dataclasses import dataclass
from collections import defaultdict

BLUE_CANDIDATES = {
    2000: frozenset({"宋楚瑜", "連戰"}),
    2004: frozenset({"連戰"}),
    2008: frozenset({"馬英九"}),
    2012: frozenset({"馬英九", "宋楚瑜"}),
    2016: frozenset({"朱立倫", "宋楚瑜"}),
    2020: frozenset({"韓國瑜", "宋楚瑜"}),
    2024: frozenset({"侯友宜"}),
}


@dataclass(frozen=True)
class VoteRow:
    year: int
    district: str
    village: str
    candidate: str
    votes: int


@dataclass(frozen=True)
class Aggregate:
    year: int
    district: str
    village: str
    valid_votes: int
    blue_votes: int

    @property
    def blue_share(self):
        return round(self.blue_votes / self.valid_votes * 100, 4)


def aggregate_geography(rows):
    grouped = defaultdict(lambda: [0, 0])
    for row in rows:
        if row.votes < 0:
            raise ValueError("votes must be non-negative")
        totals = grouped[(row.year, row.district, row.village)]
        totals[0] += row.votes
        if row.candidate in BLUE_CANDIDATES[row.year]:
            totals[1] += row.votes
    return [Aggregate(*key, *value) for key, value in sorted(grouped.items())]


def election_deltas(rows):
    return [
        (current[0], round(current[1] - previous[1], 2), current[2] - previous[2])
        for previous, current in zip(rows, rows[1:])
    ]


def select_fixed_cohort(village_years, years, threshold, minimum_valid):
    required = set(years)
    return {
        key for key, values in village_years.items()
        if required.issubset(values)
        and values[2000][1] >= minimum_valid
        and values[2000][0] / values[2000][1] * 100 >= threshold
    }


def estimate_young_votes(eligible, turnout, low_share, central_share, high_share):
    ballots = eligible * turnout
    return tuple(round(ballots * share) for share in (low_share, central_share, high_share))
```

- [ ] **Step 4: Run tests and verify GREEN**

Run: `PYTHONPATH=src caffeinate -i -m python3 -m unittest tests.test_analysis -v`

Expected: 4 tests pass.

- [ ] **Step 5: Commit the analysis unit**

```bash
git add src/taipei_blue_vote tests/test_analysis.py
git commit -m "feat: add core election analysis"
```

### Task 2: Source ingestion and reproducible artifacts

**Files:**
- Create: `src/taipei_blue_vote/sources.py`
- Create: `src/taipei_blue_vote/outputs.py`
- Create: `src/taipei_blue_vote/__main__.py`
- Create: `tests/test_sources.py`
- Create: `tests/test_outputs.py`
- Create: `pyproject.toml`

**Interfaces:**
- Consumes: TaiwanVotes index and Taipei presidential CSV bytes.
- Produces: parsed `VoteRow` objects, SHA-256 source records, and deterministic CSV/JSON files.

- [ ] **Step 1: Write failing boundary tests with real in-memory CSV bytes and a temporary output directory**

```python
import tempfile
import unittest
from pathlib import Path

from taipei_blue_vote.outputs import write_csv
from taipei_blue_vote.sources import parse_vote_csv


class SourceTests(unittest.TestCase):
    def test_parse_vote_csv_handles_utf8_bom(self):
        payload = "\ufeff屆期,鄉鎮市區,村里,候選人,得票數\n2024,信義區,景新里,侯友宜,40\n".encode()
        self.assertEqual(parse_vote_csv(payload)[0].votes, 40)


class OutputTests(unittest.TestCase):
    def test_write_csv_is_deterministic(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rows.csv"
            write_csv(path, ["year", "votes"], [[2024, 40]])
            self.assertEqual(path.read_text(), "year,votes\n2024,40\n")
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `PYTHONPATH=src caffeinate -i -m python3 -m unittest tests.test_sources tests.test_outputs -v`

Expected: import failures for the missing boundary modules.

- [ ] **Step 3: Implement parsing, download metadata, deterministic writers, and the CLI**

```python
def parse_vote_csv(payload):
    text = payload.decode("utf-8-sig")
    records = []
    for row in csv.DictReader(io.StringIO(text)):
        records.append(VoteRow(
            year=int(row["屆期"]),
            district=row["鄉鎮市區"].strip(),
            village=row["村里"].strip(),
            candidate=row["候選人"].strip(),
            votes=int(row["得票數"]),
        ))
    return records


def write_csv(path, fieldnames, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(fieldnames)
        writer.writerows(rows)
```

The CLI downloads exactly seven Taipei presidential CSVs, verifies that every configured blue candidate appears, writes their URLs and SHA-256 values to `data/derived/source_manifest.json`, and writes city, cohort, proxy, delta, and youth-estimate CSV files.

- [ ] **Step 4: Run all boundary tests and verify GREEN**

Run: `PYTHONPATH=src caffeinate -i -m python3 -m unittest tests.test_sources tests.test_outputs -v`

Expected: all boundary tests pass.

- [ ] **Step 5: Commit the ingestion and output unit**

```bash
git add pyproject.toml src/taipei_blue_vote tests/test_sources.py tests/test_outputs.py
git commit -m "feat: add reproducible data pipeline"
```

### Task 3: GitHub-previewable chart generation

**Files:**
- Create: `src/taipei_blue_vote/chart.py`
- Create: `tests/test_chart.py`
- Generate: `charts/taipei-blue-election-deltas.svg`
- Generate: `charts/taipei-blue-election-deltas.html`

**Interfaces:**
- Consumes: ordered election-delta rows.
- Produces: accessible SVG and standalone HTML with all 12 signed labels.

- [ ] **Step 1: Write a failing chart-content test**

```python
import unittest

from taipei_blue_vote.chart import render_svg


class ChartTests(unittest.TestCase):
    def test_svg_contains_both_metrics_and_signed_values(self):
        svg = render_svg([(2004, -5.16, -81232), (2008, 6.50, 113676)])
        for text in ("得票率增減", "選票增減", "−5.16 pp", "+6.50 pp", "−81,232", "+113,676"):
            self.assertIn(text, svg)
        self.assertIn("role=\"img\"", svg)
```

- [ ] **Step 2: Run the test and verify RED**

Run: `PYTHONPATH=src caffeinate -i -m python3 -m unittest tests.test_chart -v`

Expected: import failure because the chart module does not exist.

- [ ] **Step 3: Implement an accessible two-panel SVG and standalone HTML wrapper**

```python
def signed(value, digits=0):
    sign = "+" if value > 0 else "−" if value < 0 else ""
    magnitude = abs(value)
    return f"{sign}{magnitude:,.{digits}f}"


def render_svg(rows):
    share_labels = [f"{signed(row[1], 2)} pp" for row in rows]
    vote_labels = [signed(row[2]) for row in rows]
    labels = share_labels + vote_labels
    text_nodes = "".join(f"<text>{escape(label)}</text>" for label in labels)
    return f'<svg xmlns="http://www.w3.org/2000/svg" role="img"><title>台北市泛藍總統票各屆增減</title><text>得票率增減</text><text>選票增減</text>{text_nodes}</svg>'
```

Use `value_x = plot_left + (value - domain_min) / (domain_max - domain_min) * plot_width` for both panels, draw each bar between `value_x` and the zero position, and place the signed label in a fixed right-hand value column. The share domain is `(-13, 7)` and the vote domain is `(-300000, 130000)`, matching the committed chart axes.

- [ ] **Step 4: Run chart tests and verify GREEN**

Run: `PYTHONPATH=src caffeinate -i -m python3 -m unittest tests.test_chart -v`

Expected: chart tests pass.

- [ ] **Step 5: Commit chart code and generated chart files**

```bash
git add src/taipei_blue_vote/chart.py tests/test_chart.py charts
git commit -m "feat: add election delta charts"
```

### Task 4: Report, documentation, continuous integration, and publication

**Files:**
- Create: `README.md`
- Create: `report/findings.md`
- Create: `LICENSE`
- Create: `.github/workflows/test.yml`
- Generate: `data/derived/*.csv`
- Generate: `data/derived/source_manifest.json`

**Interfaces:**
- Consumes: verified program output and source citations.
- Produces: a self-contained repository landing page and a tested GitHub revision.

- [ ] **Step 1: Rebuild committed artifacts from the public source files**

Run: `PYTHONPATH=src caffeinate -i -m python3 -m taipei_blue_vote --refresh`

Expected key city totals: 2000 `979102 / 61.6887%`; 2024 `587258 / 38.0839%`.

- [ ] **Step 2: Write the report and README with chart preview and method caveats**

```markdown
# Taipei Blue Vote Trend

![每屆泛藍得票率與選票增減](charts/taipei-blue-election-deltas.svg)

The main result is a non-linear, stepwise decline: the largest breaks occur in 2016 and 2024. The 2020 vote count rises while share still falls, so turnout and electorate size must be distinguished from relative support.

The analysis never treats military-village location proxies as individual ancestry and never reports the young-vote estimate as official candidate-by-age data.
```

- [ ] **Step 3: Add CI using the exact local verification command**

```yaml
name: test
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: PYTHONPATH=src python -m unittest discover -s tests -v
```

- [ ] **Step 4: Run the complete verification suite**

Run: `PYTHONPATH=src caffeinate -i -m python3 -m unittest discover -s tests -v`

Run: `caffeinate -i -m python3 -m compileall -q src tests`

Run: `git diff --check`

Expected: all tests pass, compilation exits zero, and `git diff --check` has no output.

- [ ] **Step 5: Commit, merge, create the private GitHub repository, and push**

```bash
git add README.md LICENSE report .github data/derived
git commit -m "docs: publish Taipei blue vote trend findings"
git switch main
git merge --ff-only feat/initial-analysis
gh repo create chouchunming/taipei-blue-vote-trend --private --source=. --remote=origin
git push -u origin main
```
