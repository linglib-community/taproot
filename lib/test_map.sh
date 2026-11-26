#!/bin/bash
# test_map.sh PAGE.html [FILE]: open the map in headless Chrome, walk its views and gestures, and
# report. FILE is a dotted file name to test the descent on (default Syntax.Feature.Bundle).
# Exits 1 if a check fails or the page throws. Set CHROME to the browser binary if it is elsewhere.
set -euo pipefail
page="$1"; file="${2:-Syntax.Feature.Bundle}"; here="$(cd "$(dirname "$0")" && pwd)"
chrome="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
tmp="$(dirname "$page")/.$(basename "$page").test.html"; trap 'rm -f "$tmp"' EXIT
{ cat "$page"; printf '<script>window.TAPROOT_TEST_FILE=%s;\n' "\"$file\""; cat "$here/map_test.js"; printf '</script>\n'; } > "$tmp"
out=$("$chrome" --headless=new --disable-gpu --virtual-time-budget=40000 --dump-dom "file://$tmp" 2>/dev/null | grep -o '<title>[^<]*</title>' | sed 's/<[^>]*>//g' || true)
echo "$out" | tr '|' '\n' | sed 's/^ *//'
case "$out" in *"RESULT PASSED"*) exit 0;; *) echo "the page did not pass"; exit 1;; esac
