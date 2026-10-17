"""Group-scoped inventory access (multi-tenant), with optional location filter.

Falls back to the legacy global `data/car_catalog.json` only when no group
registry exists — normal path is per-group JSON under data/dealers/.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from dealers import default_group_id, load_inventory

ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = ROOT / "data" / "car_catalog.json"


@lru_cache(maxsize=1)
def load_catalog() -> tuple[dict[str, Any], ...]:
    """Legacy global catalog (kept for tests / fallback)."""
    with CATALOG_PATH.open(encoding="utf-8") as fh:
        cars = json.load(fh)
    return tuple(cars)


def list_cars(
    group_id: str | None = None,
    location_id: str | None = None,
    *,
    dealer_id: str | None = None,
) -> list[dict[str, Any]]:
    gid = group_id or dealer_id or default_group_id()
    return [dict(c) for c in load_inventory(gid, location_id)]


def get_car(
    car_id: str,
    group_id: str | None = None,
    location_id: str | None = None,
    *,
    dealer_id: str | None = None,
) -> dict[str, Any] | None:
    gid = group_id or dealer_id or default_group_id()
    for car in load_inventory(gid, location_id):
        if car["id"] == car_id or car.get("stock_id") == car_id:
            return dict(car)
    return None
