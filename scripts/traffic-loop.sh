#!/usr/bin/env bash
# Continuous traffic generator so Grafana rate() panels and histograms have data.
# Drives the real lifecycle: PENDING → ALLOCATED → ACTIVE → (occasionally) SUSPENDED → ACTIVE.
# Sustained reads on top to fatten http request counters.
set -u
API="${API:-http://localhost:8000}"
PLAN="${PLAN:-b71b4e9f-e143-45e3-8711-ce0246672fc1}"

# Pick a random PENDING iccid (avoids contention with parallel workers)
pick_pending() {
  local offset=$((RANDOM % 200))
  curl -s "${API}/api/v1/sims?status=PENDING&limit=1&offset=${offset}" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print((d.get('items') or [{}])[0].get('iccid',''))" 2>/dev/null
}

pick_allocated() {
  curl -s "${API}/api/v1/sims?status=ALLOCATED&limit=1" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print((d.get('items') or [{}])[0].get('iccid',''))" 2>/dev/null
}

pick_active() {
  local offset=$((RANDOM % 50))
  curl -s "${API}/api/v1/sims?status=ACTIVE&limit=1&offset=${offset}" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print((d.get('items') or [{}])[0].get('iccid',''))" 2>/dev/null
}

post() {
  local path="$1" body="$2"
  curl -s -o /dev/null -w "" \
    -H "content-type: application/json" \
    -X POST "${API}${path}" -d "$body"
}

reads() {
  for s in ACTIVE PENDING SUSPENDED ALLOCATED; do
    curl -s -o /dev/null "${API}/api/v1/sims?status=${s}&limit=20" &
  done
  curl -s -o /dev/null "${API}/api/v1/stats/summary" &
}

while true; do
  reads

  # Allocate a fresh PENDING SIM
  ID=$(pick_pending)
  if [ -n "$ID" ]; then
    post "/api/v1/sims/${ID}/allocate" \
      "{\"plan_id\":\"${PLAN}\",\"actor\":\"traffic-loop\",\"reason\":\"viva traffic\"}" &
  fi

  # Activate any ALLOCATED SIM
  ID=$(pick_allocated)
  if [ -n "$ID" ]; then
    post "/api/v1/sims/${ID}/activate" \
      "{\"actor\":\"traffic-loop\",\"reason\":\"viva traffic\"}" &
  fi

  # Every ~5 iterations, suspend then resume an ACTIVE SIM (more histogram samples)
  if [ $((RANDOM % 5)) -eq 0 ]; then
    ID=$(pick_active)
    if [ -n "$ID" ]; then
      post "/api/v1/sims/${ID}/suspend" \
        "{\"actor\":\"traffic-loop\",\"reason\":\"viva traffic\"}"
      post "/api/v1/sims/${ID}/resume" \
        "{\"actor\":\"traffic-loop\",\"reason\":\"viva traffic\"}" &
    fi
  fi

  wait
  sleep 1
done
