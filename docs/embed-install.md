# Embed install (POC)

Drop DriveQuest onto a dealer website with a script tag or iframe. Primary query param is **group**; **location** is optional for a single rooftop.

## GH Pages vs API host

| What you want | Where | Embed script? |
|---------------|-------|----------------|
| **Recruiter / shopper story** (static quest, hex, EV ROI on sample lots) | [Hosted demo](https://arthursetiawan.github.io/car_recommender/drivequest/demo.html) | No — client-side only; no `widget.js` on Pages |
| **Real dealer-site embed** (live inventory, chat API, ingest) | Your FastAPI host (`uvicorn` or container) | Yes — snippets below with `YOUR_HOST` set to that origin |

GitHub Pages cannot serve `/widget.js`, `/embed/…`, or `/api/*`. Point integrators at a deployed backend; point recruiters at the hosted try-it link above. Negotiation worksheets and fee audit live in **[vehicle-negotiator-engine](https://github.com/arthursetiawan/vehicle-negotiator-engine)** (Dealer-Counter) — not in this install path.

## One-line script (recommended)

**Whole dealer group** (all locations’ inventory):

```html
<script src="https://YOUR_HOST/widget.js?group=northstar-motors" async></script>
```

**One store / rooftop:**

```html
<script src="https://YOUR_HOST/widget.js?group=northstar-motors&location=downtown" async></script>
```

Optional demo API key (only needed if you enforce keys later):

```html
<script src="https://YOUR_HOST/widget.js?group=northstar-motors&location=downtown&api_key=dq_demo_northstar" async></script>
```

Optional height: `&height=900` (default `820`).

`dealer=` is accepted as an alias for `group=`.

### What the script does

`/widget.js` injects an iframe pointing at `/embed/{group}` (plus `?location=` when set). Parent page needs ordinary HTTPS (or localhost) access to `YOUR_HOST`.

## Iframe

```html
<iframe
  src="https://YOUR_HOST/embed/northstar-motors"
  style="width:100%;max-width:1120px;height:820px;border:0;border-radius:16px"
  title="DriveQuest"
  loading="lazy"
></iframe>
```

Location path form:

```html
<iframe src="https://YOUR_HOST/embed/northstar-motors/downtown" …></iframe>
```

Equivalent query: `/embed/northstar-motors?location=downtown`.

## Local samples

| URL | Scope |
|-----|--------|
| http://localhost:8000/ | Landing + install snippets |
| http://localhost:8000/embed/northstar-motors | Northstar group |
| http://localhost:8000/embed/northstar-motors/downtown | Downtown only |
| http://localhost:8000/embed/lakeside-ev/harbor | Lakeside Harbor |
| http://localhost:8000/widget.js?group=lakeside-ev&location=lakefront | Script (returns JS) |

## Sample tenants

| Group id | Locations | Demo API key |
|----------|-----------|--------------|
| `northstar-motors` | `downtown`, `westside` | `dq_demo_northstar` |
| `lakeside-ev` | `harbor`, `lakefront` | `dq_demo_lakeside` |

Add a group: create `data/dealers/<id>/` with `group.json` + `inventory.json`, register in `data/dealers/index.json`. POC — no admin UI for provisioning.

## CORS / embedding notes (POC)

- API allows all origins (`CORSMiddleware allow_origins=["*"]`) for easy demos.
- Production would tighten origins, cookies/keys, and CSP `frame-ancestors`.
- Widget assumes it can reach the same host that serves `/embed/…`.

## Branding

Pulled from `group.json` → CSS variables on the embed (`--copper`, `--teal`, titles). Location embeds can override display name/tagline from the location object.

## Verify install

**FastAPI embed (dealer integrator)**

1. Load the parent page over HTTPS (or `localhost`); the iframe appears after the script runs.
2. Greeting names the **group** (and **location** when set) and shows an inventory count.
3. Tap budget → body type → priority; shortlist cars must belong to that tenant only.
4. Upload or paste ingest in [`/admin`](http://localhost:8000/admin.html); refresh embed — VINs/prices should match the latest `inventory.json`.
5. Optional: `curl -s http://YOUR_HOST/health` returns OK while the embed is in use.

**Recruiter smoke (no backend)**

1. Open [demo.html](https://arthursetiawan.github.io/car_recommender/drivequest/demo.html).
2. Switch **Northstar Motors** vs **Lakeside EV** — lot and branding change.
3. Complete the quest chips; hex chart renders for the shortlist.
4. Expand **EV vs gas ROI** — break-even updates when miles/year changes.

Hosted embed docs (HTML): [drivequest/docs/embed.html](https://arthursetiawan.github.io/car_recommender/drivequest/docs/embed.html).
