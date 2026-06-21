# SIM Provisioning — Backend

Production-shaped FastAPI service implementing the SIM lifecycle state machine
for the DevOps Case Study 20 platform.

## Stack

- **FastAPI** + async **SQLAlchemy** (asyncpg in prod, aiosqlite in tests)
- **Alembic** for migrations
- **Prometheus** metrics via `prometheus-fastapi-instrumentator`
- **structlog** for structured JSON logs (pretty in dev)
- **httpx + tenacity** for the HLR/HSS adapter with retries
- **pytest + pytest-asyncio** for tests

## Local quickstart

```bash
cd app/backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env

# Option A — SQLite (no infra needed)
export DATABASE_URL="sqlite+aiosqlite:///./sim_provisioning.db"

# Option B — Postgres (preferred)
docker run --rm -d --name simpg -e POSTGRES_USER=sim -e POSTGRES_PASSWORD=sim \
  -e POSTGRES_DB=sim_provisioning -p 5432:5432 postgres:16-alpine
export DATABASE_URL="postgresql+asyncpg://sim:sim@localhost:5432/sim_provisioning"

# Apply schema (Postgres only — SQLite is auto-created by `seed`)
alembic upgrade head

# Seed plans, 5000 SIMs and 1000 MSISDNs
python -m app.seed

# Run mock HLR sidecar (separate terminal)
uvicorn mock_hlr.main:app --port 9090

# Run API
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open:

- API docs: http://localhost:8000/docs
- Health:   http://localhost:8000/healthz
- Ready:    http://localhost:8000/readyz
- Metrics:  http://localhost:8000/metrics

## State machine

```
PENDING ── allocate ──▶ ALLOCATED ── activate ──▶ ACTIVE
                                        │            │
                                        │            ├── suspend ──▶ SUSPENDED ── resume ──▶ ACTIVE
                                        │            └── port_out ──▶ PORTED  (terminal)
                                        └── recycle ──▶ RECYCLED  (terminal)
```

Every transition writes an `AuditEvent` row containing actor, request_id,
from/to status and reason.

## Endpoints

| Method | Path                                  | Notes                                |
| ------ | ------------------------------------- | ------------------------------------ |
| GET    | `/api/v1/sims`                        | filter by `status`, `plan_id`, pages |
| GET    | `/api/v1/sims/{iccid}`                | Luhn-validated                       |
| POST   | `/api/v1/sims/{iccid}/allocate`       | PENDING → ALLOCATED                  |
| POST   | `/api/v1/sims/{iccid}/activate`       | ALLOCATED → ACTIVE (assigns MSISDN)  |
| POST   | `/api/v1/sims/{iccid}/suspend`        | ACTIVE → SUSPENDED                   |
| POST   | `/api/v1/sims/{iccid}/resume`         | SUSPENDED → ACTIVE                   |
| POST   | `/api/v1/sims/{iccid}/port_out`       | ACTIVE → PORTED                      |
| POST   | `/api/v1/sims/{iccid}/recycle`        | * → RECYCLED                         |
| POST   | `/api/v1/sims/bulk_provision`         | CSV-like JSON batch                  |
| GET    | `/api/v1/plans`                       | list                                 |
| POST   | `/api/v1/plans`                       | admin                                |
| GET    | `/api/v1/stats`                       | dashboard KPIs                       |
| GET    | `/api/v1/audit`                       | live tail / pagination               |

## Custom Prometheus metrics

- `sim_state_transitions_total{from_status,to_status}` — counter
- `sim_activation_latency_seconds` — histogram (allocated → activated)
- `msisdn_pool_remaining` — gauge
- `hlr_calls_total{outcome}` — counter

## Tests

```bash
pytest -q
```

Tests use an in-memory SQLite database and a `FakeHlrClient`, so no infra is
required.

## Configuration

All settings come from environment variables (see `.env.example`). The
`pydantic-settings` schema lives in `app/config.py`.
