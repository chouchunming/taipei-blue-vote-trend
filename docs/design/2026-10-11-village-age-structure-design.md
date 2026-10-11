# Village Age Structure Analysis — Design

## Goal

Estimate the 2024 village-level association between registered age structure and pan-blue presidential vote share in Taipei City, then publish a village table that separates actual vote share from the share predicted by demographics.

## Source and timing

Use the Ministry of the Interior Department of Household Registration dataset “村里戶數、單一年齡人口（新增區域代碼）” through API `ODRP014`. Select December 2023 (`11212`) so the population snapshot immediately precedes the January 2024 presidential election.

The API response is UTF-8 JSON with male and female counts for every single age. Page 1 contains all 456 Taipei records for this snapshot; the parser filters `site_id` to Taipei City and validates that every single-age count sums to the reported village total. Election and population records join on exact `(district, village)` keys, and a rebuild fails if any 2024 election village is unmatched.

## Variables

For every matched village, calculate registered-population shares for:

- age 20–39;
- age 40–64;
- age 65 and older;
- age 75 and older.

The model outcome is 2024 Hou You-yi vote share among valid presidential votes. Explanatory variables are age-20–39 share and age-65+ share. District fixed effects absorb broad between-district differences. Village valid votes are analysis weights.

## Outputs

- `data/derived/village_age_structure_2024.csv`: age shares, actual blue share, model-predicted blue share, residual, and actual/predicted ranks.
- `data/derived/age_model_2024.csv`: coefficient effects, including the predicted change associated with a 10-percentage-point composition change, observation count, matched coverage, and weighted R².
- `data/derived/age_source_manifest.json`: source URL, snapshot period, encoding, hash, and byte count.
- `charts/village-age-model-2024.svg` and `.html`: actual-versus-predicted village shares and the two age-composition coefficients.

## Interpretation limits

This is a weighted ecological association model, not an individual voter model. It cannot say that a particular older or younger person voted for a candidate, and it cannot isolate mortality, migration, turnout, family transmission, or persuasion. The fitted demographic prediction is a descriptive benchmark learned from the same 2024 village results, not a causal forecast.

This implementation uses the December-2023 cross-section aligned to the 2024 election. It does not attempt to reconcile historical village-boundary changes or fit comparable pre-election snapshots back to 2000, so it cannot by itself decompose the full 2000–2024 trend into historical age-composition effects.
