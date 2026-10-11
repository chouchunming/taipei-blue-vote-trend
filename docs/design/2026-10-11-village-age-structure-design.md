# Village Age Structure Analysis — Design

## Goal

Estimate the 2024 village-level association between registered age structure and pan-blue presidential vote share in Taipei City, then publish a village table that separates actual vote share from the share predicted by demographics.

## Source and timing

Use Taipei City Open Data, dataset “臺北市各里人口數按年齡分,” resource “112年迄今-每月各里人口數按年齡分.” Select December 2023 (`年份=112`, `月份=12`, `性別=計`) so the population snapshot immediately precedes the January 2024 presidential election.

The CSV is CP950 encoded. District totals map the first eight digits of each 11-digit village code to the district name. Election and population records join on exact `(district, village)` keys.

## Variables

For every matched village, calculate registered-population shares for:

- age 20–39;
- age 40–64;
- age 65 and older;
- age 75 and older.

The model outcome is 2024 Hou You-yi vote share among valid presidential votes. Explanatory variables are age-20–39 share and age-65+ share; age 40–64 is the omitted age-composition reference. District fixed effects absorb broad between-district differences. Village valid votes are analysis weights.

## Outputs

- `data/derived/village_age_structure_2024.csv`: age shares, actual blue share, model-predicted blue share, residual, and actual/predicted ranks.
- `data/derived/age_model_2024.csv`: coefficient effects, including the predicted change associated with a 10-percentage-point composition change, observation count, matched coverage, and weighted R².
- `data/derived/age_source_manifest.json`: source URL, snapshot period, encoding, hash, and byte count.

## Interpretation limits

This is a weighted ecological association model, not an individual voter model. It cannot say that a particular older or younger person voted for a candidate, and it cannot isolate mortality, migration, turnout, family transmission, or persuasion. The fitted demographic prediction is a descriptive benchmark learned from the same 2024 village results, not a causal forecast.

The official open dataset begins in 2021. Therefore this feature supports a 2024 cross-section but cannot by itself decompose the full 2000–2024 trend into historical age-composition effects.

