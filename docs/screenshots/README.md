# SIM-OPS · demonstration screenshots

This folder holds the demonstration captures the documentation site references in its carousel and in the deliverables matrix. They are added during demo-prep on the day of the viva so they show real, current data — they are intentionally not checked in earlier (state would go stale and look fake).

## Required captures

| File | What it must show | Capture from |
| ---- | ----------------- | ------------ |
| `01-dashboard.png` | Operator dashboard with live SIM inventory, KPI tiles (active / suspended / ported), and the activation feed scrolling. Filter by ICCID prefix `8991100`. | `https://sim-ops.itm.edu/dashboard` in Chrome at 1440×900. |
| `02-grafana.png` | SLO board over a 24h window with the burn-rate panel, p50/p95/p99 latency, and error budget remaining. Include the dashboard title bar. | Grafana → `SIM-OPS / SLO board`. |
| `03-kibana.png` | Discover view filtered to `kubernetes.labels.app:"api" AND iccid:"8991100012345678901"` showing the trace across pods. | Kibana → Discover. |
| `04-vault.png` | The `database/roles/api` UI page with a freshly-issued lease, and the policy editor for `sim-ops-api`. Two panels stitched. | Vault UI → Secrets and Policies. |
| `05-jenkins.png` | A green pipeline run for the latest `main` commit, all seven stages with timings. | Jenkins → `sim-ops/main` build. |
| `06-kubectl.png` | Terminal capture of `kubectl get pods -n sim-ops -o wide` and `kubectl top pods -n sim-ops`, side-by-side, all pods Ready. | iTerm at 14pt JetBrains Mono. |
| `07-terraform.png` | `terraform plan` against production state showing `0 to add, 0 to change, 0 to destroy`. | `terraform/envs/prod` workspace. |

## Capture conventions

- PNG, 1600×1000 max width.
- Crop to the window content; no desktop chrome.
- Dark theme to match the docs site.
- Redact any token, ARN, or email before saving.
- Name files exactly as listed — the carousel resolves by filename.

## Adding more

If we capture extras, drop them in `screenshots/extras/` and add the path to the deliverables matrix in `docs/index.html`. They will not appear in the carousel unless wired in explicitly.
