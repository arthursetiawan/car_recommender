"""Score and rank cars on six hexagonal axes for radar comparison."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Six axes for the hexagonal / radar chart
HEX_AXES = (
    "value",
    "budget_fit",
    "reliability",
    "efficiency",
    "safety",
    "practicality",
)

HEX_AXIS_LABELS = {
    "value": "Value",
    "budget_fit": "Budget Fit",
    "reliability": "Reliability",
    "efficiency": "Efficiency",
    "safety": "Safety",
    "practicality": "Practicality",
}


def _clamp(score: float, lo: float = 0.0, hi: float = 10.0) -> float:
    return max(lo, min(hi, score))


def score_value(car: dict[str, Any]) -> float:
    """Deal quality: asking price vs estimated market value."""
    market = float(car.get("market_value") or car["price"])
    price = float(car["price"])
    if market <= 0:
        return 5.0
    ratio = market / price
    # 1.0 = fair, >1 = under market (good), <1 = overpaying
    return _clamp(5.0 + (ratio - 1.0) * 25.0)


def score_budget_fit(car: dict[str, Any], budget: float | None) -> float:
    """How comfortably the car sits under the user's budget."""
    if not budget or budget <= 0:
        return 5.0
    price = float(car["price"])
    if price > budget:
        over = (price - budget) / budget
        return _clamp(5.0 - over * 20.0)
    headroom = (budget - price) / budget
    # Sweet spot: ~10–25% under budget
    if 0.05 <= headroom <= 0.30:
        return _clamp(8.5 + (0.175 - abs(headroom - 0.175)) * 8)
    if headroom < 0.05:
        return 7.5
    return _clamp(8.0 - (headroom - 0.30) * 10)


def score_reliability(car: dict[str, Any]) -> float:
    return _clamp(float(car.get("reliability", 7.0)))


def score_efficiency(car: dict[str, Any]) -> float:
    mpg = float(car.get("mpg") or 25)
    fuel = (car.get("fuel_type") or "gas").lower()
    if fuel == "electric":
        # Treat MPGe-like numbers generously but cap
        return _clamp(mpg / 12.0)
    if fuel == "hybrid":
        return _clamp(mpg / 4.0)
    return _clamp(mpg / 3.8)


def score_safety(car: dict[str, Any]) -> float:
    rating = float(car.get("safety_rating") or 4.0)
    return _clamp(rating * 2.0)


def score_practicality(car: dict[str, Any]) -> float:
    seats = int(car.get("seats") or 5)
    body = (car.get("body_type") or "").lower()
    mileage = float(car.get("mileage") or 0)
    base = 5.0
    if seats >= 7:
        base += 2.5
    elif seats >= 5:
        base += 1.5
    body_bonus = {
        "suv": 1.5,
        "wagon": 1.5,
        "truck": 1.2,
        "hatchback": 0.8,
        "sedan": 0.5,
    }.get(body, 0.5)
    # High mileage softens practicality (more wear)
    mileage_penalty = min(2.0, mileage / 80000.0)
    return _clamp(base + body_bonus - mileage_penalty)


def score_car(car: dict[str, Any], budget: float | None = None) -> dict[str, float]:
    return {
        "value": round(score_value(car), 2),
        "budget_fit": round(score_budget_fit(car, budget), 2),
        "reliability": round(score_reliability(car), 2),
        "efficiency": round(score_efficiency(car), 2),
        "safety": round(score_safety(car), 2),
        "practicality": round(score_practicality(car), 2),
    }


def overall_score(metrics: dict[str, float], weights: dict[str, float] | None = None) -> float:
    weights = weights or {axis: 1.0 for axis in HEX_AXES}
    total_w = sum(weights.get(a, 1.0) for a in HEX_AXES) or 1.0
    return round(sum(metrics[a] * weights.get(a, 1.0) for a in HEX_AXES) / total_w, 2)


def enrich_car(car: dict[str, Any], budget: float | None = None, weights: dict[str, float] | None = None) -> dict[str, Any]:
    metrics = score_car(car, budget)
    return {
        **car,
        "metrics": metrics,
        "overall": overall_score(metrics, weights),
        "hex_labels": [HEX_AXIS_LABELS[a] for a in HEX_AXES],
        "hex_values": [metrics[a] for a in HEX_AXES],
    }


