# Monitoring stack

Prometheus + Alertmanager + Grafana, configured for the SIM Provisioning platform.

## Layout

```
monitoring/
  prometheus/
    prometheus.yml                 ← scrape config (static + k8s SD)
    rules/sim-prov.rules.yml       ← recording + alerting rules
  alertmanager/
    alertmanager.yml               ← Slack routing, severity-based dedupe
  grafana/
    datasources/datasources.yml    ← Prometheus, Loki, Alertmanager
    dashboards/dashboards.yml      ← provisioning provider
    dashboards/sim-provisioning.json
    dashboards/golden-signals.json
```

## Metric contract expected from `app/backend`

| Metric                                  | Type      | Labels                  |
| --------------------------------------- | --------- | ----------------------- |
| `http_requests_total`                   | counter   | `service`, `route`, `code` |
| `http_request_duration_seconds_bucket`  | histogram | `service`, `route`      |
| `sim_activations_total`                 | counter   | `result` (`success`/`failure`) |
| `sim_activation_duration_seconds_bucket`| histogram | `route`                 |
| `sim_count_by_status`                   | gauge     | `status`                |
| `msisdn_pool_size`                      | gauge     | —                       |
| `msisdn_pool_allocated`                 | gauge     | —                       |
| `hlr_calls_total`                       | counter   | `result`                |

## Alerts that fire end-to-end

- `HighErrorRate` (critical) — API 5xx > 5% for 10m
- `HighActivationLatency` (warning) — p95 > 5s for 15m
- `MsisdnPoolLow` / `MsisdnPoolExhausted`
- `DBDown` (critical) — `pg_up == 0`
- `PodCrashLooping`
- `CertExpiringSoon`
- `HlrCallFailureRateHigh`

Every alert ships with `summary`, `description`, and `runbook_url`.

## Local smoke test

```bash
make up
open http://localhost:9090/targets       # Prometheus
open http://localhost:9093/#/alerts      # Alertmanager
open http://localhost:3000               # Grafana (admin/admin)
```
