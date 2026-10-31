# Arthur Setiawan — recruiter portfolio

Full-stack **automotive data scientist** site aimed at recruiters hiring for:

- Data Scientist
- MLOps
- Data Engineer
- DevOps

## Preview

```bash
cd portfolio
python -m http.server 8080 --bind 127.0.0.1
```

## Publish to https://arthursetiawan.github.io/

Requires write access to `arthursetiawan/arthursetiawan.github.io`:

```bash
./publish-to-github-io.sh
```

Or copy everything in this folder (except `publish-to-github-io.sh`) into that repo’s root and push `main`.

## Alternate: project Pages on car_recommender

The workflow at `.github/workflows/pages.yml` deploys this folder after Pages is enabled on the repo.
