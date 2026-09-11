#!/usr/bin/env bash
# publish-site.sh -- rebuild the search database and publish docs/ to
# GitHub Pages.
#
# Loosely mirrors how ~/GitHub/stedt-static publishes: there, `stedt build`
# regenerates the site and a push to `main` triggers a GitHub Actions
# workflow that builds and deploys it. This project's docs/ has no build
# step of its own, though (no Node/npm, no bundler -- see README.md's
# "Static search website" section for why), so there's nothing left for a
# CI workflow to usefully do that this script doesn't already do locally:
# regenerate the one generated file (the search database), commit, push.
# GitHub Pages (once set to Settings -> Pages -> Deploy from a branch ->
# main -> /docs) serves whatever's in docs/ on main directly -- no Actions
# workflow needed.
#
# This script only touches docs/ and src/build_search_db.py -- any other
# pending changes in your working tree (e.g. unrelated LaTeX/pipeline
# work) are left alone, uncommitted, exactly as `git status` shows them
# now. Commit those yourself, separately, before or after running this.
#
# Usage:
#   src/publish-site.sh                          # default commit message
#   src/publish-site.sh "Refresh site after fixing entry X"

set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f generated/tei/lahu.xml ]; then
  echo "error: generated/tei/lahu.xml not found -- run src/regenerate-all-files.sh first" >&2
  exit 1
fi

branch=$(git rev-parse --abbrev-ref HEAD)
if [ "$branch" != "main" ]; then
  echo "warning: current branch is '$branch', not 'main' -- GitHub Pages is" >&2
  echo "         configured to deploy from main, so pushing here won't publish anything." >&2
  read -r -p "Continue anyway? [y/N] " ans
  case "$ans" in [yY]) ;; *) exit 1 ;; esac
fi

echo "==> Rebuilding docs/lahu-dictionary.sqlite3 from generated/tei/lahu.xml"
python3 src/build_search_db.py

changes="$(git status --porcelain -- docs/ src/build_search_db.py)"
if [ -z "$changes" ]; then
  echo "==> No changes in docs/ or src/build_search_db.py -- nothing to publish."
  exit 0
fi

echo "==> Changes to publish:"
echo "$changes"
echo

msg="${1:-Update dictionary search website}"
git add docs/ src/build_search_db.py
git commit -m "$msg"

echo "==> Pushing to origin/$branch"
git push origin "$branch"

echo "==> Done. GitHub Pages will redeploy in a minute or two."
echo "    (First time only: repo Settings -> Pages -> Build and deployment"
echo "    -> Source: 'Deploy from a branch' -> Branch: $branch, folder /docs.)"
