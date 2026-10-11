# Green Base and Swing-Vote Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add reproducible Taipei pan-green base trends, a fixed deep-green village cohort, observable third-candidate votes, and three-bloc electoral volatility for 2000–2024.

**Architecture:** Extend the existing election aggregate types without changing the established pan-blue definition, then compose green cohort and volatility results in `AnalysisBundle`. Generate deterministic CSVs and a dependency-free SVG/HTML chart from those tested primitives, followed by an official-source rebuild and documented interpretation limits.

**Tech Stack:** Python 3.11+ standard library, frozen dataclasses, CSV/JSON, hand-authored SVG, `unittest`.

## Global Constraints

- Keep runtime dependencies at zero.
- Keep the existing blue candidate classification unchanged and retain `ko_votes` for compatibility.
- Classify green candidates exactly as specified in the approved design.
- Define the fixed deep-green cohort from 2000 green share `>= 45.0`, 2000 valid votes `>= 100`, and exact presence in all seven elections.
- Describe `other_votes` as an observed non-blue/non-green candidate category, never as all centrist voters.
- Describe volatility as aggregate minimum net share change and its current-election vote equivalent, never as identified individual switchers.
- Run every test, rebuild, compile, or evaluation command as a direct child of `caffeinate -i -m`.

---

### Task 1: Add green and other bloc aggregation

**Files:**
- Modify: `src/taipei_blue_vote/analysis.py`
- Modify: `tests/test_analysis.py`

**Interfaces:**
- Consumes: normalized `VoteRow` candidate rows and the existing `BLUE_CANDIDATES` mapping.
- Produces: `GREEN_CANDIDATES`, extended `VillageResult`/`ElectionResult`, `select_fixed_cohort(..., bloc=...)`, `BlocDelta`, `VolatilityResult`, `bloc_deltas()`, and `electoral_volatility()`.

- [ ] **Step 1: Write failing classification and share tests**

Add a 2024 fixture containing 侯友宜 40, 賴清德 30, and 柯文哲 30 votes and assert:

```python
result = aggregate_villages(rows)[0]
self.assertEqual(result.blue_votes, 40)
self.assertEqual(result.green_votes, 30)
self.assertEqual(result.other_votes, 30)
self.assertEqual(result.ko_votes, 30)
self.assertEqual(result.green_share, 30.0)
self.assertEqual(result.other_share, 30.0)
```

Add `validate_bloc_configuration()` coverage with an overlapping custom map and assert a `ValueError` containing `overlap`.

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```bash
caffeinate -i -m env PYTHONPATH=src python3 -m unittest tests.test_analysis.AnalysisTests.test_aggregate_villages_counts_blue_green_and_other tests.test_analysis.AnalysisTests.test_bloc_configuration_rejects_overlap -v
```

Expected: FAIL because green/other fields and configuration validation do not exist.

- [ ] **Step 3: Implement the candidate maps and extended aggregate types**

Add:

```python
GREEN_CANDIDATES = {
    2000: frozenset({"陳水扁"}),
    2004: frozenset({"陳水扁"}),
    2008: frozenset({"謝長廷"}),
    2012: frozenset({"蔡英文"}),
    2016: frozenset({"蔡英文"}),
    2020: frozenset({"蔡英文"}),
    2024: frozenset({"賴清德"}),
}


def validate_bloc_configuration(blue=BLUE_CANDIDATES, green=GREEN_CANDIDATES):
    overlaps = {
        year: sorted(blue[year] & green[year])
        for year in ELECTION_YEARS
        if blue[year] & green[year]
    }
    if overlaps:
        raise ValueError(f"blue/green candidate overlap: {overlaps}")
```

Append `green_votes: int = 0` and `other_votes: int = 0` after `ko_votes` in both result dataclasses to preserve existing positional construction. Add `green_share` and `other_share` properties using the same positive-valid-vote guard as `blue_share`. Aggregate valid, blue, Ko, and green votes, then compute `other = valid - blue - green`; reject negative values.

- [ ] **Step 4: Run classification tests and verify GREEN**

Run:

```bash
caffeinate -i -m env PYTHONPATH=src python3 -m unittest tests.test_analysis -v
```

Expected: all analysis tests pass.

- [ ] **Step 5: Write failing deep-green cohort and volatility tests**

Build two villages present in all seven years, one with 2000 green share 45% and one with 44%, and assert only the first is selected by:

```python
select_fixed_cohort(results, threshold=45.0, bloc="green")
```

