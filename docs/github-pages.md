# DriveQuest on GitHub Pages

## Motormarket pattern (what we mirrored)

| | **Motormarket** | **DriveQuest** |
|--|-----------------|----------------|
| Live project Pages | https://arthursetiawan.github.io/motormarket/ | https://arthursetiawan.github.io/car_recommender/ |
| Deploy | Actions → `docs/portfolio/` | Actions → `portfolio/` |
| Portfolio entry | Hero + **Open Motormarket** / product band | Hero + **Open DriveQuest** / `#drivequest` band |
| Hosted try-it | `/motormarket/` (+ auctions) | `/drivequest/` (+ `demo.html` shopper quest) |

Motormarket repo: https://github.com/arthursetiawan/motormarket · workflow deploys static portfolio with nested product demo.

## Home button

Every DriveQuest Pages surface (portfolio, `drivequest/` hub, shopper demo, docs, resume) includes a **Home** link to the user site: https://arthursetiawan.github.io/

Motormarket (`arthursetiawan/motormarket`) was not editable from this agent (push 403) — add the same Home control there when you have write access.

## Live DriveQuest URLs

| Page | URL |
|------|-----|
| Portfolio (entry) | https://arthursetiawan.github.io/car_recommender/ |
| Product landing | https://arthursetiawan.github.io/car_recommender/drivequest/ |
| Shopper try-it | https://arthursetiawan.github.io/car_recommender/drivequest/demo.html |
| Docs (HTML) | https://arthursetiawan.github.io/car_recommender/drivequest/docs/ |

Personal site: https://arthursetiawan.github.io/ (separate repo). Sync with `portfolio/publish-to-github-io.sh` when you have write access.

## Deploy

`.github/workflows/pages.yml` publishes `portfolio/` on push to `main` (or **Actions → Deploy GitHub Pages**). Pages source: GitHub Actions.

## Limits

Static only — no FastAPI on Pages. Full dealer-group plugin: [runbook.md](./runbook.md).
