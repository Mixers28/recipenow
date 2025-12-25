#!/usr/bin/env bash
set -euo pipefail

remote="${1:-origin}"

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd -- "$script_dir/.." && pwd)"

cd "$project_root"

git add docs/PROJECT_CONTEXT.md docs/NOW.md docs/SESSION_NOTES.md
git add -A

branch="$(git rev-parse --abbrev-ref HEAD)"
timestamp="$(date '+%Y-%m-%d %H:%M')"
commit_message="Session notes update - $timestamp"

if [[ -n "$(git status --porcelain)" ]]; then
  git commit -m "$commit_message"
else
  echo "No changes to commit."
fi

git push "$remote" "$branch"
echo "Pushed branch '$branch' to $remote."
