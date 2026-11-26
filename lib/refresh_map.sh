#!/bin/bash
# refresh_map.sh REPO_CHECKOUT OUT.html [GROUPS.json]
# Build the map with full coverage from the newest successful nightly docs run: download its
# declaration table, take that commit's sources from REPO_CHECKOUT, and compare against the
# successful run before it. Needs `gh` signed in and both commits fetched in REPO_CHECKOUT.
set -euo pipefail
repo="$1"; out="$2"; groups="${3:-}"; here="$(cd "$(dirname "$0")" && pwd)"
slug=$(git -C "$repo" remote get-url origin | sed -E 's#.*github.com[:/]##; s#\.git$##')
runs=$(gh run list --repo "$slug" --workflow docs.yml --status success --limit 2 --json databaseId,headSha -q '.[] | "\(.databaseId) \(.headSha)"')
id=$(echo "$runs" | sed -n 1p | cut -d' ' -f1); sha=$(echo "$runs" | sed -n 1p | cut -d' ' -f2); bsha=$(echo "$runs" | sed -n 2p | cut -d' ' -f2)
work="$repo/scratch/taproot_nightly/$sha"; mkdir -p "$work/src" "$work/base" "$work/table"
[ -f "$work/table/table.tsv" ] || gh run download "$id" --repo "$slug" -n declaration-dependencies -D "$work/table"
tsv=$(find "$work/table" -name table.tsv | head -1)
[ -d "$work/src/Linglib" ] || git -C "$repo" archive "$sha" Linglib Studies | tar -x -C "$work/src"
[ -z "$bsha" ] || [ -d "$work/base/Linglib" ] || git -C "$repo" archive "$bsha" Linglib Studies | tar -x -C "$work/base"
behind=$(git -C "$repo" rev-list --count "$sha..origin/main" 2>/dev/null || echo '?')
args=(--out "$out" --label "main ${sha:0:10}, $behind behind"); [ -z "$bsha" ] || args+=(--base "$work/base" --base-label "main ${bsha:0:10}"); [ -z "$groups" ] || args+=(--groups "$groups")
TAPROOT_TABLE="$tsv" LINGLIB_ROOT="$work/src" python3 "$here/map.py" "${args[@]}"
