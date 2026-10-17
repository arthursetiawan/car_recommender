"""Parse dealer-group inventory from Excel, CSV, or pasted comma-delimited text.

Ingest is group-level. Rows may include a location_id (rooftop). An optional
default_location / replace_location scopes merges to one rooftop while keeping
the rest of the group lot intact.
"""

from __future__ import annotations

import csv
import io
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from dealers import (
    DEALERS_DIR,
    clear_caches,
    load_group,
    load_inventory,
    location_ids_for,
    resolve_location_id,
)

# Canonical template columns (order matters for the downloadable template)
TEMPLATE_COLUMNS = [
    "stock_number",
    "vin",
    "year",
    "make",
    "model",
    "trim",
    "price",
    "mileage",
    "body_type",
    "fuel_type",
    "condition",
    "color",
    "mpg",
    "safety_rating",
    "reliability",
    "market_value",
    "seats",
    "photo_url",
    "summary",
    "location_id",
    "location_name",
]

COLUMN_ALIASES = {
    "stock_number": {"stock_number", "stock", "stock#", "stock_no", "stock_num", "stock id", "stock_id"},
    "vin": {"vin", "vehicle_identification_number"},
    "year": {"year", "yr", "model_year"},
    "make": {"make", "brand", "manufacturer"},
    "model": {"model"},
    "trim": {"trim", "trim_level", "package"},
    "price": {"price", "asking_price", "list_price", "sale_price"},
    "mileage": {"mileage", "miles", "odometer", "odo"},
    "body_type": {"body_type", "body", "body_style", "type"},
    "fuel_type": {"fuel_type", "fuel", "powertrain", "ev_gas", "energy"},
    "condition": {"condition", "stock_type", "new_used"},
    "color": {"color", "exterior_color", "ext_color"},
    "mpg": {"mpg", "mpge", "efficiency"},
    "safety_rating": {"safety_rating", "safety", "iihs", "nhtsa"},
    "reliability": {"reliability", "reliability_score"},
    "market_value": {"market_value", "market", "fair_value", "mmr"},
    "seats": {"seats", "seating", "passengers"},
    "photo_url": {"photo_url", "photo", "image", "image_url", "photos_url"},
    "summary": {"summary", "notes", "description", "comments"},
    "location_id": {
        "location_id",
        "location",
        "loc",
        "rooftop",
        "rooftop_id",
        "store",
        "store_id",
        "site",
        "site_id",
    },
    "location_name": {"location_name", "store_name", "rooftop_name", "site_name"},
}

REQUIRED = ("year", "make", "model", "price")


def _norm_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _map_headers(headers: list[str]) -> dict[str, int]:
    """Map canonical field -> column index."""
    mapped: dict[str, int] = {}
    for idx, raw in enumerate(headers):
        key = _norm_header(raw).replace("_", " ")
        compact = key.replace(" ", "_")
        for canon, aliases in COLUMN_ALIASES.items():
            if compact in aliases or key in aliases or compact == canon:
                mapped[canon] = idx
                break
    return mapped


def _parse_number(raw: Any) -> float | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text or text.lower() in {"n/a", "na", "-", "none"}:
        return None
    text = text.replace("$", "").replace(",", "").replace("mi", "").replace("miles", "").strip()
    try:
        return float(text)
    except ValueError:
        return None


def _parse_int(raw: Any) -> int | None:
    num = _parse_number(raw)
    if num is None:
        return None
    return int(num)


def _slug(parts: list[str]) -> str:
    joined = "-".join(p for p in parts if p)
    return re.sub(r"[^a-z0-9]+", "-", joined.lower()).strip("-") or "vehicle"


def _resolve_row_location(
    raw_id: str,
    raw_name: str,
    group_id: str,
    default_location: str | None,
    known: set[str],
    name_map: dict[str, str],
) -> tuple[str | None, str | None]:
    """Return (location_id, error_message)."""
    candidate = (raw_id or "").strip()
    if not candidate and raw_name:
        candidate = name_map.get(_norm_header(raw_name), "")
        if not candidate:
            # try slug of name against known ids
            slug = _slug([raw_name])
            if slug in known:
                candidate = slug
    if not candidate and default_location:
        candidate = default_location
    if not candidate:
        return None, None  # group-shared / unscoped row OK
    if known and candidate not in known:
        return None, f"Unknown location_id '{candidate}' for group {group_id}"
    return candidate, None


