# Portfolio + DriveQuest Pages site

Static site deployed by GitHub Actions (`.github/workflows/pages.yml`) from this folder.

## URLs

| Surface | URL (after Pages is enabled on `car_recommender`) |
|---------|-----------------------------------------------------|
| Portfolio home | https://arthursetiawan.github.io/car_recommender/ |
| DriveQuest POC hub | https://arthursetiawan.github.io/car_recommender/drivequest/ |
| Static shopper demo | https://arthursetiawan.github.io/car_recommender/drivequest/demo.html |
| POC docs (HTML) | https://arthursetiawan.github.io/car_recommender/drivequest/docs/ |

Personal user site (separate repo, already live): https://arthursetiawan.github.io/  
Sync this folder there with `./publish-to-github-io.sh` when you have write access — DriveQuest then also appears at `https://arthursetiawan.github.io/drivequest/`.

## Preview locally

```bash
cd portfolio
python3 -m http.server 8080 --bind 127.0.0.1
# http://127.0.0.1:8080/  ·  /drivequest/  ·  /drivequest/demo.html
```

## Notes

- Pages is **static** — no FastAPI. Full embed/chat/ingest: run the repo with uvicorn (see `docs/runbook.md`).
- First deploy may need the workflow’s `enablement: true` (or Settings → Pages → Source: GitHub Actions).
