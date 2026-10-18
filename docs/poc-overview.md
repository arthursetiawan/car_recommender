# DriveQuest POC overview

## What it is

**DriveQuest** is a conversational car-shopping advisor you can **embed on a dealer’s site**. It turns “what should I buy?” into a short progressive **quest** (budget → body → priorities → new/used → compare → best match), shows contenders on a **hexagonal radar**, and can explain **EV vs gas** tradeoffs with a simple **break-even (ROI)** calculator.

Inventory is **multi-tenant**: primary tenant is a **dealer group**; an optional **location** (rooftop) scopes the lot for a specific storefront.

This repository engagement is a **proof of concept** — thin vertical slices, sample dealers, demo advisor when OpenAI isn’t configured. It is meant to be **demoable**, not production-hardened.

## Who it’s for

| Audience | What they get in the POC |
|----------|---------------------------|
| **Shoppers** | Chat / chips, hex compare, EV ROI — only cars on *this* group/location lot |
| **Dealer group ops** | Shared inventory + branding; Excel/CSV or paste ingest for the week/day |
| **Rooftop / store sites** | Same plugin with `location=` so the embed shows that lot only |
| **Product / eng demos** | One FastAPI process, sample JSON inventories, no mandatory cloud AI key |

## Vision (POC-sized)

1. **Honest advisor** — persona is “salesperson who isn’t paid to close”: prefer fit over upsell; never invent cars not on the lot.
2. **Dealer-owned inventory** — recommendations, quest, chat, and ROI all read the **latest loaded** inventory for that group (and location filter when set).
3. **Easy embed** — one script tag or iframe; group-wide or single-location.
4. **Easy lot updates** — Excel/CSV template or paste into admin (or chat); confirm accepted rows; flag bad ones.

## What’s in scope (POC)

- FastAPI app + static frontend (chat, hex, ROI panel)
- LangChain + OpenAI when `OPENAI_API_KEY` is set; otherwise deterministic **demo advisor**
- Dealer **groups** with optional **locations**
- Embed: `/embed/{group}` · `/embed/{group}/{location}` · `/widget.js?group=&location=`
- Inventory ingest: `.xlsx` / `.csv` upload + comma-delimited paste
- Downloadable inventory template (CSV + Excel)
- Sample groups: Northstar Motors, Lakeside EV & Hybrid
- EV tradeoff blurbs + ROI calculator (assumptions are demo defaults)
- Hex scoring on six axes from catalog fields

## What’s out of scope (POC)

See [poc-limitations.md](./poc-limitations.md) for detail. Short list:

- Real DMS / inventory sync, auth beyond demo API keys
- Multi-user admin, audit trails, RBAC
- Payment, CRM, lead capture pipelines
- Production hosting, CDN, rate limits, observability
- Perfect VIN decode, photo pipelines, market-value feeds
- Mobile native apps, A/B experimentation platform

## How pieces fit

```
Shopper site ──widget.js / iframe──► DriveQuest embed
                                         │
                    group_id (+ optional location_id)
                                         │
                    ┌────────────────────┴────────────────────┐
                    │  Session → Chat / Choice → Rank + Hex   │
                    │  ROI calculator · EV tradeoffs          │
                    │  Inventory = latest JSON for group/loc  │
                    └────────────────────┬────────────────────┘
                                         │
Dealer admin ──Excel / paste──► inventory.json (+ periods/)
```

## Suggested demo path

1. Open `/` → pick **Northstar Motors** → **Group widget**.
2. Run the quest with chips (budget → body → …) and glance at the hex chart.
3. Open `/embed/northstar-motors/downtown` — fewer cars (that rooftop only).
4. Open admin → paste a tiny CSV → confirm accepted/flagged → refresh embed.
5. On Lakeside, use **Ask EV vs gas** / ROI panel (Model 3 vs a gas car).

## Related docs

- Architecture → [architecture.md](./architecture.md)
- Shopper UI → [shopper-experience.md](./shopper-experience.md)
- Dealer ops → [dealer-admin.md](./dealer-admin.md) · [dealer-inventory-template.md](./dealer-inventory-template.md)
- Install → [embed-install.md](./embed-install.md)
- Run / test → [runbook.md](./runbook.md)
