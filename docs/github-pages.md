# DriveQuest on GitHub Pages

## Live URLs (project Pages)

| Page | URL |
|------|-----|
| Portfolio | https://arthursetiawan.github.io/car_recommender/ |
| DriveQuest hub | https://arthursetiawan.github.io/car_recommender/drivequest/ |
| Static shopper demo | https://arthursetiawan.github.io/car_recommender/drivequest/demo.html |
| Docs (HTML) | https://arthursetiawan.github.io/car_recommender/drivequest/docs/ |

Personal site (separate repo): https://arthursetiawan.github.io/  
To mirror the static POC under `/drivequest/` there: `portfolio/publish-to-github-io.sh` (needs write access to `arthursetiawan.github.io`).

## Status

GitHub Pages is **enabled** on `car_recommender` with **GitHub Actions** as the source. Deploy workflow: `.github/workflows/pages.yml` (publishes the `portfolio/` folder).

Re-deploy: push to `main` touching `portfolio/**` or the workflow file, or run **Actions → Deploy GitHub Pages → Run workflow** from the GitHub UI.

## What’s published (`portfolio/`)

- Portfolio home with DriveQuest CTAs → `drivequest/`
- `drivequest/` hub — POC overview + how to run full FastAPI locally
- `drivequest/demo.html` — client-side quest + hex radar (sample lots)
- `drivequest/docs/` — HTML docs index + overview / embed / run / limitations

## Preview locally

```bash
cd portfolio
python3 -m http.server 8080 --bind 127.0.0.1
# http://127.0.0.1:8080/drivequest/
```

## Limits

GitHub Pages is static — no FastAPI, LangChain, or inventory upload API. Full plugin: [runbook.md](./runbook.md).
