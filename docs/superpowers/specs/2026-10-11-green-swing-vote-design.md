# Taipei Green Base and Swing-Vote Analysis Design

## Goal

Extend the existing Taipei presidential-vote analysis with two transparent,
reproducible views:

1. the citywide and fixed-cohort trend of the pan-green electoral base from
   2000 through 2024; and
2. the observable third-candidate vote plus an election-to-election measure of
   net bloc volatility as a proxy for the changing swing-vote space.

The output must not claim that aggregate election returns identify individual
independent or centrist voters.

## Bloc classification

The existing pan-blue classification remains unchanged. The pan-green
classification is:

| Election | Pan-green candidate |
|---|---|
| 2000 | 陳水扁 |
| 2004 | 陳水扁 |
| 2008 | 謝長廷 |
| 2012 | 蔡英文 |
| 2016 | 蔡英文 |
| 2020 | 蔡英文 |
| 2024 | 賴清德 |

For every village and election:

- `blue_votes` is the sum of the configured pan-blue candidates;
- `green_votes` is the configured pan-green candidate;
- `other_votes = valid_votes - blue_votes - green_votes`.

The `other` category is an observed candidate-choice category, not a count of
all centrist voters. Under the existing blue classification it contains
許信良 and 李敖 in 2000, no votes in 2004–2020, and 柯文哲 in 2024.
宋楚瑜 remains in the pan-blue category in 2000, 2012, 2016, and 2020.

## Pan-green base measures

### Citywide series

For all seven elections, report green votes, green share of valid votes, and
changes from both the previous election and the 2000 baseline.

### Fixed deep-green cohort

Select villages once from the 2000 election and keep that membership fixed:

- at least 100 valid presidential votes in 2000;
- pan-green share of at least 45% in 2000; and
- an exact `(district, village)` match in all seven elections.

The threshold identifies villages materially above the 2000 Taipei citywide
green share of 37.64% while retaining a useful fixed sample. The expected
official-data rebuild contains 86 villages; the pipeline must calculate and
validate the actual count rather than hard-code membership.

## Swing-vote measures

### Observable third-candidate vote

Report `other_votes` and `other_share` directly. This is the strictest
observable proxy for a non-blue/non-green choice, but it is structurally zero
in elections where every candidate is classified into one of the two blocs.

### Three-bloc electoral volatility

For each election after 2000, calculate total variation across the blue,
green, and other vote shares relative to the previous election:

```text
volatility_pp = 0.5 * (
    abs(delta_blue_share)
    + abs(delta_green_share)
    + abs(delta_other_share)
)
```

This is the minimum net share that must have shifted between the three
categories to produce the aggregate result. Convert it to a current-election
vote equivalent as:

```text
volatility_vote_equivalent = round(valid_votes_current * volatility_pp / 100)
```

The vote equivalent is a scale translation, not a headcount of identifiable
people who changed their vote. It can also reflect turnout and electorate
composition changes.

## Data model and pipeline

Extend `VillageResult` and `ElectionResult` with `green_votes` and
`other_votes`, plus share properties. Keep `ko_votes` for backward-compatible
2024 reporting. Generalize fixed-cohort selection to accept a bloc-share
selector so the existing deep-blue cohort remains unchanged and the new
deep-green cohort uses the same exact-key and minimum-valid safeguards.

Extend `AnalysisBundle` with the deep-green keys and summaries plus green
deltas and three-bloc volatility rows. Candidate-coverage validation must
verify all configured green candidates as well as the existing blue set.

## Outputs

Update or add these committed artifacts:

- `data/derived/city_trend.csv`: blue, green, other, and Ko votes/shares plus
  changes from 2000;
- `data/derived/deep_green_cohort.csv`: fixed-cohort votes, shares, and changes;
- `data/derived/bloc_deltas.csv`: election-to-election blue, green, and other
  changes;
- `data/derived/electoral_volatility.csv`: share volatility and current-vote
  equivalent;
- `charts/taipei-bloc-and-volatility.svg` and `.html`: bloc shares over time
  and the volatility series;
- `README.md` and `report/findings.md`: definitions, headline findings, and
  interpretation limits.

The existing blue-delta chart and age-structure chart remain available.

## Error handling and validation

- Reject unsupported election years, negative votes, non-positive village
  valid totals, overlapping configured blue/green candidate sets, and negative
  computed `other_votes`.
- Require all configured blue and green candidates to appear in their election
  source.
- Keep exact village matching for both fixed cohorts.
- Generate all CSV and chart outputs deterministically.

## Testing

Use test-driven development for:

- candidate classification into blue, green, and other;
- green and other shares;
- generalized fixed-cohort selection;
- the three-bloc volatility formula and vote equivalent;
- pipeline composition and artifact schemas;
- SVG/HTML content and signed values;
- end-to-end fixture rebuilds and unchanged official city totals.

Before push, run the official-source rebuild, the full unit suite, `compileall`,
and Git diff checks. The GitHub workflow must pass on the pushed commit.

## Interpretation limits

- `other_votes` is a candidate-choice category, not a party-identification or
  ideological measure.
- Volatility measures aggregate net change, not gross individual switching;
  offsetting switches are invisible.
- Changes may combine persuasion, turnout, migration, death, newly eligible
  voters, candidate effects, and boundary changes.
- A fixed deep-green village is a geographic cohort, not a list of individual
  core supporters.
