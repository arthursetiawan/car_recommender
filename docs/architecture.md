# Architecture (POC)

High-level map of DriveQuest as shipped in this proof of concept. Prefer this over reading every module when onboarding.

## Stack

| Layer | POC choice |
|-------|------------|
| API | FastAPI (`backend/app.py`) |
| Advisor | LangChain + ChatOpenAI **or** rule-based demo (`backend/agent.py`) |
| Scoring | Hex axes in `recommendation_engine.py` |
| Inventory | JSON files under `data/dealers/<group_id>/` |
| Ingest | `inventory_ingest.py` (CSV / openpyxl Excel / paste) |
| UI | Static HTML/JS (`frontend/`) served at `/static`, embeds inject bootstrap |
| Legacy | SQLAlchemy `Car` + scrapers still in repo; conversational path uses dealer JSON |

## Tenancy model

```
DealerGroup
  ├── group.json          # branding, persona, api_key, locations[]
  ├── inventory.json      # live lot (list of cars)
  └── periods/            # optional snapshots after ingest
        inventory-<label>.json

Location (optional)       # rooftop within the group
  └── id used as filter on inventory.location_id
```

- **Primary tenant = group** (shared inventory file, group admin, default branding/persona).
- **Location** is a filter for embeds and for “merge replace this rooftop only” on ingest.
- Each car carries `group_id` (alias `dealer_id`) and optional `location_id`.
- API accepts `group_id` / `group`; `dealer_id` / `dealer` remain aliases for backward compatibility.

Registry: `data/dealers/index.json` lists groups (`groups` + legacy `dealers` keys).

Code: `backend/dealers.py` (`load_group`, `load_inventory(group, location?)`, `public_group_config`).

## Request flow (shopper)

1. Browser loads `/embed/{group}` or `/embed/{group}/{location}` (or widget injects iframe).
2. Bootstrap sets `window.__DQ_GROUP__`, optional `__DQ_LOCATION__`.
3. UI `POST /api/session` with `group_id` + optional `location_id`.
4. Chat / chip choices → `/api/chat`, `/api/choice` — session bound to that tenant.
5. Ranking uses `list_cars(group_id, location_id)` only (latest live inventory).
6. ROI uses same scope for sample pairs and car lookups.

## Advisor

- **With `OPENAI_API_KEY`:** LangChain tools (update prefs, rank, best pick, EV tradeoffs, ROI, reset).
- **Without:** demo advisor walks the same stages and tools deterministically.
- System prompt + group `persona_note` enforce honest, inventory-only recommendations.
- Tabular paste in chat can trigger inventory ingest (POC convenience for dealers/admins).

## Hex radar

Six axes (0–10-ish scores derived from catalog fields):

1. Value (price vs `market_value`)
2. Budget fit
3. Reliability
4. Efficiency (MPG / EV-ish)
5. Safety
6. Practicality (body, seats, wear)

UI draws polygons for top contenders (`frontend/app.js`).

## EV / ROI

- Knowledge blurbs: `ev_tradeoffs.py` → `GET /api/ev-tradeoffs`
- Break-even math: `roi_calculator.py` → `POST /api/roi` (car ids or manual prices)
- Defaults / sample pairs from current scoped inventory: `GET /api/roi/defaults`

Assumptions (gas $/gal, kWh rate, miles/year, charger, incentive) are **demo knobs**, not live utility rates.

## Inventory ingest path

```
Excel/CSV/paste
    → parse headers (aliases OK)
    → row → car dict (flag errors)
    → write inventory.json
    → optional periods/snapshot
    → clear caches
```

- Group-wide upload with mixed `location_id` → **replace** full live list.
- Upload/paste with `location_id` target → **merge**: replace that rooftop’s cars, keep others.

Details: [dealer-admin.md](./dealer-admin.md), [dealer-inventory-template.md](./dealer-inventory-template.md).

## Key routes (cheat sheet)

| Path | Role |
|------|------|
| `GET /` | Landing + sample groups |
| `GET /embed/{group}` · `/{group}/{location}` | Shopper UI |
| `GET /widget.js?group=&location=` | Drop-in iframe injector |
| `GET /static/admin.html?group=` | Inventory admin |
| `GET/POST /api/groups…` | Config + ingest (aliases `/api/dealers…`) |
| `POST /api/session` · `/api/chat` · `/api/choice` | Quest |
| `GET /api/catalog` · `/api/roi*` · `/api/ev-tradeoffs` | Data helpers |
| `GET /health` | Liveness + feature flags |

## Data layout (repo)

```
data/
  dealers/
    index.json
    northstar-motors/
      group.json          # also mirrored dealer.json
      inventory.json
    lakeside-ev/
      …
  templates/
    drivequest-dealer-inventory-template.csv
    drivequest-dealer-inventory-template.xlsx
  car_catalog.json        # legacy global catalog (fallback / older paths)
```

## Design stance (POC)

- File-backed inventory beats a real DB for demos.
- In-memory sessions (restart clears chats).
- API keys optional in demo; if sent, must match `group.json`.
- Branding is CSS variables from group config (copper/teal samples — not purple default AI chrome).
