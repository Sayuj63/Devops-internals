#!/usr/bin/env bash
# Run the application's seed routine inside the running api container.
# Usage:
#   ./scripts/seed-postgres.sh                    # default (50 SIMs, 3 plans)
#   COUNT=500 PLANS=5 ./scripts/seed-postgres.sh

set -Eeuo pipefail

COMPOSE="${COMPOSE:-docker compose}"
SERVICE="${SERVICE:-api}"
COUNT="${COUNT:-50}"
PLANS="${PLANS:-3}"

echo "▶ waiting for postgres..."
$COMPOSE exec -T postgres pg_isready -U simprov -d simprov >/dev/null

echo "▶ running migrations (alembic upgrade head)"
$COMPOSE exec -T "$SERVICE" alembic upgrade head || {
  echo "  (alembic not present yet — skipping)";
}

echo "▶ seeding ${COUNT} SIMs across ${PLANS} plans"
$COMPOSE exec -T -e SEED_SIM_COUNT="$COUNT" -e SEED_PLAN_COUNT="$PLANS" \
  "$SERVICE" python -m app.seed

echo "✓ seed complete"
