# DriveQuest dealer group plugin

DriveQuest embeds on dealer websites as a **multi-tenant plugin**. Primary tenancy is the **dealer group** (shared inventory, branding, persona defaults, and admin). An optional **location** (rooftop) scopes the shopper experience to one store’s lot.

This is the **specified** plugin guide. For vision/scope see [poc-overview.md](./poc-overview.md); for install snippets see [embed-install.md](./embed-install.md); for ingest UI see [dealer-admin.md](./dealer-admin.md).

## Architecture (at a glance)

```
DealerGroup  →  one or more Location(s)
inventory rows tagged with group_id + optional location_id
```

| Layer | Path / key |
|-------|------------|
| Tenant (group) | slug e.g. `northstar-motors`, `lakeside-ev` |
| Config | `data/dealers/<group_id>/group.json` (locations, branding, persona, API key) |
| Inventory | `data/dealers/<group_id>/inventory.json` (latest) + `periods/` snapshots |
| Embed (group) | `/embed/{group}` or `/widget.js?group=…` |
| Embed (location) | `/embed/{group}/{location}` or `/widget.js?group=…&location=…` |
| Admin | `/static/admin.html?group=…` (+ optional `&location=…`) |

Quest chat, hex comparison, and EV ROI call APIs with `group_id` (alias: `dealer_id`) and optional `location_id`, and read only that scope’s **latest loaded** inventory.

Legacy query/path aliases `dealer` / `dealer_id` still resolve to the group.

Deeper diagram: [architecture.md](./architecture.md).

## One-line install

**Group-wide** (all rooftops):

```html
<script src="https://YOUR_HOST/widget.js?group=northstar-motors" async></script>
```

**Single location** (this store’s site):

```html
<script src="https://YOUR_HOST/widget.js?group=northstar-motors&location=downtown" async></script>
```

Iframe alternatives:

```html
<iframe src="https://YOUR_HOST/embed/northstar-motors" style="width:100%;height:820px;border:0" title="DriveQuest"></iframe>
<iframe src="https://YOUR_HOST/embed/northstar-motors/downtown" style="width:100%;height:820px;border:0" title="DriveQuest Downtown"></iframe>
```

Full options: [embed-install.md](./embed-install.md).

## Sample groups

| Group id | Name | Demo API key | Locations | Flavor |
|----------|------|--------------|-----------|--------|
| `northstar-motors` | Northstar Motors | `dq_demo_northstar` | `downtown`, `westside` | Used Toyota/Honda-friendly multi-rooftop |
| `lakeside-ev` | Lakeside EV & Hybrid | `dq_demo_lakeside` | `harbor`, `lakefront` | EV/hybrid-forward group |

Landing page (local): http://localhost:8000/

## Inventory updates

See [dealer-inventory-template.md](./dealer-inventory-template.md) for columns (including `location_id`), Excel/CSV downloads, and paste examples. Day-to-day ops: [dealer-admin.md](./dealer-admin.md).

- **Upload:** `POST /api/groups/{id}/inventory/upload` (multipart + optional `period`, `location_id`)
- **Paste:** `POST /api/groups/{id}/inventory/paste` with `{ "text": "…", "period": "week-42", "location_id": "downtown" }`
- **Chat paste:** tabular paste with a header row updates the lot (demo advisor confirms accepted vs bad rows)

When `location_id` is set on ingest, that rooftop’s cars are **merged** (replaced) while other rooftops in the group are kept. Group-wide uploads (no location filter) replace the full live inventory.

## Honest advisor

Persona stays commission-free: recommend only from the scoped inventory, never invent cars, prefer the shopper’s fit over closing. Shopper tour: [shopper-experience.md](./shopper-experience.md).

## Run locally

```bash
pip install -r requirements.txt
uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

Open `/`, `/embed/northstar-motors`, `/embed/northstar-motors/downtown`, or `/static/admin.html?group=lakeside-ev`.

More: [runbook.md](./runbook.md). POC gaps: [poc-limitations.md](./poc-limitations.md).
