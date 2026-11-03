# DriveQuest on GitHub Pages

## Live URLs (project Pages)

After the deploy workflow succeeds on `car_recommender`:

| Page | URL |
|------|-----|
| Portfolio | https://arthursetiawan.github.io/car_recommender/ |
| DriveQuest hub | https://arthursetiawan.github.io/car_recommender/drivequest/ |
| Static demo | https://arthursetiawan.github.io/car_recommender/drivequest/demo.html |
| Docs (HTML) | https://arthursetiawan.github.io/car_recommender/drivequest/docs/ |

## User site

https://arthursetiawan.github.io/ already hosts the recruiter portfolio (separate repo `arthursetiawan.github.io`). Cloud agents cannot push that repo (403). To mirror DriveQuest onto the user site root:

```bash
cd portfolio && ./publish-to-github-io.sh
# → https://arthursetiawan.github.io/drivequest/
```

## What was published

- Static DriveQuest hub, chip-quest + hex demo (sample Northstar / Lakeside JSON), HTML docs index
- Workflow `.github/workflows/pages.yml` with `enablement: true` so Actions can turn on Pages
- Portfolio home CTAs point at `drivequest/`

## Limits

GitHub Pages cannot run FastAPI. Full plugin = local/Docker uvicorn (see [runbook.md](./runbook.md)).
