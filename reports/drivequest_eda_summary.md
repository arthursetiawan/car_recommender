# DriveQuest EDA summary

Exploratory analysis of the **public car catalog fixture** and the **hex scoring engine** used in the shopper quest. Supports [problem brief](../docs/problem.md) and [shopper funnel](../docs/shopper_funnel.md).

## Fixture overview

- **Source:** `data/car_catalog.json`
- **Rows:** 18 (public demo inventory; synthetic/curated, no PII)
- **Generated:** 2026-11-18 03:16 UTC via `scripts/drivequest_eda.py`

## Attribute distributions

### Price

| Stat | Value |
|------|-------|
| Min | $11,214 |
| Median | $24,200 |
| Mean | $24,178 |
| Max | $42,385 |
| Stdev | $7,961 |

### Mileage

Median **34,000** mi (range 0–110,405).

### Model year

Median **2022** (range 2011–2025).

### MPG (or MPGe for EVs)

Median **32** (range 23–120).

### Reliability score (1–10 scale in fixture)

Median **8.4** (stdev 1.11).

### Categorical mix

| body_type | Count | Share |
|-----------|-------|-------|
| sedan | 7 | 38.9% |
| suv | 7 | 38.9% |
| hatchback | 2 | 11.1% |
| wagon | 1 | 5.6% |
| truck | 1 | 5.6% |

| fuel_type | Count | Share |
|-----------|-------|-------|
| gas | 9 | 50.0% |
| hybrid | 7 | 38.9% |
| electric | 2 | 11.1% |

| condition | Count | Share |
|-----------|-------|-------|
| used | 16 | 88.9% |
| new | 2 | 11.1% |


## Budget funnel (eligible units)

How fast the lot collapses as budget tightens (before priority scoring):

| Max budget | Eligible cars |
|------------|-----------------|
| $15,000 | 3 |
| $20,000 | 5 |
| $25,000 | 12 |
| $30,000 | 15 |
| $35,000 | 17 |
| $50,000 | 18 |


## Baseline hex scores (budget = $35k, no priority boost)

Per-axis scores across all 18 cars before quest filters (illustrates scoring spread on the fixture).

| Axis | Min | Median | Max | Stdev |
|------|-----|--------|-----|-------|
| Value | 0.00 | 5.64 | 6.19 | 1.70 |
| Budget Fit | 0.78 | 7.62 | 9.89 | 2.45 |
| Reliability | 5.50 | 8.35 | 9.20 | 1.11 |
| Efficiency | 6.05 | 8.69 | 10.00 | 1.22 |
| Safety | 8.00 | 10.00 | 10.00 | 0.78 |
| Practicality | 4.92 | 7.64 | 9.12 | 1.02 |


## Score sensitivity — persona shortlists (top 3)

Same scoring code as `/api/catalog` and the quest compare stage. Shows how **priority** and **filters** change the shortlist — the core “3 cars that fit how you drive” promise.

### Commuter sedan — $25k, reliability priority

- **Eligible after filters:** 7 of 18

| Rank | Vehicle | Overall | Top axis (score) |
|------|---------|---------|------------------|
| 1 | 2023 Toyota Corolla | 8.58 | Safety (10.0) |
| 2 | 2023 Honda Civic | 8.45 | Safety (10.0) |
| 3 | 2019 Honda Accord | 8.30 | Safety (10.0) |

### Family SUV — $35k, practicality priority

- **Eligible after filters:** 6 of 18

| Rank | Vehicle | Overall | Top axis (score) |
|------|---------|---------|------------------|
| 1 | 2020 Toyota Highlander | 8.41 | Safety (10.0) |
| 2 | 2021 Toyota RAV4 | 8.31 | Safety (10.0) |
| 3 | 2022 Mazda CX-5 | 8.11 | Safety (10.0) |

### Efficiency seeker — $30k, any body, efficiency priority

- **Eligible after filters:** 15 of 18

| Rank | Vehicle | Overall | Top axis (score) |
|------|---------|---------|------------------|
| 1 | 2023 Honda Civic | 8.47 | Safety (10.0) |
| 2 | 2022 Toyota Camry | 8.45 | Safety (10.0) |
| 3 | 2021 Tesla Model 3 | 8.40 | Efficiency (10.0) |

### Budget hawk — $15k, value priority

- **Eligible after filters:** 3 of 18

| Rank | Vehicle | Overall | Top axis (score) |
|------|---------|---------|------------------|
| 1 | 2014 Volkswagen Jetta Hybrid | 6.36 | Efficiency (10.0) |
| 2 | 2014 Nissan Pathfinder Hybrid | 6.24 | Budget Fit (9.3) |
| 3 | 2011 MINI Cooper S | 5.07 | Budget Fit (9.7) |

### EV lean — $35k, prefer_ev=True, efficiency priority

- **Eligible after filters:** 17 of 18

| Rank | Vehicle | Overall | Top axis (score) |
|------|---------|---------|------------------|
| 1 | 2023 Ford Maverick | 8.48 | Efficiency (9.9) |
| 2 | 2021 Tesla Model 3 | 8.34 | Efficiency (10.0) |
| 3 | 2021 Toyota RAV4 | 8.28 | Safety (10.0) |

### Shortlist diversity

Pairwise overlap of top-3 vehicle IDs across the five personas (lower overlap → quest segmentation matters).

| Persona A | Persona B | Shared in top 3 |
|-----------|-----------|-----------------|
| Commuter sedan | Family SUV | 0 |
| Commuter sedan | Efficiency seeker | 1 |
| Commuter sedan | Budget hawk | 0 |
| Commuter sedan | EV lean | 0 |
| Family SUV | Efficiency seeker | 0 |
| Family SUV | Budget hawk | 0 |
| Family SUV | EV lean | 1 |
| Efficiency seeker | Budget hawk | 0 |
| Efficiency seeker | EV lean | 1 |
| Budget hawk | EV lean | 0 |


## Priority axis sensitivity ($30k, any body)

Overall score for **2023 Honda Civic** when only the stated priority (2× axis weight) changes:

| Priority (2× weight) | Civic overall | Civic rank (of eligible) |
|----------------------|---------------|---------------------------|
| reliability | 8.49 | 2 / 15 |
| value | 8.04 | 2 / 15 |
| efficiency | 8.47 | 1 / 15 |
| practicality | 8.27 | 3 / 15 |
| safety | 8.66 | 1 / 15 |

**Takeaway:** Priority chip materially reorders the shortlist without retraining — weights in `PreferenceState.weights()` drive business-visible differentiation.


## Reproduce

```bash
python scripts/drivequest_eda.py
```
