# Taipei Mayor Vote Trend Design

**Date:** 2026-10-11

## Goal

Extend the reproducible Taipei election analysis with all six mayoral elections from 2002 through 2022. Measure blue, green, and other-candidate votes; election-to-election change; aggregate electoral volatility; and fixed village cohorts without mixing mayoral and presidential contests into one continuous series.

## Scope

Included:

- Taipei mayor elections in 2002, 2006, 2010, 2014, 2018, and 2022.
- Citywide candidate, bloc, delta, and volatility results.
- A primary coalition-alignment classification and an official-nomination sensitivity classification.
- Fixed deep-blue and deep-green village cohorts selected from 2002 and followed through all six elections.
- A mayor-specific chart and a separate presidential-versus-mayoral comparison chart.
- Deterministic CSV, SVG, HTML, source manifest, tests, README, and report updates.

Excluded:

- Elections before 2002.
- Council, district, or neighborhood-chief elections.
- Treating mayor and president results as one interchangeable time series.
- Extending the 2024 age-structure model to historical mayoral elections.
- Claims about identified individual switching, death, migration, or generational replacement.

## Source and Coverage

Use the TaiwanVotes normalized Central Election Commission CSV index already used by the project. Select exactly one `縣市長` vote file for Taipei for each target year:

- 2002: `縣市長_2001-02_臺北市.csv`
- 2006: `縣市長_2005-06_臺北市.csv`
- 2010: `縣市長_2009-10_臺北市.csv`
- 2014: `縣市長_2014_臺北市.csv`
- 2018: `縣市長_2018_臺北市.csv`
- 2022: `縣市長_2022_臺北市.csv`

The files use the same village-level vote schema as the presidential source, with an additional party field. Raw downloads remain gitignored. A committed mayor source manifest records file names, URLs, hashes, byte counts, row counts, and upstream index metadata.

## Classification Scenarios

Every candidate belongs to exactly one of blue, green, or other within a scenario. Candidate maps are explicit and validated for overlap.

### Coalition alignment — primary analysis

| Year | Blue | Green | Other |
|---|---|---|---|
| 2002 | 馬英九 | 李應元 | none |
| 2006 | 郝龍斌、宋楚瑜 | 謝長廷、周玉蔻 | 李敖、柯賜海 |
| 2010 | 郝龍斌 | 蘇貞昌 | 吳炎成、蕭淑華、吳武明 |
| 2014 | 連勝文 | 柯文哲 | 陳汝斌、趙衍慶、李宏信、陳永昌、馮光遠 |
| 2018 | 丁守中 | 姚文智 | 柯文哲、吳蕚洋、李錫錕 |
| 2022 | 蔣萬安 | 陳時中 | 張家豪、王文娟、鄭匡宇、黃聖峰、童文薰、蘇煥智、黃珊珊、施奉先、唐新民、謝立康 |

The 2014 Ko Wen-je vote is assigned to the green-backed electoral alliance. His 2018 vote remains other because the DPP nominated its own candidate. James Soong is assigned to blue in 2006, while Taiwan Solidarity Union candidate 周玉蔻 is assigned to green.

### Official nomination — sensitivity analysis

- Blue contains only the Kuomintang nominee in each election.
- Green contains only the Democratic Progressive Party nominee in each election.
- Every other party and independent candidate is other.
- Consequently, Ko Wen-je is other in both 2014 and 2018, and the official-nomination green category is zero in 2014 because the DPP did not nominate a candidate.

The report must not describe the official-nomination scenario as the underlying green electorate. It exists to show how sensitive the result is to candidate classification.

## Analysis Model

Create a mayor-specific analysis boundary so the established presidential candidate definitions and artifacts remain unchanged.

The mayor module will:

1. aggregate normalized candidate rows to village and city results for a requested scenario;
2. retain candidate totals for classification transparency;
3. compute blue, green, and other vote shares;
4. compute adjacent-election vote and percentage-point changes;
5. compute three-bloc total-variation volatility and its current-election vote equivalent;
6. select and summarize fixed coalition-classification cohorts.

