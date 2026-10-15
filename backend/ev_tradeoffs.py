"""EV vs gas tradeoff knowledge encoded for DriveQuest advice + scoring.

Covers charging, fuel/energy cost, maintenance, incentives, range/cold weather,
and resale — used by the chat agent and optional preference weighting.
"""

from __future__ import annotations

from typing import Any

# Structured tradeoff knowledge the agent (and demo mode) can cite.
EV_TRADEOFFS: dict[str, dict[str, Any]] = {
    "charging": {
        "title": "Charging",
        "ev_upside": "Home Level-2 charging is convenient overnight; workplace/public DC fast charge covers trips.",
        "ev_downside": "Apartment dwellers and road-trippers may face charger hunt / wait time.",
        "gas_upside": "5-minute fill-ups nearly everywhere.",
        "gas_downside": "Must visit stations; price swings at the pump.",
        "tip": "If you can plug in at home most nights, EV ownership friction drops sharply.",
    },
    "fuel_cost": {
        "title": "Fuel / energy cost",
        "ev_upside": "Electricity usually costs less per mile than gasoline (often 40–70% cheaper).",
        "ev_downside": "Public DC fast charging can erase much of the savings.",
        "gas_upside": "Predictable if you already budget for fuel.",
        "gas_downside": "Gas prices are volatile; hybrids soften but don't remove fuel cost.",
        "tip": "Home off-peak rates make EV cost/mile strongest. Use the ROI calculator for your miles/year.",
    },
    "maintenance": {
        "title": "Maintenance",
        "ev_upside": "No oil changes, fewer brake jobs (regen), simpler drivetrain → typically lower routine maintenance.",
        "ev_downside": "Tire wear can be higher; battery out of warranty is a rare but costly risk.",
        "gas_upside": "Huge independent repair network; parts often cheaper.",
        "gas_downside": "Oil, spark plugs, exhaust, transmission service add up over years.",
        "tip": "Budget ~$300–600/yr less maintenance for many EVs vs comparable gas cars (varies by model).",
    },
    "incentives": {
        "title": "Incentives / tax credits",
        "ev_upside": "Federal new-EV credit (up to ~$7,500 when eligible), plus some state/utility rebates; used EVs may qualify for a smaller credit.",
        "ev_downside": "Income, MSRP, assembly, and battery-sourcing rules can block eligibility.",
        "gas_upside": "No paperwork or eligibility cliffs.",
        "gas_downside": "No purchase incentive to offset higher lifetime fuel spend.",
        "tip": "Apply incentives as an upfront price reduction in the ROI calculator.",
    },
    "range_cold": {
        "title": "Range & cold weather",
        "ev_upside": "Most modern EVs cover daily commuting easily (200+ mi rated).",
        "ev_downside": "Cold weather and highway speed can cut range ~20–40%; cabin heat uses battery.",
        "gas_upside": "Range barely affected by cold; heat is 'free' from the engine.",
        "gas_downside": "Still burns more fuel in winter with shorter trips / warm-up.",
        "tip": "If winters are harsh or you road-trip weekly, size EV range generously or keep gas/hybrid as backup.",
    },
    "resale": {
        "title": "Resale / depreciation",
        "ev_upside": "Strong demand for efficient used EVs in high-gas / high-incentive markets.",
        "ev_downside": "Battery tech and new-model launches can accelerate EV depreciation; used prices volatile.",
        "gas_upside": "Toyota/Honda gas & hybrids historically hold value well.",
        "gas_downside": "Gas-guzzlers suffer more when fuel prices spike.",
        "tip": "Reliability brands + remaining battery warranty matter more than badge alone for used EVs.",
    },
}

DEFAULT_ASSUMPTIONS = {
    "gas_price_per_gallon": 3.60,
    "electricity_rate_per_kwh": 0.16,
    "miles_per_year": 12000,
    "ev_kwh_per_100mi": 30.0,
    "gas_mpg": 30.0,
    "ev_maintenance_delta_per_year": -400.0,  # EV costs less
    "home_charger_cost": 800.0,
    "federal_ev_credit": 7500.0,
    "cold_range_penalty_pct": 0.25,
}


def fuel_category(car: dict[str, Any]) -> str:
    fuel = (car.get("fuel_type") or "gas").lower()
    if fuel in ("electric", "ev"):
        return "electric"
    if fuel == "hybrid":
        return "hybrid"
    return "gas"


