#!/bin/bash
# ci_map.sh OUT.html: build the map in a CI checkout, after the declaration table was extracted
# there. It is compared, by import lines, against the tree of about a day ago, so the page can say
# what changed. Run from the checkout's root.
set -euo pipefail
out="$1"; here="$(cd "$(dirname "$0")" && pwd)"; args=(--out "$out")
git fetch --quiet --shallow-since="3 days ago" origin "${GITHUB_REF_NAME:-main}" 2>/dev/null || true
base=$(git rev-list -1 --before="20 hours ago" HEAD 2>/dev/null || true)
if [ -n "$base" ] && [ "$base" != "$(git rev-parse HEAD)" ]; then
  mkdir -p .lake/build/taproot-base
  git archive "$base" Linglib Studies | tar -x -C .lake/build/taproot-base
  args+=(--base .lake/build/taproot-base --base-label "main ${base:0:10}")
fi
# no editor links on a published page: a path on the build machine means nothing to its reader
TAPROOT_EDITOR=none python3 "$here/map.py" "${args[@]}" --sha "$(git rev-parse HEAD)"
