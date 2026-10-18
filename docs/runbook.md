# Runbook (POC)

How to run DriveQuest locally, flip demo vs live advisor, and smoke-test the multi-tenant flows.

## Prerequisites

- Python 3.10+ recommended
- `pip` / venv
- Optional: `OPENAI_API_KEY` for LangChain live mode
- Ports: `8000` free (or set `PORT`)

## Install & run

```bash
cd car_recommender   # repo root
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000/

Docker (if you use the shipped Dockerfile):

```bash
docker build -t drivequest .
docker run -p 8000:8000 -e OPENAI_API_KEY=$OPENAI_API_KEY drivequest
```

## Environment

| Variable | Required? | Effect |
|----------|-----------|--------|
| `OPENAI_API_KEY` | No | If unset → **demo advisor**; if set → LangChain + tools |
| `OPENAI_MODEL` | No | Default `gpt-4o-mini` |
| `PORT` | No | When running `python -m backend.app` style entry |

`.env` via `python-dotenv` may be loaded depending on process; exporting in the shell is the reliable POC path.

### Demo mode

No key needed. Same quest stages, hex scoring, ROI math, inventory ingest. UI badge: “Demo advisor · works without an API key”.

### Live mode

```bash
export OPENAI_API_KEY=sk-...
export OPENAI_MODEL=gpt-4o-mini
uvicorn backend.app:app --reload --port 8000
```

## Sanity checks

```bash
curl -s http://127.0.0.1:8000/health | python3 -m json.tool
# expect ok, groups northstar-motors + lakeside-ev, features list

curl -s 'http://127.0.0.1:8000/api/groups/northstar-motors?location=downtown' | python3 -m json.tool
# scope=location, inventory_count < group-wide

curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8000/embed/northstar-motors/downtown
# 200

curl -s http://127.0.0.1:8000/api/templates/inventory.csv | head -1
# header includes location_id
```

### Manual UI path

1. `/` → Northstar **Group widget** → chip budget → see hex.
2. `/embed/northstar-motors/downtown` → fewer cars than group.
3. `/static/admin.html?group=northstar-motors` → paste 2 CSV rows → accept → refresh embed.
4. Lakeside embed → ROI panel / Ask EV vs gas.

## Tests

```bash
cd repo root
PYTHONPATH=backend python3 -m pytest tests/test_dealers_and_ingest.py tests/test_roi_and_ev.py -q
```

Dealer tests cover group isolation, location filter, template columns, paste replace, rooftop merge. They restore `inventory.json` after mutating — if a test is killed mid-run, restore from git.

## Common issues

| Symptom | Likely fix |
|---------|------------|
| Port in use | `pkill -f "uvicorn backend.app"` or another port |
| Branding/config stale | Restart uvicorn (lru caches) |
| Excel upload fails on `.xls` | Re-save as `.xlsx` or CSV |
| Empty lot after bad paste | Re-upload known-good file; check `data/dealers/<id>/inventory.json` |
| ROI “unknown car” | Car id not in **scoped** inventory (wrong location) |
| OpenAI errors | Unset key to fall back to demo, or fix billing/model |

## Useful paths

| Path | Purpose |
|------|---------|
| `backend/app.py` | Routes |
| `backend/dealers.py` | Tenancy |
| `backend/inventory_ingest.py` | Parse/save |
| `backend/agent.py` | Chat / demo / LangChain |
| `data/dealers/` | Sample tenants |
| `data/templates/` | Downloadable templates |
| `frontend/` | UI |

## Docs index

[README.md](./README.md)
