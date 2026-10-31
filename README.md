# DriveQuest — Conversational Car Recommender

[![License: MIT](https://img.shields.io/badge/License-MIT-0f6e63.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](./requirements.txt)
[![FastAPI](https://img.shields.io/badge/FastAPI-uvicorn-009688)](./backend/app.py)
[![Docs](https://img.shields.io/badge/docs-POC%20suite-c47a22)](./docs/README.md)

LangChain-powered car advisor that turns shopping into a progressive quest. You chat (or tap choice chips) to narrow budget, body type, priorities, and new/used — then compare contenders on a **hexagonal radar** across six axes:

1. **Value** — deal quality vs market  
2. **Budget fit** — how well price sits under your max  
3. **Reliability**  
4. **Efficiency** — fuel / energy  
5. **Safety**  
6. **Practicality** — space, body style, wear  

Built on FastAPI + SQLAlchemy + scrapers. Dealer groups can embed a location-scoped advisor; the legacy `/recommendations/` endpoint remains.

> **Personal site** (recruiter-facing full-stack automotive data scientist portfolio) lives in [`portfolio/`](./portfolio/). After merge: enable GitHub Pages via the included workflow, **or** copy `portfolio/` contents into [`arthursetiawan.github.io`](https://github.com/arthursetiawan/arthursetiawan.github.io). Optional profile README draft: [`PROFILE_README.md`](./PROFILE_README.md).

## Documentation (POC)

Full proof-of-concept docs — overview, architecture, shopper UX, dealer admin/ingest, embed install, runbook, and limitations — live in **[`docs/`](./docs/README.md)**. Start with [`docs/poc-overview.md`](./docs/poc-overview.md).

Dealer group embeds use `?group=` (optional `&location=`). Sample tenants: `northstar-motors`, `lakeside-ev`.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

Open [http://localhost:8000](http://localhost:8000).

### Demo mode (no API key)

If `OPENAI_API_KEY` is unset, the app runs a deterministic **demo advisor** that still drives the same stages, catalog scoring, and hex chart. Full LangChain + OpenAI tool-calling activates when the key is present:

```bash
export OPENAI_API_KEY=sk-...
export OPENAI_MODEL=gpt-4o-mini   # optional
uvicorn backend.app:app --reload --port 8000
```

## API

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/session` | Start a quest session |
| `POST` | `/api/chat` | `{ "message", "session_id?" }` |
| `POST` | `/api/choice` | `{ "session_id?", "stage", "value" }` chip pick |
| `GET`  | `/api/catalog` | Scored catalog (with images + powertrain fields) |
| `GET`  | `/api/ev-tradeoffs` | EV vs gas tradeoff knowledge |
| `GET`  | `/api/roi/defaults` | Default ROI assumptions + sample pairs |
| `POST` | `/api/roi` | Break-even calculator (car ids or custom prices) |
| `GET`  | `/recommendations/?budget=` | Legacy filter (DB or catalog fallback) |
| `GET`  | `/health` | Liveness |

### Try the ROI calculator

1. Open the app and scroll to **EV vs gas ROI**.
2. Pick a pair (e.g. Model 3 vs Camry), set miles/year and incentive, click **Calculate break-even**.
3. Or chat: `EV vs gas ROI for Model 3 vs Camry at 12000 miles/year` / click **Ask EV vs gas**.

## Project layout

```
backend/
  app.py                   # FastAPI + static UI
  agent.py                 # LangChain agent + demo fallback
  recommendation_engine.py # Hex scoring + game stages
  catalog.py               # Curated inventory loader
  dealers.py               # Multi-tenant dealer groups
  inventory_ingest.py      # CSV/Excel ingest
  models.py                # SQLAlchemy Car model
  scraper*/                # Existing site scrapers
frontend/                  # DriveQuest chat + radar UI
portfolio/                 # Personal portfolio (GitHub Pages)
data/car_catalog.json      # Seed inventory
docs/                      # POC documentation suite
```

## Scrapers

Existing Cars.com / CarGurus / Autotrader scrapers are unchanged. Catalog rows can be refreshed from scraped CSVs; `data/car_catalog.json` is the live source for the conversational advisor.

## Docker

```bash
docker build -t drivequest .
docker run -p 8000:8000 -e OPENAI_API_KEY=$OPENAI_API_KEY drivequest
```

## License

MIT — see [`LICENSE`](./LICENSE).