@dataclass
class PreferenceState:
    """Progressive filters collected through the game-like conversation."""

    budget: float | None = None
    body_types: list[str] = field(default_factory=list)
    condition: str | None = None  # new | used | either
    fuel_types: list[str] = field(default_factory=list)
    priority: str | None = None  # reliability | value | efficiency | practicality | safety
    min_year: int | None = None
    max_mileage: int | None = None
    eliminated_ids: list[str] = field(default_factory=list)
    shortlist_ids: list[str] = field(default_factory=list)
    stage: str = "budget"  # budget → body → priority → condition → compare → decide

    def weights(self) -> dict[str, float]:
        w = {axis: 1.0 for axis in HEX_AXES}
        boost = {
            "reliability": "reliability",
            "value": "value",
            "efficiency": "efficiency",
            "practicality": "practicality",
            "safety": "safety",
            "budget": "budget_fit",
        }.get(self.priority or "")
        if boost:
            w[boost] = 2.0
        return w

    def to_dict(self) -> dict[str, Any]:
        return {
            "budget": self.budget,
            "body_types": self.body_types,
            "condition": self.condition,
            "fuel_types": self.fuel_types,
            "priority": self.priority,
            "min_year": self.min_year,
            "max_mileage": self.max_mileage,
            "eliminated_ids": self.eliminated_ids,
            "shortlist_ids": self.shortlist_ids,
            "stage": self.stage,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "PreferenceState":
        if not data:
            return cls()
        return cls(
            budget=data.get("budget"),
            body_types=list(data.get("body_types") or []),
            condition=data.get("condition"),
            fuel_types=list(data.get("fuel_types") or []),
            priority=data.get("priority"),
            min_year=data.get("min_year"),
            max_mileage=data.get("max_mileage"),
            eliminated_ids=list(data.get("eliminated_ids") or []),
            shortlist_ids=list(data.get("shortlist_ids") or []),
            stage=data.get("stage") or "budget",
        )


STAGE_ORDER = ["budget", "body", "priority", "condition", "compare", "decide"]

STAGE_PROMPTS = {
    "budget": {
        "prompt": "What's your max budget for the car?",
        "choices": [
            {"id": "budget_15k", "label": "Under $15k", "value": 15000},
            {"id": "budget_25k", "label": "Around $25k", "value": 25000},
            {"id": "budget_35k", "label": "Around $35k", "value": 35000},
            {"id": "budget_50k", "label": "Up to $50k", "value": 50000},
        ],
    },
    "body": {
        "prompt": "What kind of vehicle fits your life?",
        "choices": [
            {"id": "body_sedan", "label": "Sedan", "value": "sedan"},
            {"id": "body_suv", "label": "SUV / Crossover", "value": "suv"},
            {"id": "body_hatch", "label": "Hatchback", "value": "hatchback"},
            {"id": "body_truck", "label": "Truck", "value": "truck"},
            {"id": "body_wagon", "label": "Wagon", "value": "wagon"},
            {"id": "body_any", "label": "Surprise me", "value": "any"},
        ],
    },
    "priority": {
        "prompt": "Which tradeoff matters most right now?",
        "choices": [
            {"id": "pri_reliability", "label": "Reliability", "value": "reliability"},
            {"id": "pri_value", "label": "Best value / deal", "value": "value"},
            {"id": "pri_efficiency", "label": "Fuel / energy efficiency", "value": "efficiency"},
            {"id": "pri_practicality", "label": "Space & practicality", "value": "practicality"},
            {"id": "pri_safety", "label": "Safety", "value": "safety"},
        ],
    },
    "condition": {
        "prompt": "New, used, or either?",
        "choices": [
            {"id": "cond_used", "label": "Used (more value)", "value": "used"},
            {"id": "cond_new", "label": "New", "value": "new"},
            {"id": "cond_either", "label": "Either works", "value": "either"},
        ],
    },
    "compare": {
        "prompt": "Here are your contenders — eliminate one or shortlist favorites.",
        "choices": [],
    },
    "decide": {
        "prompt": "Ready for the best pick, or keep comparing?",
        "choices": [
            {"id": "decide_best", "label": "Crown the best pick", "value": "best"},
            {"id": "decide_reset", "label": "Start over", "value": "reset"},
        ],
    },
}


def filter_catalog(cars: list[dict[str, Any]], prefs: PreferenceState) -> list[dict[str, Any]]:
    results = []
    for car in cars:
        if car["id"] in prefs.eliminated_ids:
            continue
        if prefs.budget is not None and float(car["price"]) > prefs.budget * 1.05:
            continue
        if prefs.body_types and "any" not in prefs.body_types:
            if car.get("body_type") not in prefs.body_types:
                continue
        if prefs.condition and prefs.condition != "either":
            if car.get("condition") != prefs.condition:
                continue
        if prefs.fuel_types and car.get("fuel_type") not in prefs.fuel_types:
            continue
        if prefs.min_year and int(car.get("year") or 0) < prefs.min_year:
            continue
        if prefs.max_mileage is not None and float(car.get("mileage") or 0) > prefs.max_mileage:
            continue
        results.append(car)
    return results


def rank_cars(
    cars: list[dict[str, Any]],
    prefs: PreferenceState,
    limit: int = 5,
) -> list[dict[str, Any]]:
    filtered = filter_catalog(cars, prefs)
    weights = prefs.weights()
    enriched = [enrich_car(c, prefs.budget, weights) for c in filtered]
    if prefs.shortlist_ids:
        shortlisted = [c for c in enriched if c["id"] in prefs.shortlist_ids]
        if shortlisted:
            enriched = shortlisted
    enriched.sort(key=lambda c: c["overall"], reverse=True)
    return enriched[:limit]


def apply_choice(prefs: PreferenceState, stage: str, choice_value: Any) -> PreferenceState:
    """Advance game state from a UI choice chip."""
    if stage == "budget":
        prefs.budget = float(choice_value)
        prefs.stage = "body"
    elif stage == "body":
        if choice_value == "any":
            prefs.body_types = ["any"]
        else:
            prefs.body_types = [str(choice_value)]
        prefs.stage = "priority"
    elif stage == "priority":
        prefs.priority = str(choice_value)
        prefs.stage = "condition"
    elif stage == "condition":
        prefs.condition = str(choice_value)
        prefs.stage = "compare"
    elif stage == "compare":
        # choice_value may be eliminate:<id> or shortlist:<id>
        val = str(choice_value)
        if val.startswith("eliminate:"):
            cid = val.split(":", 1)[1]
            if cid not in prefs.eliminated_ids:
                prefs.eliminated_ids.append(cid)
        elif val.startswith("shortlist:"):
            cid = val.split(":", 1)[1]
            if cid not in prefs.shortlist_ids:
                prefs.shortlist_ids.append(cid)
        prefs.stage = "decide" if prefs.shortlist_ids or len(prefs.eliminated_ids) >= 1 else "compare"
    elif stage == "decide":
        if choice_value == "reset":
            return PreferenceState()
        prefs.stage = "decide"
    return prefs


def next_stage_payload(prefs: PreferenceState, contenders: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    stage = prefs.stage
    meta = dict(STAGE_PROMPTS.get(stage, STAGE_PROMPTS["budget"]))
    if stage == "compare" and contenders:
        choices = []
        for car in contenders[:4]:
            label = f"{car['year']} {car['make']} {car['model']}"
            choices.append(
                {
                    "id": f"elim_{car['id']}",
                    "label": f"Eliminate {label}",
                    "value": f"eliminate:{car['id']}",
                }
            )
            choices.append(
                {
                    "id": f"short_{car['id']}",
                    "label": f"Shortlist {label}",
                    "value": f"shortlist:{car['id']}",
                }
            )
        choices.append({"id": "compare_done", "label": "I've narrowed enough →", "value": "done"})
        meta["choices"] = choices
    return {
        "stage": stage,
        "prompt": meta["prompt"],
        "choices": meta["choices"],
        "prefs": prefs.to_dict(),
    }
