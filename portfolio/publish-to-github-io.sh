#!/usr/bin/env bash
# One-shot publisher for https://arthursetiawan.github.io/
# Requires write access to arthursetiawan/arthursetiawan.github.io
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
TARGET_DIR="${1:-}"
BRANCH="${BRANCH:-main}"

if [[ -z "${TARGET_DIR}" ]]; then
  TMP="$(mktemp -d)"
  TARGET_DIR="${TMP}/arthursetiawan.github.io"
  git clone --depth 1 "https://github.com/arthursetiawan/arthursetiawan.github.io.git" "${TARGET_DIR}"
fi

# Prefer rsync; fall back to find/cp when unavailable.
if command -v rsync >/dev/null 2>&1; then
  rsync -a --delete \
    --exclude '.git' \
    --exclude 'publish-to-github-io.sh' \
    --exclude 'PUBLISH.md' \
    --exclude 'README.md' \
    "${ROOT}/" "${TARGET_DIR}/"
else
  find "${TARGET_DIR}" -mindepth 1 -maxdepth 1 ! -name '.git' -exec rm -rf {} +
  cp -a "${ROOT}/." "${TARGET_DIR}/"
  rm -f "${TARGET_DIR}/publish-to-github-io.sh" "${TARGET_DIR}/PUBLISH.md"
fi

# Preserve useful legacy tooling if present in clone already; otherwise leave as copied.
cd "${TARGET_DIR}"
git checkout -B "${BRANCH}"
git add -A
git status --short
git commit -m "Refresh portfolio: full-stack automotive data scientist" || {
  echo "Nothing to commit."
  exit 0
}
git push origin "${BRANCH}"
echo "Published. Live at https://arthursetiawan.github.io/"
