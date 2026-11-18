# DriveQuest — problem brief

## Customer

**Primary:** Car shoppers on a dealer’s website who already know they want *a* vehicle but not *which one*.

**Secondary:** Dealer groups and rooftops who embed DriveQuest to turn browsing into qualified shortlists without commission-pressure sales tactics.

## Pain: choice overload

Typical inventory search returns dozens of similar trims with overlapping specs. Shoppers must mentally trade off price, fuel cost, reliability reputation, safety ratings, and day-to-day practicality — while marketing pages push “best seller” and finance specials that may not fit how they actually drive.

Result: long time on site, tab fatigue, bounce, or a test drive for the wrong body style.

## Product hook

**“3 cars that fit how you drive.”**

A short progressive quiz (budget → body → priority → condition) narrows the lot, then hex-axis scores surface a **top-three shortlist** the shopper can compare on one radar — lifestyle, ops cost, and performance in one view, scoped to **this dealer’s inventory only**.

## Success metrics

| Stakeholder | Metric | POC proxy |
|-------------|--------|-----------|
| Shopper | Time to a confident shortlist | Quest stages completed → top-3 shown (≤ ~2 min in demo) |
| Dealer | Engagement on embed | Session starts → compare stage → best-match click |
| Data / product | Shortlist quality | Top-3 overlap stable when priority axis changes (see [EDA](../reports/drivequest_eda_summary.md)) |

## Scope for this iteration

- **Data:** Public curated fixture [`data/car_catalog.json`](../data/car_catalog.json) (18 vehicles; no PII).
- **Scoring:** Rule-based hex axes in `backend/recommendation_engine.py` — not a black-box ML model.
- **Out of scope:** Cross-dealer inventory, third-party reliability certifications, or production analytics pipelines (iter 3).

## Related docs

- [Shopper funnel](./shopper_funnel.md) — quiz → scores → shortlist narrative
- [Shopper experience](./shopper-experience.md) — POC UX detail
- [EDA summary](../reports/drivequest_eda_summary.md) — attribute distributions and score sensitivity