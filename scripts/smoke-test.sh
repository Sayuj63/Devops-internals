#!/usr/bin/env bash
# Smoke test for the SIM Provisioning API.
# Hits /healthz, /readyz, GET /sims, and asserts the response shape.
#
# Usage:
#   BASE_URL=http://localhost:8000 ./scripts/smoke-test.sh
#   STAGING_URL=https://staging.sim-prov.example.com ./scripts/smoke-test.sh

set -Eeuo pipefail

BASE="${BASE_URL:-${STAGING_URL:-http://localhost:8000}}"
TIMEOUT="${TIMEOUT:-10}"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT

ok()   { printf '\033[1;32m✓\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31m✗\033[0m %s\n' "$*" >&2; exit 1; }

probe() {
  local path="$1" expected="$2"
  local code
  code=$(curl --silent --show-error --max-time "$TIMEOUT" \
              -o "$TMP/body" -w '%{http_code}' "${BASE}${path}")
  [[ "$code" == "$expected" ]] || fail "${path} → ${code} (expected ${expected}); body: $(head -c 200 "$TMP/body")"
  ok "${path} → ${code}"
}

probe /healthz 200
probe /readyz  200

# /sims should return JSON list with the expected shape.
code=$(curl --silent --show-error --max-time "$TIMEOUT" \
            -o "$TMP/sims.json" -w '%{http_code}' "${BASE}/sims?limit=5")
[[ "$code" == "200" ]] || fail "/sims?limit=5 → ${code}; body: $(head -c 200 "$TMP/sims.json")"

count=$(python3 -c '
import json, sys
data = json.load(open(sys.argv[1]))
items = data["items"] if isinstance(data, dict) and "items" in data else data
assert isinstance(items, list), "expected a list of SIMs"
for s in items[:5]:
    for f in ("iccid", "status"):
        assert f in s, f"missing field {f}"
print(len(items))
' "$TMP/sims.json")

ok "/sims returned ${count} item(s) with iccid + status"

# /metrics should expose Prometheus format
code=$(curl --silent --show-error --max-time "$TIMEOUT" \
            -o "$TMP/metrics" -w '%{http_code}' "${BASE}/metrics" || true)
if [[ "$code" == "200" ]] && grep -q '^# HELP ' "$TMP/metrics"; then
  ok "/metrics exposes Prometheus format"
else
  printf '\033[1;33m!\033[0m /metrics not validated (status %s) — skipping (non-fatal)\n' "$code"
fi

ok "smoke test passed against ${BASE}"