For city rows with shares `(60, 35, 5)` then `(50, 40, 10)` and 1,000 current valid votes, assert:

```python
delta = bloc_deltas(city)[0]
self.assertEqual((delta.blue_share_delta, delta.green_share_delta, delta.other_share_delta), (-10.0, 5.0, 5.0))
volatility = electoral_volatility(city)[0]
self.assertEqual(volatility.volatility_pp, 10.0)
self.assertEqual(volatility.vote_equivalent, 100)
```

- [ ] **Step 6: Run the new tests and verify RED**

Run:

```bash
caffeinate -i -m env PYTHONPATH=src python3 -m unittest tests.test_analysis -v
```

Expected: FAIL because generalized cohort selection and volatility functions do not exist.

- [ ] **Step 7: Implement generalized cohort and three-bloc change types**

Define:

```python
@dataclass(frozen=True, slots=True)
class BlocDelta:
    year: int
    blue_share_delta: float
    blue_vote_delta: int
    green_share_delta: float
    green_vote_delta: int
    other_share_delta: float
    other_vote_delta: int


@dataclass(frozen=True, slots=True)
class VolatilityResult:
    year: int
    volatility_pp: float
    vote_equivalent: int
```

Accept `bloc: str = "blue"` in `select_fixed_cohort`, map it to `blue_share` or `green_share`, and reject other values. Implement `bloc_deltas()` with signed current-minus-previous values. Implement `electoral_volatility()` as half the sum of absolute three-bloc share deltas and multiply the resulting fraction by current valid votes.

- [ ] **Step 8: Run all analysis tests and commit**

Run:

```bash
caffeinate -i -m env PYTHONPATH=src python3 -m unittest tests.test_analysis -v
```

Expected: PASS.

Commit:

```bash
git add src/taipei_blue_vote/analysis.py tests/test_analysis.py
git commit -m "feat: aggregate green and swing vote measures"
```

---

### Task 2: Compose and validate the extended analysis

