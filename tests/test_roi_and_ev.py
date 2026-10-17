"""Tests for EV tradeoffs encoding and ROI calculator."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from catalog import get_car
from ev_tradeoffs import advise_ev_vs_gas, powertrain_score_adjustments, summarize_tradeoffs
from recommendation_engine import PreferenceState, enrich_car, score_car
from roi_calculator import calculate_ev_roi, roi_from_cars


def test_tradeoff_topics_cover_six_areas():
    data = summarize_tradeoffs()
    ids = {t["id"] for t in data["topics"]}
    assert ids >= {"charging", "fuel_cost", "maintenance", "incentives", "range_cold", "resale"}


def test_roi_breaks_even_with_incentive():
    result = calculate_ev_roi(
        ev_price=35000,
        gas_price=28000,
        incentive=7500,
        home_charger_cost=800,
        miles_per_year=15000,
        gas_mpg=28,
        gas_price_per_gallon=3.8,
        ev_kwh_per_100mi=28,
        electricity_rate_per_kwh=0.14,
        annual_maintenance_delta=-400,
    )
    assert result["annual_total_savings"] > 0
    assert result["years_to_roi"] is not None
    assert result["years_to_roi"] < 10
    assert "verdict" in result


def test_roi_from_catalog_cars():
    ev = get_car("tesla-model3-2021", "lakeside-ev")
    gas = get_car("toyota-camry-2022", "lakeside-ev")
    result = roi_from_cars(ev, gas, incentive=0, miles_per_year=12000)
    assert result["ev_car"]["id"] == "tesla-model3-2021"
    assert result["gas_car"]["id"] == "toyota-camry-2022"
    assert "years_to_roi" in result


def test_ev_score_boost_when_prefer_ev():
    bolt = get_car("chevrolet-bolt-2022", "lakeside-ev")
    camry = get_car("toyota-camry-2022", "lakeside-ev")
    prefs = {"prefer_ev": True, "priority": "efficiency"}
    bolt_m = score_car(bolt, budget=30000, prefs=prefs)
    camry_m = score_car(camry, budget=30000, prefs=prefs)
    assert bolt_m["efficiency"] >= camry_m["efficiency"]


def test_powertrain_adjustments_gas_lean():
    bolt = get_car("chevrolet-bolt-2022", "lakeside-ev")
    adj = powertrain_score_adjustments(bolt, {"prefer_ev": False})
    assert adj["practicality"] < 0


def test_advise_mentions_charging_context():
    text = advise_ev_vs_gas({}, "I live in an apartment with no charger")
    assert "charging" in text.lower() or "charger" in text.lower()


def test_enrich_includes_image_and_powertrain():
    car = enrich_car(get_car("tesla-model3-2021", "lakeside-ev"), budget=30000)
    assert car.get("image")
    assert car.get("powertrain") == "electric"
    assert car.get("range_miles")
