"""Tests for hexagonal scoring and progressive filtering."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from catalog import list_cars
from recommendation_engine import (
    HEX_AXES,
    PreferenceState,
    apply_choice,
    enrich_car,
    rank_cars,
    score_car,
)


def test_hex_axes_are_six():
    assert len(HEX_AXES) == 6


def test_score_car_returns_all_axes():
    car = list_cars()[0]
    metrics = score_car(car, budget=30000)
    assert set(metrics) == set(HEX_AXES)
    for v in metrics.values():
        assert 0 <= v <= 10


def test_rank_respects_budget():
    prefs = PreferenceState(budget=20000, stage="compare", condition="either", body_types=["any"])
    ranked = rank_cars(list_cars(), prefs, limit=10)
    assert ranked
    assert all(c["price"] <= 20000 * 1.05 for c in ranked)


def test_apply_choice_advances_stages():
    prefs = PreferenceState()
    prefs = apply_choice(prefs, "budget", 25000)
    assert prefs.budget == 25000
    assert prefs.stage == "body"
    prefs = apply_choice(prefs, "body", "sedan")
    assert prefs.body_types == ["sedan"]
    assert prefs.stage == "priority"


def test_enrich_includes_hex_arrays():
    car = enrich_car(list_cars()[0], budget=40000)
    assert len(car["hex_values"]) == 6
    assert len(car["hex_labels"]) == 6