def enrich_powertrain_fields(car: dict[str, Any]) -> dict[str, Any]:
    """Attach default EV/gas operating assumptions used by ROI + advice."""
    out = dict(car)
    cat = fuel_category(car)
    out["powertrain"] = cat
    if cat == "electric":
        out.setdefault("kwh_per_100mi", 28.0 if "bolt" in car.get("id", "") else 30.0)
        out.setdefault("range_miles", 250 if "model3" in car.get("id", "") else 220)
        out.setdefault("cold_range_miles", int(out["range_miles"] * (1 - DEFAULT_ASSUMPTIONS["cold_range_penalty_pct"])))
        out.setdefault("home_charging_friendly", True)
    elif cat == "hybrid":
        out.setdefault("kwh_per_100mi", None)
        out.setdefault("range_miles", 500)
        out.setdefault("cold_range_miles", 480)
    else:
        out.setdefault("kwh_per_100mi", None)
        mpg = float(car.get("mpg") or 28)
        tank = 14.0
        out.setdefault("range_miles", int(mpg * tank))
        out.setdefault("cold_range_miles", int(out["range_miles"] * 0.95))
    return out


def summarize_tradeoffs(topics: list[str] | None = None) -> dict[str, Any]:
    keys = topics or list(EV_TRADEOFFS.keys())
    sections = []
    for key in keys:
        if key not in EV_TRADEOFFS:
            continue
        t = EV_TRADEOFFS[key]
        sections.append(
            {
                "id": key,
                "title": t["title"],
                "ev_upside": t["ev_upside"],
                "ev_downside": t["ev_downside"],
                "gas_upside": t["gas_upside"],
                "gas_downside": t["gas_downside"],
                "tip": t["tip"],
            }
        )
    return {"topics": sections, "assumptions": DEFAULT_ASSUMPTIONS}


def advise_ev_vs_gas(prefs: dict[str, Any] | None = None, context: str | None = None) -> str:
    """Short advisory blurb tailored to light preference hints."""
    prefs = prefs or {}
    ctx = (context or "").lower()
    miles = prefs.get("miles_per_year") or DEFAULT_ASSUMPTIONS["miles_per_year"]
    lines = [
        "EV vs gas quick take:",
        f"- At ~{int(miles):,} mi/yr, electricity usually beats gasoline on cost/mile if you charge at home.",
        "- EVs typically save on maintenance; gas wins on fill-up speed and cold-weather range certainty.",
        "- Incentives can erase much of an EV sticker premium — plug numbers into the ROI calculator.",
    ]
    if any(w in ctx for w in ("apartment", "condo", "no charger", "street park")):
        lines.append("- Without reliable home charging, lean gas/hybrid unless workplace charging is solid.")
    if any(w in ctx for w in ("cold", "winter", "alaska", "midwest")):
        lines.append("- Plan on ~20–40% less EV range in deep cold; oversize battery or keep a hybrid option.")
    if any(w in ctx for w in ("road trip", "highway", "long distance")):
        lines.append("- Frequent long highway trips favor gas/hybrid unless you're OK with DC fast-charge stops.")
    if any(w in ctx for w in ("tax", "credit", "incentive", "rebate")):
        lines.append("- Confirm federal/state eligibility before counting the full credit in break-even math.")
    return "\n".join(lines)


def powertrain_score_adjustments(car: dict[str, Any], prefs: dict[str, Any] | None = None) -> dict[str, float]:
    """Small hex-axis nudges reflecting EV/gas tradeoffs given preferences."""
    prefs = prefs or {}
    cat = fuel_category(car)
    adj = {k: 0.0 for k in ("value", "budget_fit", "reliability", "efficiency", "safety", "practicality")}
    priority = (prefs.get("priority") or "").lower()
    wants_ev = prefs.get("prefer_ev") is True or "electric" in (prefs.get("fuel_types") or [])
    wants_gas = prefs.get("prefer_ev") is False or (
        prefs.get("fuel_types") == ["gas"]
    )

    if cat == "electric":
        adj["efficiency"] += 1.2
        adj["value"] += 0.4  # lower energy cost
        adj["practicality"] -= 0.6  # charging / range friction
        if wants_ev:
            adj["value"] += 0.5
            adj["practicality"] += 0.4
        if wants_gas:
            adj["practicality"] -= 0.8
        if priority == "efficiency":
            adj["efficiency"] += 0.5
    elif cat == "hybrid":
        adj["efficiency"] += 0.7
        adj["practicality"] += 0.3
        adj["value"] += 0.3
    else:
        adj["practicality"] += 0.5
        if wants_ev:
            adj["efficiency"] -= 0.8
            adj["value"] -= 0.3
        if priority == "efficiency":
            adj["efficiency"] -= 0.4

    return adj
