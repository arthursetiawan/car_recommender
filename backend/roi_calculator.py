"""EV vs gas break-even / time-to-ROI calculator."""

from __future__ import annotations

from typing import Any

from ev_tradeoffs import DEFAULT_ASSUMPTIONS


def _annual_fuel_cost_gas(miles: float, mpg: float, gas_price: float) -> float:
    if mpg <= 0:
        return 0.0
    return (miles / mpg) * gas_price


def _annual_energy_cost_ev(miles: float, kwh_per_100: float, rate: float) -> float:
    return (miles / 100.0) * kwh_per_100 * rate


def calculate_ev_roi(
    ev_price: float,
    gas_price: float,
    *,
    incentive: float = 0.0,
    home_charger_cost: float | None = None,
    miles_per_year: float | None = None,
    gas_mpg: float | None = None,
    gas_price_per_gallon: float | None = None,
    ev_kwh_per_100mi: float | None = None,
    electricity_rate_per_kwh: float | None = None,
    annual_maintenance_delta: float | None = None,
    # Positive delta means EV costs MORE per year; negative = EV saves
    years_horizon: int = 8,
) -> dict[str, Any]:
    """Estimate years/months to break even buying EV vs a comparable gas car.

    Net upfront EV premium = (ev_price - incentive + charger) - gas_price
    Annual EV advantage = fuel savings - maintenance_delta
      (maintenance_delta is EV_cost - gas_cost; default negative = EV cheaper)
    """
    a = DEFAULT_ASSUMPTIONS
    miles = float(miles_per_year if miles_per_year is not None else a["miles_per_year"])
    mpg = float(gas_mpg if gas_mpg is not None else a["gas_mpg"])
    gal_price = float(gas_price_per_gallon if gas_price_per_gallon is not None else a["gas_price_per_gallon"])
    kwh100 = float(ev_kwh_per_100mi if ev_kwh_per_100mi is not None else a["ev_kwh_per_100mi"])
    rate = float(
        electricity_rate_per_kwh if electricity_rate_per_kwh is not None else a["electricity_rate_per_kwh"]
    )
    maint_delta = float(
        annual_maintenance_delta
        if annual_maintenance_delta is not None
        else a["ev_maintenance_delta_per_year"]
    )
    charger = float(home_charger_cost if home_charger_cost is not None else a["home_charger_cost"])
    incentive = float(incentive or 0.0)

    ev_effective_price = ev_price - incentive + charger
    gas_effective_price = gas_price
    upfront_premium = ev_effective_price - gas_effective_price

    annual_gas_fuel = _annual_fuel_cost_gas(miles, mpg, gal_price)
    annual_ev_energy = _annual_energy_cost_ev(miles, kwh100, rate)
    annual_fuel_savings = annual_gas_fuel - annual_ev_energy
    # maint_delta: EV - gas (negative => EV cheaper => savings = -delta)
    annual_maint_savings = -maint_delta
    annual_total_savings = annual_fuel_savings + annual_maint_savings

    if annual_total_savings <= 0:
        years_to_roi = None
        months_to_roi = None
        never_breaks_even = True
    elif upfront_premium <= 0:
        years_to_roi = 0.0
        months_to_roi = 0.0
        never_breaks_even = False
    else:
        years_to_roi = upfront_premium / annual_total_savings
        months_to_roi = years_to_roi * 12.0
        never_breaks_even = False

    cumulative = []
    running = -upfront_premium
    for y in range(1, years_horizon + 1):
        running += annual_total_savings
        cumulative.append({"year": y, "net_vs_gas": round(running, 2)})

    verdict = _verdict(upfront_premium, years_to_roi, never_breaks_even, annual_total_savings)

    return {
        "inputs": {
            "ev_price": ev_price,
            "gas_price": gas_price,
            "incentive": incentive,
            "home_charger_cost": charger,
            "miles_per_year": miles,
            "gas_mpg": mpg,
            "gas_price_per_gallon": gal_price,
            "ev_kwh_per_100mi": kwh100,
            "electricity_rate_per_kwh": rate,
            "annual_maintenance_delta": maint_delta,
            "years_horizon": years_horizon,
        },
        "ev_effective_price": round(ev_effective_price, 2),
        "gas_effective_price": round(gas_effective_price, 2),
        "upfront_premium": round(upfront_premium, 2),
        "annual_gas_fuel_cost": round(annual_gas_fuel, 2),
        "annual_ev_energy_cost": round(annual_ev_energy, 2),
        "annual_fuel_savings": round(annual_fuel_savings, 2),
        "annual_maintenance_savings": round(annual_maint_savings, 2),
        "annual_total_savings": round(annual_total_savings, 2),
        "years_to_roi": None if years_to_roi is None else round(years_to_roi, 2),
        "months_to_roi": None if months_to_roi is None else round(months_to_roi, 1),
        "never_breaks_even": never_breaks_even,
        "cumulative": cumulative,
        "savings_at_5_years": next((c["net_vs_gas"] for c in cumulative if c["year"] == 5), None),
        "verdict": verdict,
    }


def _verdict(
    premium: float,
    years: float | None,
    never: bool,
    annual_savings: float,
) -> str:
    if premium <= 0 and annual_savings > 0:
        return (
            f"EV wins from day one (effective price at or below gas) and saves "
            f"~${annual_savings:,.0f}/yr on energy + maintenance."
        )
    if never:
        return (
            "At these inputs the EV never breaks even on operating savings alone — "
            "revisit incentives, electricity rate, or miles/year."
        )
    assert years is not None
    if years <= 3:
        tone = "Strong EV value case"
    elif years <= 5:
        tone = "Reasonable EV payback"
    elif years <= 8:
        tone = "Longer EV payback — still workable if you value charging convenience / emissions"
    else:
        tone = "Slow payback — gas/hybrid may be the better pure-money play"
    return f"{tone}: ~{years:.1f} years ({years * 12:.0f} months) to recover the ${premium:,.0f} EV premium."


def roi_from_cars(
    ev_car: dict[str, Any],
    gas_car: dict[str, Any],
    *,
    incentive: float | None = None,
    miles_per_year: float | None = None,
    gas_price_per_gallon: float | None = None,
    electricity_rate_per_kwh: float | None = None,
    home_charger_cost: float | None = None,
) -> dict[str, Any]:
    """Convenience wrapper using catalog cars."""
    a = DEFAULT_ASSUMPTIONS
    kwh = float(ev_car.get("kwh_per_100mi") or a["ev_kwh_per_100mi"])
    mpg = float(gas_car.get("mpg") or a["gas_mpg"])
    # Used EVs often get smaller credit; new may get federal — caller can override
    if incentive is None:
        incentive = a["federal_ev_credit"] if ev_car.get("condition") == "new" else 0.0
    result = calculate_ev_roi(
        float(ev_car["price"]),
        float(gas_car["price"]),
        incentive=incentive,
        home_charger_cost=home_charger_cost,
        miles_per_year=miles_per_year,
        gas_mpg=mpg,
        gas_price_per_gallon=gas_price_per_gallon,
        ev_kwh_per_100mi=kwh,
        electricity_rate_per_kwh=electricity_rate_per_kwh,
    )
    result["ev_car"] = {
        "id": ev_car.get("id"),
        "label": f"{ev_car.get('year')} {ev_car.get('make')} {ev_car.get('model')}",
        "image": ev_car.get("image"),
    }
    result["gas_car"] = {
        "id": gas_car.get("id"),
        "label": f"{gas_car.get('year')} {gas_car.get('make')} {gas_car.get('model')}",
        "image": gas_car.get("image"),
    }
    return result
