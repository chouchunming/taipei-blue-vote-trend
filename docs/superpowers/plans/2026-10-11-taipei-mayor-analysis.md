# Taipei Mayor Vote Trend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a reproducible 2002–2022 Taipei mayor election analysis with coalition and official-nomination classifications, fixed village cohorts, electoral volatility, CSVs, charts, and a presidential comparison.

**Architecture:** Keep the established presidential pipeline unchanged and add a mayor-specific domain module whose inputs are normalized mayor vote rows. Extend source discovery and rebuild orchestration around that module, emit mayor artifacts through a focused writer, and render dependency-free SVG/HTML charts from tested result types.

**Tech Stack:** Python 3.11+ standard library, frozen dataclasses, CSV/JSON, hand-authored SVG, `unittest`.

## Global Constraints

- Cover exactly the 2002, 2006, 2010, 2014, 2018, and 2022 Taipei mayor elections.
- Keep all existing presidential candidate definitions, outputs, and schemas unchanged.
- Use `coalition` as the primary classification and `official_nomination` as a sensitivity analysis.
- Under `coalition`, classify Ko Wen-je as green in 2014 and other in 2018; classify James Soong as blue and 周玉蔻 as green in 2006.
- Under `official_nomination`, only KMT nominees are blue and DPP nominees are green; the 2014 green category is zero.
- Build fixed coalition cohorts from 2002: blue share `>= 65.0`, green share `>= 45.0`, valid votes `>= 100`, and exact presence in all six elections.
- Never describe other-candidate votes as all ideological centrists or volatility as identified individual switchers.
- Keep runtime dependencies at zero and raw downloads gitignored.
- Run every test, rebuild, compile, evaluation, or lint command as a direct child of `caffeinate -i -m`.

---

### Task 1: Discover and parse Taipei mayor sources

**Files:**
- Modify: `src/taipei_blue_vote/sources.py`
- Create: `tests/test_mayor_sources.py`

**Interfaces:**
- Consumes: TaiwanVotes index JSON and normalized `縣市長` CSV bytes.
- Produces: `MAYOR_YEARS`, `MayorVoteRow`, `select_taipei_mayor_files(index_payload) -> dict[int, str]`, and `parse_mayor_vote_csv(payload) -> tuple[MayorVoteRow, ...]`.

- [ ] **Step 1: Write failing source-selection tests**

Create a minimal index containing the six exact mayor entries plus irrelevant president and council entries. Assert:

```python
self.assertEqual(
    select_taipei_mayor_files(payload),
    {
        2002: "縣市長_2001-02_臺北市.csv",
        2006: "縣市長_2005-06_臺北市.csv",
        2010: "縣市長_2009-10_臺北市.csv",
        2014: "縣市長_2014_臺北市.csv",
        2018: "縣市長_2018_臺北市.csv",
        2022: "縣市長_2022_臺北市.csv",
    },
)
```

Add one test for a missing 2014 file and one for duplicate 2018 files; both must raise a `ValueError` naming the affected year.

- [ ] **Step 2: Run source-selection tests and verify RED**

Run:

```bash
caffeinate -i -m env PYTHONPATH=src python3 -m unittest tests.test_mayor_sources -v
```

Expected: FAIL because mayor constants and selectors do not exist.

- [ ] **Step 3: Implement mayor row parsing and file selection**

Define the normalized input type in `sources.py`:

```python
MAYOR_YEARS = (2002, 2006, 2010, 2014, 2018, 2022)


@dataclass(frozen=True, slots=True)
class MayorVoteRow:
    year: int
    district: str
    village: str
    candidate: str
    party: str
    votes: int
```

Add `政黨` to the mayor-only required columns, strip all text fields, parse votes as integers, and reject malformed rows with `ValueError("invalid mayor vote row: ...")`. Select only index entries where `kind == "votes"`, `type == "縣市長"`, `county == "臺北市"`, and year is in `MAYOR_YEARS`.

