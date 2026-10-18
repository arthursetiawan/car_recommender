# Dealer admin — inventory updates (POC)

How a dealer group keeps the lot current for the day/week. Shopper quest, hex, chat, and ROI all read **only the latest live inventory** after a successful ingest.

## Admin UI

- Static page: `/static/admin.html?group=northstar-motors`
- Optional rooftop: `&location=downtown` (merge mode target)
- Convenience route: `/admin/{group_id}`

Fields:

| Field | Use |
|-------|-----|
| Group id | Tenant slug |
| Location id | Optional — default/merge rooftop |
| API key | Optional in demo; if set, must match `group.json` |
| Period label | e.g. `2026-10-17` or `week-42` (snapshot filename) |

Actions:

1. **Upload** `.xlsx` / `.csv` (legacy `.xls` rejected — save as xlsx/csv).
2. **Paste** comma/tab-delimited text with a header row → **Parse & replace**.
3. Download **CSV** / **Excel** templates from the same page (or `/api/templates/…`).

Result panel: accepted count, period, location scope, flagged bad rows.

## Mental model: group vs location

| Mode | How | Effect on live lot |
|------|-----|--------------------|
| **Group-wide** | Leave location empty; rows may include `location_id` | **Replace** entire `inventory.json` |
| **Rooftop merge** | Set location (admin/API); rows inherit if column missing | **Replace that location’s cars**; keep other rooftops |

Full column specs + paste samples: [dealer-inventory-template.md](./dealer-inventory-template.md).

## API (same behavior as UI)

```bash
# Group replace
curl -X POST "http://localhost:8000/api/groups/northstar-motors/inventory/upload" \
  -H "X-API-Key: dq_demo_northstar" \
  -F "file=@lot.xlsx" \
  -F "period=week-42"

# Rooftop merge
curl -X POST "http://localhost:8000/api/groups/northstar-motors/inventory/upload" \
  -H "X-API-Key: dq_demo_northstar" \
  -F "file=@downtown.csv" \
  -F "period=day-shift" \
  -F "location_id=downtown"

# Paste JSON body
curl -X POST "http://localhost:8000/api/groups/northstar-motors/inventory/paste" \
  -H "Content-Type: application/json" \
  -d '{"text":"stock_number,year,make,model,price,location_id\nNS-1,2021,Honda,Civic,21900,downtown","period":"week-42"}'
```

Aliases: `/api/dealers/{id}/inventory/…` still work.

## Chat paste (POC shortcut)

In the advisor chat, a message that looks like CSV (header with stock/make/year/price + comma/tab rows) is treated as an inventory update. The bot replies with accepted count, sample rows, and **flagged bad rows**. In a location-scoped session, paste defaults/merges to that location.

This is intentional for demos — not a production ACL story.

## After a good ingest

- `data/dealers/<group>/inventory.json` updated
- Snapshot under `periods/inventory-<period>.json` when a period label is set
- Caches cleared — embeds immediately rank the new lot
- Preview links on admin open group or location embeds

## Bad rows

Common flags:

- Missing/invalid `year`, `make`, `model`, `price`
- Unknown `location_id` for that group
- Missing required header columns entirely
- Legacy `.xls` upload

Accepted rows still load; bad rows are listed, not silently dropped without notice.

## Branding / persona (group config)

Not edited in the admin UI in this POC — edit `data/dealers/<group>/group.json`:

- `name`, `tagline`, `branding` colors, `persona_note`, `api_key`, `locations[]`

Redeploy/restart not always required for JSON inventory; group config is cached — restart uvicorn if branding edits don’t show.