The volatility formula remains:

```text
0.5 × (|Δ blue share| + |Δ green share| + |Δ other share|)
```

The vote equivalent is the volatility percentage multiplied by current-election valid votes. It is an aggregate scale, not a count of identified switchers.

## Fixed Village Cohorts

The cohort analysis uses only the primary coalition classification:

- Deep blue: 2002 blue share at least 65%, at least 100 valid votes, and exact district-plus-village presence in all six elections.
- Deep green: 2002 green share at least 45%, at least 100 valid votes, and exact district-plus-village presence in all six elections.

Selection happens once in 2002; the same village keys are followed through 2022. Renamed, split, or merged villages are excluded rather than heuristically joined. The resulting cohort counts are generated from data and documented after the official rebuild.

## Data Flow and Components

1. `sources.py` selects and downloads the six mayor CSVs and parses their shared vote fields.
2. A new mayor analysis module owns years, scenario maps, aggregation, candidate totals, cohort selection, deltas, and volatility.
3. `rebuild.py` rebuilds presidential artifacts as before, then independently rebuilds mayor artifacts from the same index.
4. Mayor artifact writing emits deterministic CSVs and charts without changing presidential schemas.
5. Documentation compares endpoint and election-to-election trends while keeping contest types visually distinct.

## Outputs

Committed derived data:

- `data/derived/mayor_candidate_totals.csv`
- `data/derived/mayor_city_trend.csv`
- `data/derived/mayor_bloc_deltas.csv`
- `data/derived/mayor_electoral_volatility.csv`
- `data/derived/mayor_deep_blue_cohort.csv`
- `data/derived/mayor_deep_green_cohort.csv`
- `data/derived/mayor_source_manifest.json`

The first four tables include a `classification` column with `coalition` and `official_nomination` values. Cohort tables are explicitly labelled as coalition classification.

Committed charts:

- `charts/taipei-mayor-bloc-and-volatility.svg`
- `charts/taipei-mayor-bloc-and-volatility.html`
- `charts/taipei-presidential-mayor-comparison.svg`
- `charts/taipei-presidential-mayor-comparison.html`

The mayor chart shows the coalition series prominently and the official-nomination result as a sensitivity comparison, especially for 2014. The comparison chart uses separate panels or clearly distinct line styles for presidential and mayoral contests; it never interpolates them as one series.

## Validation and Error Handling

- Reject missing or duplicate mayor files for target years.
- Reject missing configured candidates and any candidate classified into both blue and green within one scenario.
- Verify every parsed row contains a supported year, non-negative vote count, and positive village valid-vote total.
- Hard-code verified citywide valid, blue, green, and other totals for both scenarios after the first official rebuild so later source or classification drift fails loudly.
- Assert blue plus green plus other equals valid votes at village and city levels.
- Allow an empty fixed cohort or an all-zero volatility fixture to produce deterministic output rather than crash.

## Tests

Use test-driven development for:

- source selection and schema parsing;
- 2006 Song/TSU classification;
- 2014 Ko scenario divergence;
- 2018 Ko remaining other in both scenarios;
- 2022 Huang Shan-shan remaining other;
- candidate overlap and coverage validation;
- city totals, deltas, volatility, and fixed cohorts;
- deterministic artifact schemas;
- SVG content, accessibility labels, and zero-volatility handling;
- end-to-end rebuild from in-memory payloads without network access.

Release verification includes an official refresh, the entire test suite, bytecode compilation, diff checks, visual chart inspection, remote SHA verification, and a successful GitHub Actions run.

## Interpretation Rules

- “Coalition blue/green” is an explicit analytical classification, not an official CEC field.
- “Official nomination” measures nominees, not every voter who identifies with a bloc.
- Other-candidate votes do not equal ideological centrists.
- Volatility is an aggregate minimum net distribution change, not identified individual switching.
- Vote-count and vote-share changes must be reported separately.
- Mayor and presidential elections may be compared, but candidate appeal, turnout, office, and election context prevent direct causal equivalence.