- [ ] **Step 4: Add parser tests and verify GREEN**

Parse a BOM-prefixed fixture containing Ko Wen-je and assert the party and village fields. Add a missing-party-column failure. Run:

```bash
caffeinate -i -m env PYTHONPATH=src python3 -m unittest tests.test_mayor_sources tests.test_sources -v
```

Expected: all source tests pass.

- [ ] **Step 5: Commit source ingestion**

```bash
git add src/taipei_blue_vote/sources.py tests/test_mayor_sources.py
git commit -m "feat: ingest Taipei mayor election sources"
```

---

### Task 2: Implement mayor classification and trend analysis

**Files:**
- Create: `src/taipei_blue_vote/mayor.py`
- Create: `tests/test_mayor.py`

**Interfaces:**
- Consumes: `MayorVoteRow` values for all six elections.
- Produces: candidate maps, `MayorVillageResult`, `MayorElectionResult`, `MayorCandidateTotal`, `MayorBlocDelta`, `MayorVolatility`, `MayorScenarioAnalysis`, `MayorAnalysisBundle`, `validate_mayor_bloc_configuration()`, `aggregate_mayor_villages()`, `summarize_mayor()`, `select_mayor_cohort()`, and `analyze_mayor_rows()`.

- [ ] **Step 1: Write failing classification tests**

Use compact candidate fixtures and assert the approved differences:

```python
self.assertEqual(bloc_for_candidate(2006, "宋楚瑜", "coalition"), "blue")
self.assertEqual(bloc_for_candidate(2006, "周玉蔻", "coalition"), "green")
self.assertEqual(bloc_for_candidate(2006, "宋楚瑜", "official_nomination"), "other")
self.assertEqual(bloc_for_candidate(2014, "柯文哲", "coalition"), "green")
self.assertEqual(bloc_for_candidate(2014, "柯文哲", "official_nomination"), "other")
self.assertEqual(bloc_for_candidate(2018, "柯文哲", "coalition"), "other")
self.assertEqual(bloc_for_candidate(2022, "黃珊珊", "coalition"), "other")
```

Pass overlapping custom maps to `validate_mayor_bloc_configuration()` and assert a `ValueError` containing `overlap`. Assert an unknown scenario raises `ValueError` containing `classification`.

- [ ] **Step 2: Run classification tests and verify RED**

```bash
caffeinate -i -m env PYTHONPATH=src python3 -m unittest tests.test_mayor.MayorAnalysisTests.test_candidate_classification tests.test_mayor.MayorAnalysisTests.test_configuration_rejects_overlap -v
```

Expected: FAIL because `mayor.py` does not exist.

- [ ] **Step 3: Define exact candidate maps and result types**

Implement these maps:

```python
COALITION_BLUE = {
    2002: frozenset({"馬英九"}),
    2006: frozenset({"郝龍斌", "宋楚瑜"}),
    2010: frozenset({"郝龍斌"}),
    2014: frozenset({"連勝文"}),
    2018: frozenset({"丁守中"}),
    2022: frozenset({"蔣萬安"}),
}
COALITION_GREEN = {
    2002: frozenset({"李應元"}),
    2006: frozenset({"謝長廷", "周玉蔻"}),
    2010: frozenset({"蘇貞昌"}),
    2014: frozenset({"柯文哲"}),
    2018: frozenset({"姚文智"}),
    2022: frozenset({"陳時中"}),
}
OFFICIAL_BLUE = {
    2002: frozenset({"馬英九"}), 2006: frozenset({"郝龍斌"}),
    2010: frozenset({"郝龍斌"}), 2014: frozenset({"連勝文"}),
    2018: frozenset({"丁守中"}), 2022: frozenset({"蔣萬安"}),
}
OFFICIAL_GREEN = {
    2002: frozenset({"李應元"}), 2006: frozenset({"謝長廷"}),
    2010: frozenset({"蘇貞昌"}), 2014: frozenset(),
    2018: frozenset({"姚文智"}), 2022: frozenset({"陳時中"}),
}
```

