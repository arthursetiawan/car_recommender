# Embed install (POC)

Drop DriveQuest onto a dealer website with a script tag or iframe. Primary query param is **group**; **location** is optional for a single rooftop.

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

1. Load the host page; iframe appears under the script.
2. Greeting mentions the group/location and inventory count.
3. Chip through budget; contenders should only be that tenant’s cars.
4. Change inventory in admin; refresh embed — lot should update.
