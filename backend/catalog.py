"""Load the curated car catalog (enriched from scrapers + hand-tuned metrics)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = ROOT / "data" / "car_catalog.json"


@lru_cache(maxsize=1)
def load_catalog() -> tuple[dict[str, Any], ...]:
    with CATALOG_PATH.open(encoding="utf-8") as fh:
        cars = json.load(fh)
    return tuple(cars)


def get_car(car_id: str) -> dict[str, Any] | None:
    for car in load_catalog():
        if car["id"] == car_id:
            return dict(car)
    return None


def list_cars() -> list[dict[str, Any]]:
    return [dict(c) for c in load_catalog()]