Each village and election result contains `classification`, `year`, valid votes, and blue/green/other votes with guarded share properties. Candidate totals contain year, candidate, party, assigned bloc, votes, and share. Delta and volatility types contain the same three-bloc fields used by the presidential analysis.

- [ ] **Step 4: Implement and verify aggregation**

`aggregate_mayor_villages(rows, classification)` groups by year/district/village, assigns each candidate exactly once, and calculates `other = valid - blue - green`. Reject negative votes, unsupported years, non-positive village totals, and negative other totals.

Add a 2014 fixture with 40 Lien, 55 Ko, and 5 minor-candidate votes. Assert coalition results `(blue, green, other) == (40, 55, 5)` and official-nomination results `(40, 0, 60)`. Run:

```bash
caffeinate -i -m env PYTHONPATH=src python3 -m unittest tests.test_mayor -v
```

Expected: aggregation and classification tests pass; later cohort tests still fail until implemented.

- [ ] **Step 5: Write failing cohort, delta, and volatility tests**

Create two villages across all six years: one exactly 65% blue and one exactly 45% green in 2002. Assert both boundary villages are included in their respective fixed cohorts. Add scenario results changing from `(60, 35, 5)` to `(50, 40, 10)` with 1,000 current valid votes and assert:

```python
self.assertEqual(delta.blue_share_delta, -10.0)
self.assertEqual(delta.green_share_delta, 5.0)
self.assertEqual(delta.other_share_delta, 5.0)
self.assertEqual(volatility.volatility_pp, 10.0)
self.assertEqual(volatility.vote_equivalent, 100)
```

- [ ] **Step 6: Implement cohort, delta, volatility, and bundle composition**

`select_mayor_cohort(results, bloc, threshold, minimum_valid=100)` requires the exact village key in `MAYOR_YEARS` and uses the 2002 share. `analyze_mayor_rows(rows)` returns both scenario analyses, coalition deep-blue/deep-green keys and summaries, and scenario-specific candidate totals, deltas, and volatility.

- [ ] **Step 7: Run all mayor analysis tests and commit**

```bash
caffeinate -i -m env PYTHONPATH=src python3 -m unittest tests.test_mayor -v
git add src/taipei_blue_vote/mayor.py tests/test_mayor.py
git commit -m "feat: analyze Taipei mayor vote blocs"
```

Expected: all mayor analysis tests pass.

---

### Task 3: Validate official totals and compose rebuild inputs

**Files:**
- Modify: `src/taipei_blue_vote/validation.py`
- Modify: `src/taipei_blue_vote/rebuild.py`
- Create: `tests/test_mayor_validation.py`
- Modify: `tests/test_rebuild.py`

**Interfaces:**
- Consumes: parsed mayor rows, `MayorAnalysisBundle`, index metadata, filenames, and payload bytes.
- Produces: `EXPECTED_MAYOR_CITY_TOTALS`, `verify_mayor_candidate_coverage()`, `verify_mayor_city_totals()`, and `prepare_mayor_from_payloads() -> tuple[MayorAnalysisBundle, dict[str, object]]`.

- [ ] **Step 1: Write failing official-total validation tests**

Define the exact expected totals as `(valid, blue, green, other)`:

```python
EXPECTED_MAYOR_CITY_TOTALS = {
    "coalition": {
        2002: (1_361_913, 873_102, 488_811, 0),
        2006: (1_286_089, 745_366, 529_241, 11_482),
        2010: (1_433_736, 797_865, 628_129, 7_742),
        2014: (1_494_046, 609_932, 853_983, 30_131),
        2018: (1_413_870, 577_096, 244_342, 592_432),
        2022: (1_360_951, 575_590, 434_558, 350_803),
    },
    "official_nomination": {
        2002: (1_361_913, 873_102, 488_811, 0),
        2006: (1_286_089, 692_085, 525_869, 68_135),
        2010: (1_433_736, 797_865, 628_129, 7_742),
        2014: (1_494_046, 609_932, 0, 884_114),
        2018: (1_413_870, 577_096, 244_342, 592_432),
        2022: (1_360_951, 575_590, 434_558, 350_803),
    },
}
```

