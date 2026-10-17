"""Multi-tenant dealer groups + location-scoped inventory ingest tests."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from catalog import get_car, list_cars
from dealers import (
    clear_caches,
    list_group_summaries,
    load_group,
    public_group_config,
)
from inventory_ingest import (
    apply_paste_inventory,
    parse_tabular_text,
    rows_to_cars,
    template_csv_text,
)


def test_two_sample_groups():
    ids = {g["id"] for g in list_group_summaries()}
    assert "northstar-motors" in ids
    assert "lakeside-ev" in ids


def test_groups_have_locations():
    ns = load_group("northstar-motors")
    loc_ids = {loc["id"] for loc in ns["locations"]}
    assert loc_ids == {"downtown", "westside"}
    lake = load_group("lakeside-ev")
    assert {loc["id"] for loc in lake["locations"]} == {"harbor", "lakefront"}


def test_inventories_are_isolated_by_group():
    clear_caches()
    north = {c["id"] for c in list_cars("northstar-motors")}
    lake = {c["id"] for c in list_cars("lakeside-ev")}
    assert "toyota-corolla-2023" in north
    assert "tesla-model3-2021" in lake
    assert "tesla-model3-2021" not in north


def test_location_filters_rooftop_lot():
    clear_caches()
    downtown = list_cars("northstar-motors", "downtown")
    westside = list_cars("northstar-motors", "westside")
    assert downtown and westside
    assert all(c.get("location_id") == "downtown" for c in downtown)
    assert all(c.get("location_id") == "westside" for c in westside)
    assert {c["id"] for c in downtown}.isdisjoint({c["id"] for c in westside})
    # Group-wide is the union
    all_cars = list_cars("northstar-motors")
    assert len(all_cars) == len(downtown) + len(westside)


def test_public_config_hides_api_key_and_exposes_locations():
    cfg = public_group_config("northstar-motors")
    assert "api_key" not in cfg
    assert cfg["inventory_count"] > 0
    assert cfg["scope"] == "group"
    assert len(cfg["locations"]) == 2
    loc_cfg = public_group_config("northstar-motors", "downtown")
    assert loc_cfg["scope"] == "location"
    assert loc_cfg["location_id"] == "downtown"
    assert loc_cfg["inventory_count"] < cfg["inventory_count"]


def test_template_includes_location_columns():
    header = template_csv_text().splitlines()[0]
    assert "location_id" in header
    assert "location_name" in header


def test_parse_and_flag_bad_rows():
    text = template_csv_text() + "BAD,row,only\n"
    headers, rows = parse_tabular_text(text)
    parsed = rows_to_cars(headers, rows, "northstar-motors")
    assert parsed["accepted"] >= 2
    assert parsed["errors"]
    # Sample rows carry location from template
    assert any(c.get("location_id") for c in parsed["cars"])


def test_unknown_location_flagged():
    paste = """stock_number,year,make,model,price,location_id
X-1,2020,Honda,Fit,12900,not-a-real-lot
"""
    headers, rows = parse_tabular_text(paste)
    parsed = rows_to_cars(headers, rows, "northstar-motors")
    assert parsed["accepted"] == 0
    assert parsed["errors"]


def test_paste_updates_live_inventory_group_wide():
    inv_path = Path(__file__).resolve().parents[1] / "data/dealers/northstar-motors/inventory.json"
    backup = inv_path.read_text(encoding="utf-8")
    try:
        clear_caches()
        paste = """stock_number,year,make,model,price,mileage,body_type,fuel_type,condition,location_id
TST-1,2020,Honda,Fit,12900,41000,hatchback,gas,used,downtown
TST-2,2022,Toyota,Corolla,19900,18000,sedan,gas,used,westside
"""
        result = apply_paste_inventory("northstar-motors", paste, period="test-period")
        assert result["accepted"] == 2
        clear_caches()
        cars = list_cars("northstar-motors")
        assert len(cars) == 2
        assert {c["location_id"] for c in cars} == {"downtown", "westside"}
    finally:
        inv_path.write_text(backup, encoding="utf-8")
        clear_caches()
        assert json.loads(backup)


def test_location_merge_keeps_other_rooftop():
    inv_path = Path(__file__).resolve().parents[1] / "data/dealers/northstar-motors/inventory.json"
    backup = inv_path.read_text(encoding="utf-8")
    try:
        clear_caches()
        before_west = {c["id"] for c in list_cars("northstar-motors", "westside")}
        assert before_west
        paste = """stock_number,year,make,model,price,mileage,body_type,fuel_type,condition
DT-ONLY,2021,Honda,Civic,21000,20000,sedan,gas,used
"""
        result = apply_paste_inventory(
            "northstar-motors",
            paste,
            period="test-loc-merge",
            default_location="downtown",
            replace_location="downtown",
        )
        assert result["accepted"] == 1
        clear_caches()
        downtown = list_cars("northstar-motors", "downtown")
        westside = list_cars("northstar-motors", "westside")
        assert len(downtown) == 1
        assert downtown[0]["model"] == "Civic"
        assert {c["id"] for c in westside} == before_west
    finally:
        inv_path.write_text(backup, encoding="utf-8")
        clear_caches()


def test_roi_car_still_resolves_on_lakeside():
    car = get_car("tesla-model3-2021", "lakeside-ev")
    assert car is not None
    assert car.get("group_id") == "lakeside-ev"
