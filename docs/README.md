# DriveQuest POC documentation

Proof-of-concept docs for **DriveQuest** — an honest, embeddable car advisor scoped to a **dealer group** (optional rooftop **location**). Written for demos: stubs and sample data are called out, not hidden.

## Start here

| Doc | What it covers |
|-----|----------------|
| [poc-overview.md](./poc-overview.md) | Vision, who it’s for, what’s in/out for the POC |
| [architecture.md](./architecture.md) | Group/location tenancy, embed, LangChain advisor, hex, ROI |
| [shopper-experience.md](./shopper-experience.md) | Quest, chat, hex radar, EV ROI from the buyer’s view |
| [dealer-admin.md](./dealer-admin.md) | Excel + paste ingest, admin UI, daily/weekly updates |
| [dealer-plugin.md](./dealer-plugin.md) | Multi-tenant plugin summary + sample groups |
| [dealer-inventory-template.md](./dealer-inventory-template.md) | Column definitions, Excel vs paste, examples |
| [embed-install.md](./embed-install.md) | Widget snippet, group/location params, samples |
| [runbook.md](./runbook.md) | Run locally, env vars, demo mode, test tips |
| [poc-limitations.md](./poc-limitations.md) | Honest gaps vs production |

## 30-second pitch

DriveQuest sits on a dealer website (iframe / one-line script). A shopper chats or taps through a short “quest,” compares cars on a six-axis hex chart, and can check EV vs gas break-even — **only against that group’s (or location’s) latest inventory**. Dealers update the lot with Excel/CSV upload or comma-delimited paste. The advisor persona is deliberately **not** commission-driven.

## Sample tenants (shipped with the repo)

| Group | Locations | Demo API key |
|-------|-----------|--------------|
| `northstar-motors` | `downtown`, `westside` | `dq_demo_northstar` |
| `lakeside-ev` | `harbor`, `lakefront` | `dq_demo_lakeside` |

Local landing: `http://localhost:8000/` after `uvicorn backend.app:app --port 8000`.

## Repo

Mirrored in the git repo under `docs/` (same filenames). Root README links to that index. Code: `arthursetiawan/car_recommender` (`main` includes the dealer-group plugin from PR #50).