Assert one altered green total raises `ValueError` containing the scenario and year. Assert a missing configured candidate raises an error naming that candidate.

- [ ] **Step 2: Run validation tests and verify RED**

```bash
caffeinate -i -m env PYTHONPATH=src python3 -m unittest tests.test_mayor_validation -v
```

Expected: FAIL because mayor validation functions do not exist.

- [ ] **Step 3: Implement mayor validation**

`verify_mayor_candidate_coverage()` checks the union of configured blue and green candidates for each scenario and year. `verify_mayor_city_totals()` compares every scenario/year tuple and reports expected and observed values. Keep existing presidential validation signatures unchanged.

- [ ] **Step 4: Write failing payload-composition test**

Build six in-memory CSV payloads with the same headers as the official source and minimal configured candidates. Pass fixture expected totals explicitly. Assert that `prepare_mayor_from_payloads()` returns two scenario analyses and a manifest with six file records, dataset `TaiwanVotes normalized CEC Taipei mayor CSV`, and SHA-256 values.

- [ ] **Step 5: Implement `prepare_mayor_from_payloads()`**

The function must:

```python
def prepare_mayor_from_payloads(
    index_payload: bytes,
    filenames: Mapping[int, str],
    payloads: Mapping[int, bytes],
    *,
    expected_city_totals=EXPECTED_MAYOR_CITY_TOTALS,
) -> tuple[MayorAnalysisBundle, dict[str, object]]:
```

Parse each payload, reject a row whose internal year differs from its filename mapping, verify candidate coverage, analyze both scenarios, validate totals, and build a deterministic manifest without writing files.

- [ ] **Step 6: Run validation and rebuild tests, then commit**

```bash
caffeinate -i -m env PYTHONPATH=src python3 -m unittest tests.test_mayor_validation tests.test_rebuild -v
git add src/taipei_blue_vote/validation.py src/taipei_blue_vote/rebuild.py tests/test_mayor_validation.py tests/test_rebuild.py
git commit -m "feat: validate Taipei mayor vote totals"
```

Expected: all focused tests pass.

---

### Task 4: Export deterministic mayor tables and integrate rebuild

**Files:**
- Create: `src/taipei_blue_vote/mayor_artifacts.py`
- Create: `tests/test_mayor_artifacts.py`
- Modify: `src/taipei_blue_vote/rebuild.py`
- Modify: `tests/test_rebuild.py`

**Interfaces:**
- Consumes: `MayorAnalysisBundle` and mayor source manifest.
- Produces: `write_mayor_artifacts(root, analysis, source_manifest)`, seven committed mayor data artifacts, and full-rebuild mayor downloads.

- [ ] **Step 1: Write failing artifact-schema tests**

Build a six-year fixture bundle and call `write_mayor_artifacts()`. Assert these files exist:

```text
mayor_candidate_totals.csv
mayor_city_trend.csv
mayor_bloc_deltas.csv
mayor_electoral_volatility.csv
mayor_deep_blue_cohort.csv
mayor_deep_green_cohort.csv
mayor_source_manifest.json
```

Assert `mayor_city_trend.csv` begins with:

```text
classification,year,valid_votes,blue_votes,blue_share,green_votes,green_share,other_votes,other_share
```

Assert the fixture includes both classification labels and that cohort rows are labelled `coalition`.

- [ ] **Step 2: Run artifact tests and verify RED**

```bash
caffeinate -i -m env PYTHONPATH=src python3 -m unittest tests.test_mayor_artifacts -v
```

