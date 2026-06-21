#!/usr/bin/env bash
# scripts/shot.sh — screenshot a URL via a dedicated Chrome instance.
#
# Never raises the window (uses `screencapture -l <CGWindowID>`), so the
# user's active tab in their main Chrome is never disturbed.
#
# Usage:
#   scripts/shot.sh <output.png> <url> [wait_seconds]
#
# Env:
#   SHOT_PROFILE  Chrome profile dir (default ~/.shotchrome).
#                 Sessions persist — login to Vault/Kibana once and it sticks.
#   SHOT_BOUNDS   "x,y,w,h" initial window bounds (default "20,60,1680,1050")
#   PY            Python with Quartz bindings (default ~/.shotvenv/bin/python)
set -euo pipefail

OUT="$1"
URL="$2"
WAIT="${3:-6}"
PROFILE="${SHOT_PROFILE:-$HOME/.shotchrome}"
BOUNDS="${SHOT_BOUNDS:-20,60,1680,1050}"
PY="${PY:-$HOME/.shotvenv/bin/python}"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

mkdir -p "$PROFILE" "$(dirname "$OUT")"

find_shot_pid() {
  pgrep -fl "Google Chrome.*--user-data-dir=$PROFILE" \
    | awk '!/--type=/{print $1; exit}' || true
}

SHOT_PID="$(find_shot_pid)"
if [ -z "$SHOT_PID" ]; then
  IFS=, read -r X Y W H <<< "$BOUNDS"
  nohup "$CHROME" \
    --user-data-dir="$PROFILE" \
    --no-first-run --no-default-browser-check \
    --window-position="${X},${Y}" \
    --window-size="${W},${H}" \
    "$URL" >/dev/null 2>&1 &
  for _ in $(seq 1 40); do
    sleep 0.3
    SHOT_PID="$(find_shot_pid)"
    [ -n "$SHOT_PID" ] && break
  done
  sleep 2
else
  "$CHROME" --user-data-dir="$PROFILE" "$URL" >/dev/null 2>&1 || true
fi

if [ -z "$SHOT_PID" ]; then
  echo "ERROR: could not start dedicated Chrome" >&2
  exit 1
fi

sleep "$WAIT"

WID=$("$PY" - "$SHOT_PID" <<'PY'
import sys
from Quartz import (
    CGWindowListCopyWindowInfo,
    kCGWindowListOptionAll,
    kCGNullWindowID,
)
target_pid = int(sys.argv[1])
best, best_area = None, 0
for w in CGWindowListCopyWindowInfo(kCGWindowListOptionAll, kCGNullWindowID):
    if w.get("kCGWindowOwnerPID") != target_pid:
        continue
    if w.get("kCGWindowLayer", 0) != 0:
        continue  # ignore menus / overlays / sub-windows
    bounds = w.get("kCGWindowBounds", {}) or {}
    area = bounds.get("Width", 0) * bounds.get("Height", 0)
    if area > best_area:
        best, best_area = w["kCGWindowNumber"], area
print(best or "")
PY
)

if [ -z "$WID" ]; then
  echo "ERROR: no CGWindow found for PID $SHOT_PID" >&2
  exit 1
fi

# -l captures the window by CGWindowID — does NOT bring it to front.
screencapture -l "$WID" -x -o "$OUT"
echo "captured $OUT ($(wc -c < "$OUT") bytes) [pid=$SHOT_PID wid=$WID]"