**Files:**
- Modify: `src/taipei_blue_vote/pipeline.py`
- Modify: `src/taipei_blue_vote/validation.py`
- Modify: `src/taipei_blue_vote/rebuild.py`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_validation.py`
- Modify: `tests/test_rebuild.py`

**Interfaces:**
- Consumes: extended result types and Task 1 functions.
- Produces: `AnalysisBundle.green_cohort_keys`, `.green_cohort`, `.green_deltas`, `.bloc_deltas`, and `.volatility`; official four-value city-total validation.

- [ ] **Step 1: Write failing pipeline tests**

Update the seven-year fixture to include the configured green candidate and assert:

```python
self.assertEqual(analysis.green_cohort_keys, frozenset({("甲區", "綠里")}))
self.assertEqual(analysis.city[0].green_votes, expected_green)
self.assertEqual(analysis.green_cohort[0].green_share, 45.0)
self.assertEqual(len(analysis.bloc_deltas), 6)
self.assertEqual(len(analysis.volatility), 6)
```

- [ ] **Step 2: Run pipeline tests and verify RED**

Run:

```bash
caffeinate -i -m env PYTHONPATH=src python3 -m unittest tests.test_pipeline -v
```

Expected: FAIL because the extended bundle fields do not exist.

- [ ] **Step 3: Extend `AnalysisBundle` and `analyze_rows()`**

Calculate:

```python
green_cohort_keys = select_fixed_cohort(villages, threshold=45.0, bloc="green")
green_cohort = summarize(villages, green_cohort_keys)
green_deltas = tuple(
    election_deltas([(row.year, row.green_share, row.green_votes) for row in city])
)
all_bloc_deltas = tuple(bloc_deltas(city))
volatility = tuple(electoral_volatility(city))
```

Append these fields to `AnalysisBundle` and return them from `analyze_rows()`.

- [ ] **Step 4: Run pipeline tests and verify GREEN**

Run:

```bash
caffeinate -i -m env PYTHONPATH=src python3 -m unittest tests.test_pipeline -v
```

Expected: PASS.

- [ ] **Step 5: Write failing validation tests**

Build candidate coverage with both configured maps. Assert a 2024 source containing only 侯友宜 raises an error naming missing green candidates. Change the city-total fixture to:

```python
ElectionResult(2024, 100, 40, 30, 30, 30)
```

and validate against `{2024: (100, 40, 30, 30)}`.

- [ ] **Step 6: Run validation tests and verify RED**

Run:

```bash
caffeinate -i -m env PYTHONPATH=src python3 -m unittest tests.test_validation -v
```

Expected: FAIL until green coverage and four-value totals are checked.

- [ ] **Step 7: Implement official bloc validation**

Set `EXPECTED_CITY_TOTALS` to `(valid, blue, green, other)` tuples:

```python
2000: (1_587_166, 979_102, 597_465, 10_599),
2004: (1_588_249, 897_870, 690_379, 0),
2008: (1_604_802, 1_011_546, 593_256, 0),
2012: (1_604_730, 970_165, 634_565, 0),
2016: (1_457_678, 700_295, 757_383, 0),
2020: (1_632_453, 756_599, 875_854, 0),
2024: (1_542_011, 587_258, 587_899, 366_854),
```

Update `verify_candidate_coverage()` to report missing configured blue and green candidates and update `verify_city_totals()` to compare all four values.

- [ ] **Step 8: Update rebuild fixtures, run focused tests, and commit**

Use the configured green candidate instead of a generic `其他` row in `_csv_payload()`, and change fixture expected totals to `(100, 70, 30, 0)`. Run:

```bash
caffeinate -i -m env PYTHONPATH=src python3 -m unittest tests.test_pipeline tests.test_validation tests.test_rebuild -v
```

Expected: PASS.

Commit:

```bash
git add src/taipei_blue_vote/pipeline.py src/taipei_blue_vote/validation.py src/taipei_blue_vote/rebuild.py tests/test_pipeline.py tests/test_validation.py tests/test_rebuild.py
git commit -m "feat: compose and validate green vote analysis"
```

---

### Task 3: Export green cohort, bloc deltas, and volatility

**Files:**
- Modify: `src/taipei_blue_vote/artifacts.py`
- Modify: `tests/test_artifacts.py`

**Interfaces:**
- Consumes: the extended `AnalysisBundle` from Task 2.
- Produces: expanded `city_trend.csv`, `deep_green_cohort.csv`, `bloc_deltas.csv`, and `electoral_volatility.csv`.

- [ ] **Step 1: Write failing artifact schema tests**

Assert the city header contains `green_votes,green_share,other_votes,other_share`; assert the three new files exist; and assert the fixture rows contain the expected green cohort count, signed bloc deltas, and volatility vote equivalent.

- [ ] **Step 2: Run artifact tests and verify RED**

Run:

```bash
caffeinate -i -m env PYTHONPATH=src python3 -m unittest tests.test_artifacts -v
```

Expected: FAIL because the new columns and files are missing.

- [ ] **Step 3: Extend deterministic CSV writing**

Write city columns in this order:

```text
year,valid_votes,blue_votes,blue_share,green_votes,green_share,
other_votes,other_share,ko_votes,ko_share,
blue_vote_change_from_2000,blue_share_point_change_from_2000,
green_vote_change_from_2000,green_share_point_change_from_2000,
other_vote_change_from_2000,other_share_point_change_from_2000
```

Write `deep_green_cohort.csv` with year, fixed village count, valid votes, green votes/share, and changes from 2000. Write `bloc_deltas.csv` with all three signed share and vote deltas. Write `electoral_volatility.csv` with year, `volatility_pp`, `vote_equivalent`, and current valid votes.

- [ ] **Step 4: Run artifact tests and commit**

Run:

```bash
caffeinate -i -m env PYTHONPATH=src python3 -m unittest tests.test_artifacts -v
```

Expected: PASS.

Commit:

```bash
git add src/taipei_blue_vote/artifacts.py tests/test_artifacts.py
git commit -m "feat: export green and volatility tables"
```

---

### Task 4: Add the bloc and volatility chart

**Files:**
- Modify: `src/taipei_blue_vote/chart.py`
- Modify: `src/taipei_blue_vote/artifacts.py`
- Modify: `tests/test_chart.py`
- Modify: `tests/test_artifacts.py`
- Create: `charts/taipei-bloc-and-volatility.svg` (generated)
- Create: `charts/taipei-bloc-and-volatility.html` (generated)

**Interfaces:**
- Consumes: `BlocShareRow = tuple[int, float, float, float]` and `VolatilityRow = tuple[int, float, int]`.
- Produces: `render_bloc_svg(bloc_rows, volatility_rows) -> str` and the two committed chart files.

- [ ] **Step 1: Write failing chart tests**

Use compact fixture rows and assert the SVG contains:

```python
for label in ("泛藍", "泛綠", "其他候選人", "最低淨移動規模", "23.79%", "23.79 pp"):
    self.assertIn(label, svg)