Expected: FAIL because the writer does not exist.

- [ ] **Step 3: Implement deterministic mayor CSV/JSON output**

Write rows sorted by classification, year, candidate, district, and village as applicable. Use four decimal places for levels and volatility, two decimal places for adjacent-election deltas, and integers for vote counts. Candidate totals include `classification,year,candidate,party,bloc,votes,vote_share`. Empty cohort fixtures must produce a header-only valid CSV.

- [ ] **Step 4: Integrate mayor downloads into `rebuild()`**

After presidential payload preparation, select the six mayor files from the same cached index, download them through `cached_payload()`, call `prepare_mayor_from_payloads()`, and write mayor artifacts. Add:

```python
def rebuild_mayor_from_payloads(
    root,
    index_payload,
    filenames,
    payloads,
    *,
    expected_city_totals=EXPECTED_MAYOR_CITY_TOTALS,
):
    analysis, manifest = prepare_mayor_from_payloads(
        index_payload, filenames, payloads, expected_city_totals=expected_city_totals
    )
    write_mayor_artifacts(root, analysis, manifest)
    return analysis
```

- [ ] **Step 5: Run artifact and offline rebuild tests, then commit**

```bash
caffeinate -i -m env PYTHONPATH=src python3 -m unittest tests.test_mayor_artifacts tests.test_rebuild -v
git add src/taipei_blue_vote/mayor_artifacts.py src/taipei_blue_vote/rebuild.py tests/test_mayor_artifacts.py tests/test_rebuild.py
git commit -m "feat: export Taipei mayor vote tables"
```

Expected: both focused suites pass without network access.

---

### Task 5: Render mayor and presidential-comparison charts

**Files:**
- Modify: `src/taipei_blue_vote/chart.py`
- Modify: `src/taipei_blue_vote/mayor_artifacts.py`
- Modify: `src/taipei_blue_vote/rebuild.py`
- Modify: `tests/test_chart.py`
- Modify: `tests/test_mayor_artifacts.py`
- Modify: `tests/test_rebuild.py`
- Create: `charts/taipei-mayor-bloc-and-volatility.svg` (generated)
- Create: `charts/taipei-mayor-bloc-and-volatility.html` (generated)
- Create: `charts/taipei-presidential-mayor-comparison.svg` (generated)
- Create: `charts/taipei-presidential-mayor-comparison.html` (generated)

**Interfaces:**
- Consumes: coalition and official mayor share rows, mayor volatility rows, and existing presidential city share rows.
- Produces: `render_mayor_bloc_svg()`, `render_presidential_mayor_comparison_svg()`, `write_mayor_charts(root, mayor_analysis, presidential_city)`, and four committed chart files.

- [ ] **Step 1: Write failing mayor-chart tests**

Call `render_mayor_bloc_svg(coalition_rows, official_rows, volatility_rows)` and assert the SVG contains:

```python
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
```

Add an all-zero volatility fixture and assert rendering succeeds.

- [ ] **Step 2: Write failing comparison-chart tests**

Call `render_presidential_mayor_comparison_svg(presidential_rows, mayor_rows)` and assert separate labels for `總統選舉 2000–2024` and `市長選舉 2002–2022`, shared blue/green/other colors, both year sequences, an accessibility description, and no browser-only system colors.

- [ ] **Step 3: Run chart tests and verify RED**

```bash
caffeinate -i -m env PYTHONPATH=src python3 -m unittest tests.test_chart -v
```

Expected: FAIL because the two renderers do not exist.

- [ ] **Step 4: Implement the SVG renderers**

The mayor SVG uses solid coalition lines and thinner dashed official-nomination lines on the same 0–70% scale, with a separate five-bar coalition volatility panel and a note that classification changes explain the 2014 divergence. The comparison SVG uses two aligned panels with the same vertical scale; it never connects presidential points to mayoral points.

