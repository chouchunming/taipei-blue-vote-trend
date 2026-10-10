# Taipei Blue Vote Trend — Design

**Status:** Approved through the user’s requests to continue, create the GitHub repository, and include the chart.

## Goal

Build a reproducible analysis of Taipei City presidential voting from 2000 through 2024 that measures:

1. citywide pan-blue vote and vote-share change;
2. change in a fixed cohort of villages that were deeply blue in 2000;
3. change in explicitly labeled military-village location proxies; and
4. a bounded estimate of 2024 KMT votes from voters aged 20–39 who were not eligible in 2000.

The repository must include derived data, documented source provenance, tested Python code, a readable report, and chart files that GitHub can preview.

## Definitions

The primary series counts these presidential candidates as pan-blue:

| Election | Candidates counted |
|---|---|
| 2000 | 宋楚瑜、連戰 |
| 2004 | 連戰 |
| 2008 | 馬英九 |
| 2012 | 馬英九、宋楚瑜 |
| 2016 | 朱立倫、宋楚瑜 |
| 2020 | 韓國瑜、宋楚瑜 |
| 2024 | 侯友宜 |

柯文哲 is reported separately as non-green in 2024 and is not counted as pan-blue.

The fixed deep-blue cohort is the set of Taipei villages with at least 100 valid presidential votes and at least 65% pan-blue share in 2000, restricted to village keys present in every election from 2000 through 2024.

Military-village results are geographic proxies, not a count of military-village descendants. The continuously comparable core contains 景新里、 西村里、林泉里、富水里; 學府里 is shown from 2004 because it is not continuously comparable from 2000.

## Sources

- Central Election Commission election data, distributed in normalized CSV form by TaiwanVotes from the CEC open-data release.
- Taipei and CEC electorate-by-age statistics for the number of 20–39-year-old eligible voters.
- Official CEC age-turnout study for approximate young-adult turnout.
- TVBS and United Daily News age-group polls for a bounded 2024 Hou You-yi support estimate.

Every downloaded election file is recorded with its URL and SHA-256 digest. Raw downloads are reproducible but gitignored; compact derived CSV files and a source manifest are committed.

## Calculations

For each election and geography:

- valid votes = sum of votes for every presidential candidate;
- pan-blue votes = sum for the candidates in the definition table;
- pan-blue share = pan-blue votes / valid votes × 100;
- election delta = current election value − previous election value.

The young replacement estimate uses 571,536 eligible Taipei voters aged 20–39 in 2024, an approximate 71.5% turnout, and a survey-supported Hou vote-share range. It is presented as a range with a central estimate, not as official candidate-by-age data or individual-level causal identification.

## Repository layout

- `src/taipei_blue_vote/`: source definitions, parsing, aggregation, output, and chart rendering.
- `tests/`: unit tests using small in-memory fixtures, without network mocks.
- `data/derived/`: committed analysis tables and source manifest.
- `charts/`: GitHub-previewable SVG and standalone HTML.
- `report/`: findings, method, caveats, and citations.
- `docs/superpowers/plans/`: implementation plan.
- `.github/workflows/`: automated unit-test workflow.

## Validation and failure behavior

- Fail when an expected candidate is missing, a vote is negative, a denominator is zero, or a requested village is absent.
- Unit-test candidate classification, aggregation, fixed-cohort selection, election deltas, young-vote estimation, CSV output, and chart labels.
- Rebuild all committed derived artifacts from downloaded source files and compare key totals against the expected citywide series before release.

## Known limitations

- The changing candidate field means “pan-blue” is an explicit analytic classification, not an official CEC category.
- Aggregate village results cannot identify how an individual voted or distinguish death, migration, redevelopment, turnout, and persuasion effects.
- The 2024 young-vote estimate combines official population/turnout statistics with survey support rates and therefore remains an estimate.
- Administrative-boundary continuity is handled through exact district-and-village matching; unmatched or renamed villages are excluded from the fixed cohort.
