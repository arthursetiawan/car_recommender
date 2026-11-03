# DriveQuest on GitHub Pages

## Target live URLs (project Pages)

| Page | URL |
|------|-----|
| Portfolio | https://arthursetiawan.github.io/car_recommender/ |
| DriveQuest hub | https://arthursetiawan.github.io/car_recommender/drivequest/ |
| Static shopper demo | https://arthursetiawan.github.io/car_recommender/drivequest/demo.html |
| Docs (HTML) | https://arthursetiawan.github.io/car_recommender/drivequest/docs/ |

Personal site (already live, separate repo): https://arthursetiawan.github.io/  
DriveQuest is featured there with repo links. To mirror the static POC under `/drivequest/` on the user site, run `portfolio/publish-to-github-io.sh` with write access to `arthursetiawan/arthursetiawan.github.io`.

## One-time enable (required)

The deploy workflow is in `.github/workflows/pages.yml` (`enablement: true`). Creating the Pages site still needs a **repo admin** click — GitHub Actions tokens get `403 Resource not accessible by integration` until Pages exists:

1. Open https://github.com/arthursetiawan/car_recommender/settings/pages  
2. **Build and deployment → Source:** GitHub Actions  
3. Actions → **Deploy GitHub Pages** → **Run workflow** (or push any change under `portfolio/`)

After a green run, the URLs above should return 200.

## What’s in the static publish (`portfolio/`)

- Recruiter portfolio home with DriveQuest CTAs → `drivequest/`
- `drivequest/` hub — what the POC is, how to run the full FastAPI app
- `drivequest/demo.html` — client-side quest + hex radar over sample Northstar / Lakeside JSON (no server)
- `drivequest/docs/` — HTML overview, embed, run, limitations (+ links to full Markdown in `docs/`)

## Preview without Pages

```bash
cd portfolio
python3 -m http.server 8080 --bind 127.0.0.1
# http://127.0.0.1:8080/drivequest/
```

Or browse the files on `main`: `portfolio/drivequest/`.

## Limits

GitHub Pages is static — no FastAPI, LangChain, or inventory upload API. Full plugin: [runbook.md](./runbook.md).
