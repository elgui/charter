#!/usr/bin/env bash
# Owner Desk payload. --check is read-only; publication runs only on Gui's confirmation.
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# The Desk copies the payload: use its configured project cwd when running that copy.
[ -f "$repo/package/VERSION" ] || repo="$PWD"
branch=owner-json-content-payload-20261024
release=8ffb6a774af6c09717b0ea0d669cb18d6a2cb404
[ "$(git -C "$repo" branch --show-current)" = "$branch" ] || { echo 'Checkout is not the prepared release branch'; exit 1; }
head="$(git -C "$repo" rev-parse HEAD)"
case "$(git -C "$repo" remote get-url origin)" in
  git@github.com:elgui/charter.git|https://github.com/elgui/charter.git) ;;
  *) echo 'Origin is not the reviewed charter repository'; exit 1 ;;
esac
[ "$(cat "$repo/package/VERSION")" = 0.4.19 ] || { echo 'Unexpected package version'; exit 1; }
git -C "$repo" merge-base --is-ancestor "$release" "$head"
[ -z "$(git -C "$repo" status --porcelain --untracked-files=no)" ] || { echo 'Tracked files changed; review first'; exit 1; }
while IFS= read -r path; do
  case "$path" in
    docs/proposals/publish-owner-json-review.sh|docs/proposals/owner-json-content-contract.md|docs/proposals/owner-json-content-contract-pr.md) ;;
    *) echo "Release content changed after verification: $path"; exit 1 ;;
  esac
done < <(git -C "$repo" diff --name-only "$release" "$head")
if [ "${1:-}" = --check ]; then
  echo "Verified release preparation: 0.4.19, $branch, $head"
  exit 0
fi
printf 'Publish charter 0.4.19 for review\nBranch: %s\nCommit: %s\n' "$branch" "$head"
read -r -p 'Push this branch and open its release PR? [y/N] ' answer
[ "$answer" = y ] || { echo 'No publication performed'; exit 1; }
git -C "$repo" push origin "$head:refs/heads/$branch"
body="$(mktemp)"
trap 'rm -f "$body"' EXIT
git -C "$repo" show "$head:docs/proposals/owner-json-content-contract-pr.md" > "$body"
if ! gh pr view "$branch" --repo elgui/charter --json url --jq .url; then
  gh pr create --repo elgui/charter --base main --head "$branch" \
    --title 'Charter 0.4.19: decision content in owner JSON' \
    --body-file "$body"
fi
echo 'Release branch published for review. Merge, tag, push main/tag and installed upgrades remain owner actions.'
echo 'Follow docs/proposals/owner-json-content-contract.md and docs/install.md for those stages.'
