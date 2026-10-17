"""Multi-tenant dealer groups with optional rooftop locations.

Primary tenant = DealerGroup. Locations are optional scopes within a group
(for storefront embeds and “at this location” chat). Inventory is stored at
group level; each vehicle is tagged with group_id + optional location_id.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEALERS_DIR = ROOT / "data" / "dealers"
INDEX_PATH = DEALERS_DIR / "index.json"

# Alias for callers that still say “dealer”
GROUPS_DIR = DEALERS_DIR


class DealerNotFound(KeyError):
    """Unknown group (or legacy dealer) id."""


class LocationNotFound(KeyError):
    """Unknown location id within a group."""


@lru_cache(maxsize=1)
def _index() -> dict[str, Any]:
    with INDEX_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def clear_caches() -> None:
    _index.cache_clear()
    load_group.cache_clear()
    load_inventory.cache_clear()


def _group_entries() -> list[dict[str, Any]]:
    data = _index()
    return list(data.get("groups") or data.get("dealers") or [])


def list_group_summaries() -> list[dict[str, str]]:
    return [{"id": g["id"], "name": g["name"]} for g in _group_entries()]


def list_dealer_summaries() -> list[dict[str, str]]:
    """Backward-compatible alias — dealers are groups."""
    return list_group_summaries()


def default_group_id() -> str:
    data = _index()
    return data.get("default_group") or data.get("default_dealer") or list_group_summaries()[0]["id"]


def default_dealer_id() -> str:
    return default_group_id()


def _group_dir(group_id: str) -> Path:
    for entry in _group_entries():
        if entry["id"] == group_id:
            return DEALERS_DIR / entry["path"]
    raise DealerNotFound(group_id)


def _read_group_config(group_id: str) -> dict[str, Any]:
    group_dir = _group_dir(group_id)
    for name in ("group.json", "dealer.json"):
        path = group_dir / name
        if path.exists():
            with path.open(encoding="utf-8") as fh:
                return json.load(fh)
    raise DealerNotFound(group_id)


@lru_cache(maxsize=32)
def load_group(group_id: str) -> dict[str, Any]:
    cfg = _read_group_config(group_id)
    cfg = dict(cfg)
    cfg["id"] = group_id
    cfg["group_id"] = group_id
    # Normalize locations
    locations = []
    for loc in cfg.get("locations") or []:
        locations.append(
            {
                "id": loc["id"],
                "name": loc.get("name") or loc["id"],
                "city": loc.get("city"),
                "address": loc.get("address"),
                "tagline": loc.get("tagline"),
            }
        )
    cfg["locations"] = locations
    return cfg


def load_dealer(dealer_id: str) -> dict[str, Any]:
    """Alias: a dealer id is a group id."""
    return load_group(dealer_id)


def get_location(group_id: str, location_id: str | None) -> dict[str, Any] | None:
    if not location_id:
        return None
    cfg = load_group(group_id)
    for loc in cfg.get("locations") or []:
        if loc["id"] == location_id:
            return loc
    raise LocationNotFound(f"{group_id}/{location_id}")


def resolve_location_id(group_id: str, location_id: str | None) -> str | None:
    if not location_id:
        return None
    get_location(group_id, location_id)  # validate
    return location_id


@lru_cache(maxsize=64)
def load_inventory(group_id: str, location_id: str | None = None) -> tuple[dict[str, Any], ...]:
    """Load group inventory, optionally filtered to one rooftop."""
    cfg = load_group(group_id)
    if location_id:
        resolve_location_id(group_id, location_id)
    inv_name = cfg.get("inventory") or "inventory.json"
    path = _group_dir(group_id) / inv_name
    with path.open(encoding="utf-8") as fh:
        cars = json.load(fh)
    out = []
    for car in cars:
        item = dict(car)
        item["group_id"] = group_id
        item["dealer_id"] = group_id  # alias
        loc = item.get("location_id")
        if location_id and loc and loc != location_id:
            continue
        if location_id and not loc:
            # Untagged rows are group-shared; include them in location scope
            item["location_id"] = location_id
        out.append(item)
    return tuple(out)


def public_group_config(group_id: str, location_id: str | None = None) -> dict[str, Any]:
    """Safe config for embed UI (no API key)."""
    cfg = load_group(group_id)
    loc = get_location(group_id, location_id) if location_id else None
    cars = load_inventory(group_id, location_id)
    name = cfg.get("name")
    tagline = cfg.get("tagline")
    if loc:
        name = loc.get("name") or name
        tagline = loc.get("tagline") or tagline
    return {
        "id": cfg["id"],
        "group_id": cfg["id"],
        "dealer_id": cfg["id"],  # alias
        "name": name,
        "group_name": cfg.get("name"),
        "tagline": tagline,
        "branding": cfg.get("branding") or {},
        "locations": cfg.get("locations") or [],
        "location_id": location_id,
        "location": loc,
        "inventory_count": len(cars),
        "scope": "location" if location_id else "group",
    }


def public_dealer_config(dealer_id: str, location_id: str | None = None) -> dict[str, Any]:
    return public_group_config(dealer_id, location_id)


def resolve_group(
    group_id: str | None = None,
    api_key: str | None = None,
    *,
    dealer_id: str | None = None,
) -> str:
    """Resolve group from slug and optional API key. dealer_id is an alias."""
    gid = group_id or dealer_id
    if gid:
        cfg = load_group(gid)
        if api_key and cfg.get("api_key") and api_key != cfg["api_key"]:
            raise PermissionError("Invalid API key for dealer group")
        return gid
    if api_key:
        for summary in list_group_summaries():
            cfg = load_group(summary["id"])
            if cfg.get("api_key") == api_key:
                return summary["id"]
        raise PermissionError("Unknown API key")
    return default_group_id()


def resolve_dealer(dealer_id: str | None = None, api_key: str | None = None) -> str:
    return resolve_group(dealer_id=dealer_id, api_key=api_key)


def authenticate_group(group_id: str, api_key: str | None) -> bool:
    """API key is optional in demo mode; if provided it must match."""
    cfg = load_group(group_id)
    expected = cfg.get("api_key")
    if not api_key:
        return True
    return bool(expected) and api_key == expected


def authenticate_dealer(dealer_id: str, api_key: str | None) -> bool:
    return authenticate_group(dealer_id, api_key)


def location_ids_for(group_id: str) -> set[str]:
    return {loc["id"] for loc in load_group(group_id).get("locations") or []}