Both SVGs use a white background, fixed literal colors, `role="img"`, `<title>`, `<desc>`, readable direct labels, and no JavaScript. Wrap each with `render_html()`.

Add `write_mayor_charts()` to `mayor_artifacts.py`. In the top-level `rebuild()`, retain the returned presidential and mayor bundles and call:

```python
write_mayor_charts(root, mayor_analysis, presidential_analysis.city)
```

Keep `rebuild_mayor_from_payloads()` responsible for mayor data artifacts only so its offline fixtures do not need presidential inputs.

- [ ] **Step 5: Generate and visually inspect official charts**

```bash
caffeinate -i -m env PYTHONPATH=src python3 -m unittest tests.test_chart tests.test_mayor_artifacts -v
caffeinate -i -m env PYTHONPATH=src python3 -m taipei_blue_vote --refresh
```

Render both SVGs to PNG with Quick Look and inspect line placement, dashed sensitivity lines, legends, axes, year labels, volatility labels, clipping, and contrast. Fix any visible defect and rerun the focused tests plus rebuild.

- [ ] **Step 6: Commit charts and generated data**

```bash
git add src/taipei_blue_vote/chart.py src/taipei_blue_vote/mayor_artifacts.py src/taipei_blue_vote/rebuild.py tests/test_chart.py tests/test_mayor_artifacts.py tests/test_rebuild.py charts data/derived
git commit -m "feat: chart Taipei mayor vote trends"
```

---

### Task 6: Report findings and release to GitHub

**Files:**
- Modify: `README.md`
- Modify: `report/findings.md`
- Modify: `docs/superpowers/plans/2026-10-11-taipei-mayor-analysis.md`

**Interfaces:**
- Consumes: verified mayor CSV values and inspected charts.
- Produces: user-facing interpretation, completed checklist, merged `main`, and verified GitHub artifacts.

- [x] **Step 1: Extract official findings**

Read all mayor derived tables and record:

- coalition and official-nomination city totals and shares for every election;
- each adjacent-election vote and percentage-point change;
- largest blue and green rises and falls;
- all five volatility percentages and vote equivalents;
- fixed deep-blue and deep-green cohort counts and 2002–2022 endpoint changes;
- the exact 2006 and 2014 classification sensitivity differences;
- similarities and differences between presidential and mayoral trends.

- [x] **Step 2: Update README and report**

Document the six elections, both candidate-classification tables, why coalition is primary, why 2014 official green is zero, cohort definitions and counts, citywide findings, volatility, chart paths, CSV paths, source manifest, and interpretation limits. State explicitly that local candidate effects and turnout make presidential and mayoral results non-interchangeable.

- [x] **Step 3: Run fresh full verification**

```bash
caffeinate -i -m env PYTHONPATH=src python3 -m taipei_blue_vote --refresh
caffeinate -i -m env PYTHONPATH=src python3 -m unittest discover -s tests -v
caffeinate -i -m python3 -m compileall -q src tests
caffeinate -i -m git diff --check
```

Expected: official rebuild exits zero, all tests pass, compileall exits zero, and diff check prints nothing.

- [x] **Step 4: Review requirements and commit documentation**

Compare every design requirement with code, generated artifacts, charts, and prose. Confirm presidential files are unchanged except intentional comparison-chart references. Fix only in-scope gaps, rerun affected checks, then commit:

```bash
git add README.md report/findings.md docs/superpowers/plans/2026-10-11-taipei-mayor-analysis.md
git commit -m "docs: report Taipei mayor vote findings"
```

- [x] **Step 5: Push, integrate, and verify GitHub**

Push the feature branch and verify its SHA with `git ls-remote`. Fast-forward `main`, rerun the complete test suite on `main`, push `main`, and verify:

- the remote `main` SHA equals the local SHA;
- both mayor SVGs and all mayor CSVs are readable through the GitHub contents API;
- the newest GitHub Actions `test` workflow for `main` concludes successfully.
