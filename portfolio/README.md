# Arthur Setiawan — personal portfolio

Static site positioned for recruiters hiring **Data Scientist**, **MLOps**, **Data Engineer**, and **DevOps** talent — with an automotive full-stack focus.

## Local preview

```bash
cd portfolio
python -m http.server 8080 --bind 127.0.0.1
```

Open [http://127.0.0.1:8080](http://127.0.0.1:8080).

## Publish

1. **This repo (project Pages)** — `.github/workflows/pages.yml` publishes `portfolio/` to `https://arthursetiawan.github.io/car_recommender/` once GitHub Pages is enabled for the repository.
2. **Username site** — copy everything inside `portfolio/` into the root of [`arthursetiawan.github.io`](https://github.com/arthursetiawan/arthursetiawan.github.io). Paths are relative, so no path rewrites are required.