self.assertEqual(svg.count('class="volatility-bar"'), 6)
self.assertIn('role="img"', svg)
```

Add artifact assertions for both generated files.

- [ ] **Step 2: Run chart tests and verify RED**

Run:

```bash
caffeinate -i -m env PYTHONPATH=src python3 -m unittest tests.test_chart tests.test_artifacts -v
```

Expected: FAIL because `render_bloc_svg()` and the chart files do not exist.

- [ ] **Step 3: Implement a two-panel SVG**

Create a 1200×650 light-background SVG. The upper panel plots blue, green, and other shares for all seven elections with distinct colors and direct labels. The lower panel plots six volatility bars labelled with signed-free percentage-point values and vote equivalents. Include a description stating that `other` is a candidate category and volatility is aggregate net change, not identified voters.

In `write_artifacts()`, pass:

```python
bloc_rows = [
    (row.year, row.blue_share, row.green_share, row.other_share)
    for row in analysis.city
]
volatility_rows = [
    (row.year, row.volatility_pp, row.vote_equivalent)
    for row in analysis.volatility
]
```

Write the SVG and wrap it with `render_html(..., title="臺北市藍綠與選票波動")`.

- [ ] **Step 4: Run chart tests, render the real chart, inspect it, and commit**

Run:

```bash
caffeinate -i -m env PYTHONPATH=src python3 -m unittest tests.test_chart tests.test_artifacts -v
caffeinate -i -m env PYTHONPATH=src python3 -m taipei_blue_vote --refresh
```

Render the SVG to PNG with Quick Look and visually inspect text, axes, point/line placement, bar labels, clipping, and contrast.

Expected: tests pass, rebuild exits zero, and the chart has no overlap or clipping.

Commit:

```bash
git add src/taipei_blue_vote/chart.py src/taipei_blue_vote/artifacts.py tests/test_chart.py tests/test_artifacts.py charts/taipei-bloc-and-volatility.svg charts/taipei-bloc-and-volatility.html data/derived
git commit -m "feat: chart bloc trends and electoral volatility"
```

---

### Task 5: Document findings and perform release verification

**Files:**
- Modify: `README.md`
- Modify: `report/findings.md`
- Modify: `docs/superpowers/plans/2026-10-11-green-swing-vote.md`

**Interfaces:**
- Consumes: verified official derived CSV values.
- Produces: final user-facing definitions, findings, limitations, and completed checklist.

- [ ] **Step 1: Extract official findings from generated artifacts**

Read the city trend, deep-green cohort, bloc deltas, and volatility CSVs. Record exact 2000/2024 totals, percentage-point changes, the largest green increase/decrease, observed third-candidate votes, and all volatility vote equivalents.

- [ ] **Step 2: Update README and report**

Document:

- the seven green candidates and unchanged blue classification;
- the 45% fixed deep-green cohort definition and actual village count;
- citywide green votes/share by election and 2000–2024 change;
- `other_votes` by election, explicitly noting structural zeros;
- volatility by election with the largest movement highlighted;
- why neither measure is an exact count of ideological centrists;
- paths to all new CSV and chart outputs.

- [ ] **Step 3: Run fresh full verification**

Run:

```bash
caffeinate -i -m env PYTHONPATH=src python3 -m taipei_blue_vote --refresh
caffeinate -i -m env PYTHONPATH=src python3 -m unittest discover -s tests -v
caffeinate -i -m python3 -m compileall -q src tests
caffeinate -i -m git diff --check
```

Expected: official rebuild exits zero, every test passes with zero failures, compileall exits zero, and diff check prints nothing.

- [ ] **Step 4: Review requirements and commit documentation**

Compare every approved design requirement with the code, artifacts, chart, and report. Fix only in-scope gaps and rerun the relevant verification before committing.

Commit:

```bash
git add README.md report/findings.md docs/superpowers/plans/2026-10-11-green-swing-vote.md
git commit -m "docs: report green base and swing vote findings"
```

- [ ] **Step 5: Push, verify GitHub, and integrate**

Push the feature branch, verify its commit with `git ls-remote`, fast-forward `main`, rerun the full test suite on `main`, push `main`, verify the remote SHA and chart file through the GitHub API, and wait for the GitHub Actions `test` workflow to conclude successfully.
