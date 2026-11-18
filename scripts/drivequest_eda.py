#!/usr/bin/env python3
"""EDA on public DriveQuest inventory fixture: distributions + score sensitivity.

Reads data/car_catalog.json (no network). Writes reports/drivequest_eda_summary.md.
Uses the same scoring functions as production (backend/recommendation_engine.py).
"""

from __future__ import annotations

import json
import statistics
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from recommendation_engine import (  # noqa: E402
    HEX_AXES,
    HEX_AXIS_LABELS,
    PreferenceState,
    enrich_car,
    filter_catalog,
    rank_cars,
    score_car,
)

CATALOG_PATH = ROOT / "data" / "car_catalog.json"
REPORT_PATH = ROOT / "reports" / "drivequest_eda_summary.md"


def load_catalog() -> list[dict]:
    with open(CATALOG_PATH, encoding="utf-8") as f:
        return json.load(f)


def pct(n: int, total: int) -> str:
    if total == 0:
        return "0%"
    return f"{100 * n / total:.1f}%"


def describe_numeric(values: list[float]) -> dict[str, float]:
    if not values:
        return {}
    vals = sorted(values)
    return {
        "n": len(vals),
        "min": vals[0],
        "p25": vals[len(vals) // 4],
        "median": statistics.median(vals),
        "mean": statistics.mean(vals),
        "p75": vals[3 * len(vals) // 4],
        "max": vals[-1],
        "stdev": statistics.stdev(vals) if len(vals) > 1 else 0.0,
    }


def fmt_money(x: float) -> str:
    return f"${x:,.0f}"


def distribution_section(cars: list[dict]) -> str:
    n = len(cars)
    prices = [float(c["price"]) for c in cars]
    miles = [float(c.get("mileage") or 0) for c in cars]
    years = [int(c["year"]) for c in cars]
    mpgs = [float(c.get("mpg") or 0) for c in cars]
    rel = [float(c.get("reliability") or 7) for c in cars]

    body = Counter(c.get("body_type", "?") for c in cars)
    fuel = Counter((c.get("fuel_type") or "gas").lower() for c in cars)
    cond = Counter(c.get("condition", "?") for c in cars)

    pstats = describe_numeric(prices)
    mstats = describe_numeric(miles)
    ystats = describe_numeric([float(y) for y in years])
    mpgstats = describe_numeric(mpgs)
    rstats = describe_numeric(rel)

    lines = [
        "## Fixture overview",
        "",
        f"- **Source:** `{CATALOG_PATH.relative_to(ROOT)}`",
        f"- **Rows:** {n} (public demo inventory; synthetic/curated, no PII)",
        f"- **Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} via `scripts/drivequest_eda.py`",
        "",
        "## Attribute distributions",
        "",
        "### Price",
        "",
        "| Stat | Value |",
        "|------|-------|",
        f"| Min | {fmt_money(pstats['min'])} |",
        f"| Median | {fmt_money(pstats['median'])} |",
        f"| Mean | {fmt_money(pstats['mean'])} |",
        f"| Max | {fmt_money(pstats['max'])} |",
        f"| Stdev | {fmt_money(pstats['stdev'])} |",
        "",
        "### Mileage",
        "",
        f"Median **{mstats['median']:,.0f}** mi (range {mstats['min']:,.0f}–{mstats['max']:,.0f}).",
        "",
        "### Model year",
        "",
        f"Median **{ystats['median']:.0f}** (range {ystats['min']:.0f}–{ystats['max']:.0f}).",
        "",
        "### MPG (or MPGe for EVs)",
        "",
        f"Median **{mpgstats['median']:.0f}** (range {mpgstats['min']:.0f}–{mpgstats['max']:.0f}).",
        "",
        "### Reliability score (1–10 scale in fixture)",
        "",
        f"Median **{rstats['median']:.1f}** (stdev {rstats['stdev']:.2f}).",
        "",
        "### Categorical mix",
        "",
        "| body_type | Count | Share |",
        "|-----------|-------|-------|",
    ]
    for k, v in body.most_common():
        lines.append(f"| {k} | {v} | {pct(v, n)} |")
    lines += ["", "| fuel_type | Count | Share |", "|-----------|-------|-------|"]
    for k, v in fuel.most_common():
        lines.append(f"| {k} | {v} | {pct(v, n)} |")
    lines += ["", "| condition | Count | Share |", "|-----------|-------|-------|"]
    for k, v in cond.most_common():
        lines.append(f"| {k} | {v} | {pct(v, n)} |")

    return "\n".join(lines) + "\n"


def axis_baseline_section(cars: list[dict], budget: float = 35_000) -> str:
    """Unweighted axis distributions at a representative budget."""
    rows = []
    for c in cars:
        m = score_car(c, budget=budget)
        rows.append(m)

    lines = [
        "",
        "## Baseline hex scores (budget = $35k, no priority boost)",
        "",
        "Per-axis scores across all 18 cars before quest filters (illustrates scoring spread on the fixture).",
        "",
        "| Axis | Min | Median | Max | Stdev |",
        "|------|-----|--------|-----|-------|",
    ]
    for axis in HEX_AXES:
        vals = [r[axis] for r in rows]
        st = describe_numeric(vals)
        lines.append(
            f"| {HEX_AXIS_LABELS[axis]} | {st['min']:.2f} | {st['median']:.2f} | {st['max']:.2f} | {st['stdev']:.2f} |"
        )
    return "\n".join(lines) + "\n"


def car_label(c: dict) -> str:
    return f"{c['year']} {c['make']} {c['model']}"


def scenario_rankings(cars: list[dict]) -> str:
    scenarios: list[tuple[str, PreferenceState]] = [
        (
            "Commuter sedan — $25k, reliability priority",
            PreferenceState(
                budget=25_000,
                body_types=["sedan"],
                priority="reliability",
                condition="either",
                stage="compare",
            ),
        ),
        (
            "Family SUV — $35k, practicality priority",
            PreferenceState(
                budget=35_000,
                body_types=["suv"],
                priority="practicality",
                condition="either",
                stage="compare",
            ),
        ),
        (
            "Efficiency seeker — $30k, any body, efficiency priority",
            PreferenceState(
                budget=30_000,
                body_types=["any"],
                priority="efficiency",
                condition="either",
                stage="compare",
            ),
        ),
        (
            "Budget hawk — $15k, value priority",
            PreferenceState(
                budget=15_000,
                body_types=["any"],
                priority="value",
                condition="used",
                stage="compare",
            ),
        ),
        (
            "EV lean — $35k, prefer_ev=True, efficiency priority",
            PreferenceState(
                budget=35_000,
                body_types=["any"],
                priority="efficiency",
                condition="either",
                prefer_ev=True,
                stage="compare",
            ),
        ),
    ]

    lines = [
        "",
        "## Score sensitivity — persona shortlists (top 3)",
        "",
        "Same scoring code as `/api/catalog` and the quest compare stage. "
        "Shows how **priority** and **filters** change the shortlist — the core “3 cars that fit how you drive” promise.",
        "",
    ]

    all_tops: list[set[str]] = []
    for title, prefs in scenarios:
        filtered = filter_catalog(cars, prefs)
        ranked = rank_cars(cars, prefs, limit=3)
        ids = {c["id"] for c in ranked}
        all_tops.append(ids)

        lines += [
            f"### {title}",
            "",
            f"- **Eligible after filters:** {len(filtered)} of {len(cars)}",
            "",
            "| Rank | Vehicle | Overall | Top axis (score) |",
            "|------|---------|---------|------------------|",
        ]
        for i, c in enumerate(ranked, start=1):
            metrics = c["metrics"]
            top_axis = max(HEX_AXES, key=lambda a: metrics[a])
            lines.append(
                f"| {i} | {car_label(c)} | {c['overall']:.2f} | "
                f"{HEX_AXIS_LABELS[top_axis]} ({metrics[top_axis]:.1f}) |"
            )
        lines.append("")

    # Pairwise overlap of top-3 across scenarios
    lines += [
        "### Shortlist diversity",
        "",
        "Pairwise overlap of top-3 vehicle IDs across the five personas (lower overlap → quest segmentation matters).",
        "",
        "| Persona A | Persona B | Shared in top 3 |",
        "|-----------|-----------|-----------------|",
    ]
    for i in range(len(scenarios)):
        for j in range(i + 1, len(scenarios)):
            shared = len(all_tops[i] & all_tops[j])
            a = scenarios[i][0].split("—")[0].strip()
            b = scenarios[j][0].split("—")[0].strip()
            lines.append(f"| {a} | {b} | {shared} |")

    return "\n".join(lines) + "\n"


def priority_flip_section(cars: list[dict]) -> str:
    """Same filters, rotate priority — show rank movement for top car."""
    base = PreferenceState(
        budget=30_000,
        body_types=["any"],
        condition="either",
        stage="compare",
    )
    priorities = ["reliability", "value", "efficiency", "practicality", "safety"]

    lines = [
        "",
        "## Priority axis sensitivity ($30k, any body)",
        "",
        "Overall score for **2023 Honda Civic** when only the stated priority (2× axis weight) changes:",
        "",
        "| Priority (2× weight) | Civic overall | Civic rank (of eligible) |",
        "|----------------------|---------------|---------------------------|",
    ]

    civic_id = "honda-civic-2023"
    for pri in priorities:
        prefs = PreferenceState(
            budget=base.budget,
            body_types=base.body_types,
            condition=base.condition,
            priority=pri,
            stage="compare",
        )
        ranked = rank_cars(cars, prefs, limit=20)
        civic = next((c for c in ranked if c["id"] == civic_id), None)
        if civic:
            rank = ranked.index(civic) + 1
            lines.append(f"| {pri} | {civic['overall']:.2f} | {rank} / {len(ranked)} |")
        else:
            lines.append(f"| {pri} | — | not in ranked set |")

    lines += [
        "",
        "**Takeaway:** Priority chip materially reorders the shortlist without retraining — weights in `PreferenceState.weights()` drive business-visible differentiation.",
        "",
    ]
    return "\n".join(lines)


def budget_funnel_section(cars: list[dict]) -> str:
    lines = [
        "",
        "## Budget funnel (eligible units)",
        "",
        "How fast the lot collapses as budget tightens (before priority scoring):",
        "",
        "| Max budget | Eligible cars |",
        "|------------|-----------------|",
    ]
    for b in (15_000, 20_000, 25_000, 30_000, 35_000, 50_000):
        prefs = PreferenceState(budget=b, body_types=["any"], condition="either", stage="body")
        n = len(filter_catalog(cars, prefs))
        lines.append(f"| {fmt_money(b)} | {n} |")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    cars = load_catalog()
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    body = [
        "# DriveQuest EDA summary",
        "",
        "Exploratory analysis of the **public car catalog fixture** and the **hex scoring engine** "
        "used in the shopper quest. Supports [problem brief](../docs/problem.md) and [shopper funnel](../docs/shopper_funnel.md).",
        "",
        distribution_section(cars),
        budget_funnel_section(cars),
        axis_baseline_section(cars),
        scenario_rankings(cars),
        priority_flip_section(cars),
        "",
        "## Reproduce",
        "",
        "```bash",
        "python scripts/drivequest_eda.py",
        "```",
        "",
    ]

    REPORT_PATH.write_text("\n".join(body), encoding="utf-8")
    print(f"Wrote {REPORT_PATH} ({len(cars)} vehicles)")


if __name__ == "__main__":
    main()