def _row_to_car(
    values: list[str],
    colmap: dict[str, int],
    row_num: int,
    group_id: str,
    *,
    default_location: str | None = None,
    known_locations: set[str] | None = None,
    location_name_map: dict[str, str] | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    def get(field: str) -> str:
        idx = colmap.get(field)
        if idx is None or idx >= len(values):
            return ""
        return str(values[idx]).strip()

    missing = [f for f in REQUIRED if not get(f)]
    price = _parse_number(get("price"))
    year = _parse_int(get("year"))
    if missing or price is None or year is None:
        return None, {
            "row": row_num,
            "message": "Missing/invalid "
            + ", ".join(missing or (["year"] if year is None else []) + (["price"] if price is None else [])),
        }

    known = known_locations or set()
    name_map = location_name_map or {}
    loc_id, loc_err = _resolve_row_location(
        get("location_id"),
        get("location_name"),
        group_id,
        default_location,
        known,
        name_map,
    )
    if loc_err:
        return None, {"row": row_num, "message": loc_err}

    make = get("make")
    model = get("model")
    stock = get("stock_number") or f"{year}-{make}-{model}"
    car_id = _slug([stock, make, model, str(year)])
    mileage = _parse_number(get("mileage")) or 0
    mpg = _parse_number(get("mpg"))
    safety = _parse_number(get("safety_rating")) or 4.5
    reliability = _parse_number(get("reliability")) or 7.5
    market = _parse_number(get("market_value")) or price
    seats = _parse_int(get("seats")) or 5
    body = (get("body_type") or "sedan").lower()
    fuel = (get("fuel_type") or "gas").lower()
    if fuel in {"ev", "electric vehicle"}:
        fuel = "electric"
    condition = (get("condition") or ("new" if mileage == 0 else "used")).lower()
    photo = get("photo_url")
    where = loc_id or "group lot"
    summary = get("summary") or f"{year} {make} {model} on the {group_id} {where}."

    car = {
        "id": car_id,
        "stock_id": f"{group_id}-{car_id}",
        "stock_number": get("stock_number") or stock,
        "vin": get("vin") or None,
        "make": make,
        "model": model,
        "trim": get("trim") or None,
        "year": year,
        "body_type": body,
        "condition": condition,
        "price": price,
        "mileage": mileage,
        "mpg": mpg if mpg is not None else (110 if fuel == "electric" else 28),
        "safety_rating": safety,
        "reliability": reliability,
        "market_value": market,
        "seats": seats,
        "fuel_type": fuel,
        "color": get("color") or None,
        "summary": summary,
        "image": photo or "/static/cars/toyota-camry-2022.jpg",
        "group_id": group_id,
        "dealer_id": group_id,
        "location_id": loc_id,
    }
    return car, None


def parse_tabular_text(text: str) -> tuple[list[str], list[list[str]]]:
    """Parse CSV or comma/tab-delimited paste into headers + rows."""
    sample = text.strip()
    if not sample:
        return [], []
    try:
        dialect = csv.Sniffer().sniff(sample.splitlines()[0], delimiters=",\t|;")
    except csv.Error:
        dialect = csv.excel
    reader = csv.reader(io.StringIO(sample), dialect)
    rows = [list(r) for r in reader if any(str(c).strip() for c in r)]
    if not rows:
        return [], []
    return [str(h) for h in rows[0]], rows[1:]


def parse_csv_bytes(data: bytes) -> tuple[list[str], list[list[str]]]:
    text = data.decode("utf-8-sig", errors="replace")
    return parse_tabular_text(text)


def parse_excel_bytes(data: bytes) -> tuple[list[str], list[list[str]]]:
    try:
        from openpyxl import load_workbook
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("openpyxl is required for Excel uploads") from exc
    wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    ws = wb.active
    rows: list[list[str]] = []
    for row in ws.iter_rows(values_only=True):
        values = [("" if v is None else str(v)) for v in row]
        if any(v.strip() for v in values):
            rows.append(values)
    if not rows:
        return [], []
    return rows[0], rows[1:]


def rows_to_cars(
    headers: list[str],
    data_rows: list[list[str]],
    group_id: str,
    *,
    default_location: str | None = None,
) -> dict[str, Any]:
    colmap = _map_headers(headers)
    missing_required = [f for f in REQUIRED if f not in colmap]
    if missing_required:
        return {
            "accepted": 0,
            "cars": [],
            "errors": [
                {
                    "row": 1,
                    "message": f"Template missing required columns: {', '.join(missing_required)}",
                }
            ],
            "sample": [],
        }

    known = location_ids_for(group_id)
    if default_location:
        resolve_location_id(group_id, default_location)

    name_map: dict[str, str] = {}
    for loc in load_group(group_id).get("locations") or []:
        name_map[_norm_header(loc["name"])] = loc["id"]
        name_map[_norm_header(loc["id"])] = loc["id"]

    cars: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for i, row in enumerate(data_rows, start=2):
        car, err = _row_to_car(
            row,
            colmap,
            i,
            group_id,
            default_location=default_location,
            known_locations=known,
            location_name_map=name_map,
        )
        if err:
            errors.append(err)
        elif car:
            cars.append(car)
    return {
        "accepted": len(cars),
        "cars": cars,
        "errors": errors,
        "sample": cars[:3],
    }


def _period_paths(group_id: str, period: str | None = None) -> tuple[Path, Path, str]:
    """Return (inventory.json live path, dated snapshot path, period label)."""
    group_dir = DEALERS_DIR / group_id
    live = group_dir / "inventory.json"
    today = date.today().isoformat()
    label = period or today
    safe = re.sub(r"[^0-9A-Za-z_-]+", "-", label)[:32]
    snap_dir = group_dir / "periods"
    snap_dir.mkdir(parents=True, exist_ok=True)
    snap = snap_dir / f"inventory-{safe}.json"
    return live, snap, label


def save_inventory(
    group_id: str,
    cars: list[dict[str, Any]],
    period: str | None = None,
    *,
    replace_location: str | None = None,
) -> dict[str, Any]:
    """Write live inventory. If replace_location is set, merge: keep other rooftops."""
    load_group(group_id)
    if replace_location:
        resolve_location_id(group_id, replace_location)
        # load_inventory cache may be stale mid-write — read file directly via uncached path
        clear_caches()
        existing = [dict(c) for c in load_inventory(group_id)]
        kept = [c for c in existing if c.get("location_id") != replace_location]
        for car in cars:
            car["location_id"] = car.get("location_id") or replace_location
        cars = kept + cars

    live, snap, label = _period_paths(group_id, period)
    payload = {
        "group_id": group_id,
        "dealer_id": group_id,
        "period": label,
        "replace_location": replace_location,
        "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "count": len(cars),
        "cars": cars,
    }
    live.write_text(json.dumps(cars, indent=2) + "\n", encoding="utf-8")
    snap.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    meta = {
        "period": label,
        "updated_at": payload["updated_at"],
        "count": len(cars),
        "replace_location": replace_location,
        "snapshot": str(snap.relative_to(DEALERS_DIR.parent.parent)),
    }
    (DEALERS_DIR / group_id / "inventory.meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    clear_caches()
    return meta


def apply_rows(
    group_id: str,
    headers: list[str],
    rows: list[list[str]],
    period: str | None = None,
    *,
    default_location: str | None = None,
    replace_location: str | None = None,
) -> dict[str, Any]:
    # If caller targets one rooftop without a per-row default, use it as default
    loc = replace_location or default_location
    parsed = rows_to_cars(headers, rows, group_id, default_location=loc)
    meta = None
    if parsed["cars"]:
        # Auto-merge when all accepted rows share one location and a replace_location was given,
        # or when replace_location is explicitly set.
        merge_loc = replace_location
        if not merge_loc and loc:
            locs = {c.get("location_id") for c in parsed["cars"]}
            if locs == {loc}:
                merge_loc = loc
        meta = save_inventory(group_id, parsed["cars"], period=period, replace_location=merge_loc)
    return {
        "accepted": parsed["accepted"],
        "errors": parsed["errors"],
        "sample": parsed["sample"],
        "period_label": (meta or {}).get("period") or period or date.today().isoformat(),
        "meta": meta,
        "group_id": group_id,
        "dealer_id": group_id,
        "location_id": replace_location or default_location,
    }


def apply_paste_inventory(
    group_id: str,
    text: str,
    period: str | None = None,
    *,
    default_location: str | None = None,
    replace_location: str | None = None,
) -> dict[str, Any]:
    headers, rows = parse_tabular_text(text)
    if not headers:
        return {
            "accepted": 0,
            "errors": [{"row": 0, "message": "No tabular data found. Paste CSV with a header row."}],
            "sample": [],
            "period_label": period or date.today().isoformat(),
            "meta": None,
            "group_id": group_id,
            "dealer_id": group_id,
            "location_id": replace_location or default_location,
        }
    return apply_rows(
        group_id,
        headers,
        rows,
        period=period,
        default_location=default_location,
        replace_location=replace_location,
    )


def apply_upload(
    group_id: str,
    filename: str,
    data: bytes,
    period: str | None = None,
    *,
    default_location: str | None = None,
    replace_location: str | None = None,
) -> dict[str, Any]:
    name = filename.lower()
    empty = {
        "accepted": 0,
        "errors": [],
        "sample": [],
        "period_label": period or date.today().isoformat(),
        "meta": None,
        "group_id": group_id,
        "dealer_id": group_id,
        "location_id": replace_location or default_location,
    }
    if name.endswith((".xlsx", ".xlsm", ".xltx", ".xls")):
        if name.endswith(".xls") and not name.endswith(".xlsx"):
            empty["errors"] = [
                {
                    "row": 0,
                    "message": "Legacy .xls not supported — save as .xlsx or CSV and re-upload.",
                }
            ]
            return empty
        headers, rows = parse_excel_bytes(data)
    elif name.endswith(".csv") or name.endswith(".txt"):
        headers, rows = parse_csv_bytes(data)
    else:
        empty["errors"] = [{"row": 0, "message": "Unsupported file type. Use .xlsx or .csv"}]
        return empty
    return apply_rows(
        group_id,
        headers,
        rows,
        period=period,
        default_location=default_location,
        replace_location=replace_location,
    )


def template_csv_text() -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(TEMPLATE_COLUMNS)
    writer.writerow(
        [
            "NS-1001",
            "1HGCV1F30JA000001",
            "2022",
            "Toyota",
            "Camry",
            "SE",
            "24500",
            "32000",
            "sedan",
            "hybrid",
            "used",
            "Silver",
            "32",
            "5.0",
            "9.2",
            "25000",
            "5",
            "",
            "Reliable midsize hybrid sedan",
            "downtown",
            "Northstar Downtown",
        ]
    )
    writer.writerow(
        [
            "NS-2002",
            "5YJ3E1EA1KF000002",
            "2021",
            "Tesla",
            "Model 3",
            "Standard Range",
            "24900",
            "38000",
            "sedan",
            "electric",
            "used",
            "White",
            "120",
            "5.0",
            "7.0",
            "25500",
            "5",
            "",
            "Efficient EV sedan",
            "westside",
            "Northstar Westside",
        ]
    )
    return buf.getvalue()


def write_template_files(target_dir: Path) -> dict[str, Path]:
    """Write CSV + XLSX templates into target_dir; return paths."""
    target_dir.mkdir(parents=True, exist_ok=True)
    csv_path = target_dir / "drivequest-dealer-inventory-template.csv"
    csv_path.write_text(template_csv_text(), encoding="utf-8")

    xlsx_path = target_dir / "drivequest-dealer-inventory-template.xlsx"
    try:
        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        ws.title = "Inventory"
        reader = csv.reader(io.StringIO(template_csv_text()))
        for r_idx, row in enumerate(reader, start=1):
            for c_idx, value in enumerate(row, start=1):
                ws.cell(row=r_idx, column=c_idx, value=value)
        # Second sheet: column legend
        legend = wb.create_sheet("Columns")
        legend.append(["column", "required", "notes"])
        legend_rows = [
            ("stock_number", "recommended", "Dealer stock #"),
            ("vin", "optional", "17-char VIN"),
            ("year", "yes", "Model year"),
            ("make", "yes", "e.g. Toyota"),
            ("model", "yes", "e.g. Camry"),
            ("trim", "optional", "SE, LT, etc."),
            ("price", "yes", "Asking price"),
            ("mileage", "optional", "Odometer; 0 for new"),
            ("body_type", "optional", "sedan, suv, hatchback, truck, wagon"),
            ("fuel_type", "optional", "gas, hybrid, electric"),
            ("condition", "optional", "new / used"),
            ("color", "optional", "Exterior color"),
            ("mpg", "optional", "MPG or MPGe"),
            ("safety_rating", "optional", "0–5"),
            ("reliability", "optional", "0–10"),
            ("market_value", "optional", "For value hex axis"),
            ("seats", "optional", "Defaults to 5"),
            ("photo_url", "optional", "Image URL"),
            ("summary", "optional", "Short honest blurb"),
            ("location_id", "recommended for multi-rooftop", "Rooftop slug within the dealer group"),
            ("location_name", "optional", "Human label; mapped to location_id when id omitted"),
        ]
        for row in legend_rows:
            legend.append(list(row))
        wb.save(xlsx_path)
    except ImportError:
        xlsx_path = csv_path
    return {"csv": csv_path, "xlsx": xlsx_path}
