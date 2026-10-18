# Dealer inventory input template

Use this template for **daily/weekly lot updates** at the **dealer group** level. Rows may target a **location** (rooftop). The plugin writes live `inventory.json` so recommendations, chat, hex quest, and EV ROI only see the new stock for that group (and location filter, when the embed is scoped).

Ops UI walkthrough: [dealer-admin.md](./dealer-admin.md). Plugin context: [dealer-plugin.md](./dealer-plugin.md).

## Downloadable files (in repo)

| Format | Path |
|--------|------|
| CSV | `data/templates/drivequest-dealer-inventory-template.csv` |
| Excel | `data/templates/drivequest-dealer-inventory-template.xlsx` |

Also served at runtime:

- `GET /api/templates/inventory.csv`
- `GET /api/templates/inventory.xlsx`

Excel workbook includes an **Inventory** sheet (sample rows) and a **Columns** legend sheet.

## Columns

| Column | Required | Notes |
|--------|----------|--------|
| `stock_number` | recommended | Dealer stock # |
| `vin` | optional | 17-char VIN when available (not decoded in POC) |
| `year` | **yes** | Model year |
| `make` | **yes** | e.g. Toyota |
| `model` | **yes** | e.g. Camry |
| `trim` | optional | SE, LT, etc. |
| `price` | **yes** | Asking price (numbers; `$` and commas OK) |
| `mileage` | optional | Odometer; `0` for new |
| `body_type` | optional | sedan, suv, hatchback, truck, wagon |
| `fuel_type` | optional | gas, hybrid, electric (aliases: ev) |
| `condition` | optional | new / used (defaults from mileage) |
| `color` | optional | Exterior color |
| `mpg` | optional | MPG or MPGe |
| `safety_rating` | optional | 0–5 scale (defaults if blank) |
| `reliability` | optional | 0–10 score (defaults if blank) |
| `market_value` | optional | For “value” hex axis; defaults to price |
| `seats` | optional | Defaults to 5 |
| `photo_url` | optional | Absolute or site-relative image URL |
| `summary` | optional | Short honest blurb |
| `location_id` | **recommended for multi-rooftop** | Rooftop slug within the group (`downtown`, `westside`, …) |
| `location_name` | optional | Human label; mapped to `location_id` when id omitted |

Header aliases are accepted (e.g. `stock#`, `miles`, `body`, `fuel`, `image_url`, `rooftop`, `store`, `site`).

### Group vs location columns

| Situation | What to put in the sheet | Admin “Location id” |
|-----------|--------------------------|---------------------|
| Multi-rooftop weekly dump | Fill `location_id` per row | Leave empty → **full replace** |
| One rooftop’s daily update | Column optional | Set to that rooftop → **merge replace** |
| Group-shared / unscoped unit | Leave `location_id` blank | Empty |

Unknown `location_id` values are **flagged** (must match `group.json` → `locations[].id`).

## Excel path

1. Download the `.xlsx` template.
2. Fill one row per vehicle for this day/week; set `location_id` per rooftop when applicable.
3. In **Admin** (`/static/admin.html?group=YOUR_GROUP`) choose the file → **Upload inventory**.
4. Optional period label: `2026-10-17` or `week-42` (stored under `data/dealers/<group>/periods/`).
5. Optional location field: merge only that rooftop.

API:

```bash
# Group-wide replace
curl -X POST "http://localhost:8000/api/groups/northstar-motors/inventory/upload" \
  -H "X-API-Key: dq_demo_northstar" \
  -F "file=@lot.xlsx" \
  -F "period=week-42"

# Rooftop merge
curl -X POST "http://localhost:8000/api/groups/northstar-motors/inventory/upload" \
  -H "X-API-Key: dq_demo_northstar" \
  -F "file=@downtown-lot.xlsx" \
  -F "period=week-42" \
  -F "location_id=downtown"
```

Legacy `.xls` is **not** supported — save as `.xlsx` or CSV.

## Chat / paste path

Paste CSV text (header + rows) into:

- Admin paste box → **Parse & replace inventory**, or
- The advisor chat (demo mode detects tabular pastes with `stock`/`make`/`year` headers)

### Group paste (mixed rooftops)

```text
stock_number,year,make,model,price,mileage,body_type,fuel_type,condition,location_id
NS-2001,2021,Honda,Civic,21900,24000,sedan,gas,used,downtown
NS-2002,2022,Toyota,RAV4,26800,31000,suv,hybrid,used,westside
```

### Location paste (admin location = downtown, or column omitted)

```text
stock_number,year,make,model,price,mileage,body_type,fuel_type,condition
DT-101,2020,Honda,Fit,12900,41000,hatchback,gas,used
DT-102,2022,Toyota,Corolla,19900,18000,sedan,gas,used
```

### Minimal viable paste

```text
year,make,model,price
2021,Honda,Civic,21900
2022,Toyota,Camry,24500
```

The system replies with how many rows were accepted, a sample of parsed cars (with location when present), and **flagged bad rows** (missing year/make/model/price, unknown `location_id`, etc.).

## After ingest

Live file `data/dealers/<group_id>/inventory.json` is updated. Caches clear automatically.

| Embed | What shoppers see |
|-------|-------------------|
| `/embed/{group}` | Full live lot |
| `/embed/{group}/{location}` | Rows with that `location_id` (+ untagged group-shared rows in POC) |

## Template maintenance

Templates are regenerated on app startup via `write_template_files()` into `data/templates/`. Source of column order: `TEMPLATE_COLUMNS` in `backend/inventory_ingest.py`.
