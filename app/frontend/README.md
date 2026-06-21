# SIMOPS · Operator Console

Pure HTML + Tailwind (CDN) + vanilla JS. No build step.

## Run locally

```bash
cd app/frontend
python -m http.server 5173
```

Open:

- http://localhost:5173/ — overview dashboard
- http://localhost:5173/pages/sims.html — SIM inventory
- http://localhost:5173/pages/audit.html — audit log
- http://localhost:5173/pages/health.html — system health

## Modes

| URL param | Behaviour |
| --- | --- |
| `?mock=1` (default when API unreachable) | In-browser mock API with 5000 SIMs, live audit ticks every 3s |
| `?mock=0` | Force live mode, talks to backend at `API_BASE` |
| `?api=https://host` | Override API base URL |

The mock layer (`assets/mock-api.js`) intercepts `fetch` for `/api/v1/*` and `/healthz`, so the dashboard demos cleanly with no backend running.

## File map

```
index.html                  overview dashboard shell
pages/sims.html             SIM inventory + transitions
pages/audit.html            paginated audit log
pages/health.html           component health + SLOs
assets/app.js               shared rendering + overview logic
assets/mock-api.js          in-browser API stub (5k SIMs, 6 statuses)
assets/icons.js             inline heroicons-style SVG set
assets/styles.css           dark theme, panels, charts, animations
```

## Backend contract

Reads:
- `GET /api/v1/stats`
- `GET /api/v1/sims?status=&plan_id=&q=&limit=&offset=`
- `GET /api/v1/sims/{iccid}`
- `GET /api/v1/audit?limit=&since=`
- `GET /api/v1/plans`
- `GET /api/v1/health/components`

Writes:
- `POST /api/v1/sims/{iccid}/{allocate|activate|suspend|resume|port|recycle}`

## Keyboard

- `R` — refresh current page (when not focused in an input)
