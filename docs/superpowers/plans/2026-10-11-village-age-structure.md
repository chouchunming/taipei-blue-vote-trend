# Village Age Structure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a tested December-2023 village population parser and weighted 2024 age-structure association model to the existing Taipei vote repository.

**Architecture:** Decode and normalize the official population CSV into typed village rows, join exact keys to the already-validated 2024 election aggregates, and fit a dependency-free weighted least-squares model with district fixed effects. Keep population source provenance and derived outputs separate from the election manifest.

**Tech Stack:** Python 3.11+ standard library, `csv`, typed dataclasses, small-matrix Gaussian elimination, `unittest`.

## Global Constraints

- Use December 2023 (`112/12`) registered population to align with the January 2024 election.
- Join only exact district-and-village keys and report match coverage.
- Use age-20–39 share and age-65+ share with district fixed effects; weight by valid votes.
- Describe coefficients as ecological associations, never individual behavior or causation.
- Keep runtime dependencies at zero.

---

### Task 1: Parse and join official population data

**Files:**
- Create: `src/taipei_blue_vote/age_structure.py`
- Create: `tests/test_age_structure.py`

**Interfaces:**
- Consumes: CP950 CSV bytes and 2024 `VillageResult` rows.
- Produces: `PopulationRow` and `AgeObservation` records keyed by `(district, village)`.

- [ ] **Step 1: Write failing tests for CP950 parsing, age bands, and exact-key joins**

```python
population = parse_population_csv(payload, roc_year=112, month=12)
self.assertEqual(population[0].district, "信義區")
self.assertEqual(population[0].age_20_39, 20)
observations, coverage = join_age_and_votes(population, votes)
self.assertEqual(coverage, (1, 1))
```

- [ ] **Step 2: Run the focused test and verify RED**

Run: `PYTHONPATH=src caffeinate -i -m python3 -m unittest tests.test_age_structure -v`

Expected: import failure because `age_structure` does not exist.

- [ ] **Step 3: Implement typed parsing and exact joins**

```python
def age_sum(source, start, end):
    return sum(int(source[f"{age}歲數量"]) for age in range(start, end + 1))


def population_share(count, total):
    if total <= 0:
        raise ValueError("population total must be positive")
    return count / total
```

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `PYTHONPATH=src caffeinate -i -m python3 -m unittest tests.test_age_structure -v`

Expected: parser and join tests pass.

### Task 2: Fit and export the weighted ecological model

**Files:**
- Modify: `src/taipei_blue_vote/age_structure.py`
- Create: `tests/test_age_model.py`
- Modify: `src/taipei_blue_vote/rebuild.py`
- Modify: `README.md`
- Modify: `report/findings.md`

**Interfaces:**
- Consumes: matched `AgeObservation` rows.
- Produces: coefficient rows, weighted R², village predictions and ranks.

- [ ] **Step 1: Write failing tests for exact weighted least squares and model outputs**

```python
coefficients = weighted_least_squares(
    [[1.0, 0.0], [1.0, 1.0], [1.0, 2.0]],
    [1.0, 3.0, 5.0],
    [1.0, 1.0, 1.0],
)
self.assertAlmostEqual(coefficients[0], 1.0)
self.assertAlmostEqual(coefficients[1], 2.0)
```

- [ ] **Step 2: Run model tests and verify RED**

Run: `PYTHONPATH=src caffeinate -i -m python3 -m unittest tests.test_age_model -v`

Expected: missing model functions.

- [ ] **Step 3: Implement Gaussian elimination, district fixed effects, prediction, weighted R², and deterministic CSV output**

```python
xtwx = [[sum(w * x[i] * x[j] for x, w in zip(rows, weights)) for j in range(k)] for i in range(k)]
xtwy = [sum(w * x[i] * y for x, y, w in zip(rows, targets, weights)) for i in range(k)]
coefficients = solve_linear_system(xtwx, xtwy)
```

- [ ] **Step 4: Rebuild from the official source and verify coverage and artifact content**

Run: `PYTHONPATH=src caffeinate -i -m python3 -m taipei_blue_vote --refresh`

Expected: all 2024 election villages match December-2023 population records or unmatched keys are explicitly reported as a validation failure.

- [ ] **Step 5: Run the complete suite, commit, merge, and push**

Run: `PYTHONPATH=src caffeinate -i -m python3 -m unittest discover -s tests -v`

Run: `caffeinate -i -m python3 -m compileall -q src tests`

Run: `git diff --check`

Expected: all commands exit zero before merge and push.
