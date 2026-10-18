# POC limitations (honest)

DriveQuest in this repo is a **demoable vertical slice**, not a production dealer platform. Use this list in stakeholder conversations so expectations stay clear.

## Product / UX

| Gap | POC reality |
|-----|-------------|
| Lead capture / CRM | None — no forms to salesforce, email drip, or SMS |
| Appointments / F&I | Not present |
| Multi-language | English UI/copy only |
| Accessibility | Basic HTML; not audited WCAG |
| Mobile polish | Responsive enough to demo; not app-store quality |
| Photo quality | Sample/static images; optional `photo_url` not a DAM |

## Tenancy & security

| Gap | POC reality |
|-----|-------------|
| Auth | Demo API keys in JSON; optional on requests; easy to skip |
| Admin ACL | Anyone who can hit admin URL can paste in demo mode |
| Chat ingest | Shopper chat can update inventory if paste looks like CSV — great for demos, bad for prod |
| Secrets | Keys in `group.json` on disk |
| CORS | Allow-all |
| iframe hardening | No strict `frame-ancestors` / CSP story |
| Multi-region / SSO | N/A |

## Inventory & data

| Gap | POC reality |
|-----|-------------|
| DMS / feed sync | Manual Excel/CSV/paste only |
| Conflict / partial edit | Full replace or per-location merge — no row-level PATCH UI |
| VIN decode | Field stored; not validated/decoded |
| Market value | Spreadsheet or defaults to asking price |
| Reliability/safety | Defaults if omitted |
| History / audit | Period snapshots only; no who/when UI |
| Concurrent writers | Last write wins on JSON files |

## Advisor / AI

| Gap | POC reality |
|-----|-------------|
| Without OpenAI | Deterministic demo advisor (still useful) |
| With OpenAI | Tool-calling loop; cost/latency not budgeted |
| Hallucination controls | Prompt + “only this inventory” — not a formal guardrail product |
| Eval harness | Light pytest coverage; no large offline eval set in-repo |
| Memory | In-process session dict — lost on restart; not multi-instance safe |

## Scoring / ROI

| Gap | POC reality |
|-----|-------------|
| Hex scores | Heuristics from JSON fields |
| ROI rates | User/default knobs, not live utility/gas APIs |
| Incentives | Manual input — not geo/eligibility engine |
| Compliance | Not financial/legal advice; demo copy only |

## Platform / ops

| Gap | POC reality |
|-----|-------------|
| Hosting | Run uvicorn locally / simple Docker |
| Observability | No OTel/metrics dashboards wired for dealers |
| Rate limits | None |
| Backups | Git + local files |
| CI | Ad hoc pytest; don’t assume full prod pipeline |
| Schema migrations | File JSON — no migration framework for tenants |

## What *is* intentionally solid for a POC

- Clear **group → location** model and embed params
- Inventory-scoped recommendations for quest / hex / ROI
- Excel + paste ingest with **bad-row reporting**
- Honest advisor persona (anti-upsell)
- Demo mode without cloud credentials
- Sample multi-rooftop data you can click through in minutes

## If this graduates past POC

Typical next slices (not promised here): real auth, DMS connector, hosted multi-tenant DB, lead webhooks, CSP/CORS lockdown, remove public chat-ingest, evals on advisor quality, CDN embeds, and ops runbooks beyond this file.

Back to [poc-overview.md](./poc-overview.md) · [README.md](./README.md)
