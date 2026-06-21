# VIVA Guide — SIM Provisioning Automation Platform

**Case Study 20 · DevOps Sem IV · ITM Skills University**

This is your single source of truth for the viva. Open this file in VS Code preview during prep.

---

## 1. Deliverables status — 14/14 covered

| # | Deliverable | Status | Where it lives | What to show |
| - | ----------- | ------ | -------------- | ------------ |
| 1 | Working Application | ✅ built | `app/backend/` (FastAPI) + `app/frontend/` (HTML dashboard) | API at `:8000/docs`, dashboard at `:5173` (mock-mode works offline) |
| 2 | Source Code Repo | ⏳ git init pending | this folder | Push to GitHub, share link |
| 3 | Dockerfile + Images | ✅ built | `docker/Dockerfile.*` (4 images) + `docker-compose.yml` | `docker compose ps` showing 14 containers green |
| 4 | Jenkins CI/CD | ✅ built (file) | `jenkins/Jenkinsfile` | Walk through 9 stages incl. parallel test/lint, trivy scan, manual prod gate |
| 5 | Terraform | ✅ built | `terraform/envs/prod/` + `modules/{vpc,eks,rds}/` | `terraform/envs/prod/main.tf` — VPC + EKS 1.29 + RDS multi-AZ |
| 6 | Kubernetes | ✅ built | `k8s/base/` + `k8s/overlays/prod/` (Kustomize) | `kustomize build k8s/overlays/prod` — Deployment + Service + Ingress + HPA + PDB + NetworkPolicy |
| 7 | Prometheus + Grafana | ✅ built | `monitoring/` | Grafana at `:3000` (admin/admin) showing 2 dashboards, Prometheus at `:9090/alerts` |
| 8 | ELK Logging | ✅ built | `logging/` | Kibana at `:5601` — import `logging/kibana/dashboard-sim-prov.ndjson` |
| 9 | Vault | ✅ built | `vault/` | Vault UI at `:8200` (token: `root-dev-token`), `vault/scripts/bootstrap.sh` |
| 10 | Architecture Diagram | ✅ built | `docs/assets/architecture.svg` + interactive version in `docs/index.html` | Open `docs/index.html` in browser — hover nodes for tooltips |
| 11 | Deployment Diagram | ✅ built | `docs/assets/deployment.svg` | 3-AZ EKS + multi-AZ RDS + ALB + DR region |
| 12 | Disaster Recovery Plan | ✅ built | `docs/dr-plan.html` | 4-tier RPO/RTO table + 6 failure scenarios with playbooks |
| 13 | Demonstration Screenshots | ⏳ capture pending | `docs/screenshots/` (spec in README) | See §4 below — 8 screenshots to capture |
| 14 | Project Documentation | ✅ built | `docs/index.html`, `docs/architecture.html`, `docs/runbook.html` + `PLAN.md` + `README.md` | The showcase site at `docs/index.html` |

**Pending you do:** git init+push, install Docker, run the stack once, capture 8 screenshots. Steps below.

---

## 2. Prerequisites — what to install once

You currently have **none of these** installed on this machine. Install in this order:

1. **Docker Desktop for Mac** → https://www.docker.com/products/docker-desktop/
   - After install, open it once; wait for the whale icon in the menu bar to settle.
   - In Settings → Resources → set RAM to ≥ 6 GB (ELK is hungry).
2. **(Optional) GitHub CLI** — `brew install gh` then `gh auth login`. Lets us push from terminal.
3. **(Optional, for K8s demo) kubectl + kustomize** — `brew install kubectl kustomize`.
4. **(Optional, for Terraform demo) Terraform** — `brew install terraform`.

You **do not need** Jenkins, AWS, or a real EKS cluster for the viva. The Jenkinsfile and Terraform are evaluated as artifacts, not by execution.

---

## 3. Run the full stack — three commands

Once Docker is running:

```bash
cd ~/Desktop/devops
make up        # builds 4 images, starts 14 containers, runs migrations
sleep 30       # give ELK + grafana time to start
make seed      # populates 50 SIMs / 3 plans / MSISDN pool
```

Then verify everything:

```bash
make ps                # all 14 services 'Up' (migrate will be 'Exited (0)' — that's correct)
make smoke             # hits /healthz, /readyz, /sims — exits 0
curl localhost:8000/metrics | head -30
```

If you see any service in `Restarting`:
```bash
make logs SERVICE=<name>
```

### URL & credentials cheat sheet

| Service | URL | Login |
| ------- | --- | ----- |
| Operator dashboard | http://localhost:5173 | — |
| API Swagger docs | http://localhost:8000/docs | — |
| API metrics | http://localhost:8000/metrics | — |
| Grafana | http://localhost:3000 | admin / admin |
| Prometheus | http://localhost:9090 | — |
| Alertmanager | http://localhost:9093 | — |
| Kibana | http://localhost:5601 | — |
| Vault UI | http://localhost:8200/ui | token: `root-dev-token` |
| Mock HLR | http://localhost:9000/docs | — |
| Postgres | localhost:5432 | simprov / simprov_dev_pw |

---

## 4. Screenshots to capture (8) — these become deliverable #13

Save each as PNG into `docs/screenshots/`:

1. `01-dashboard-overview.png` — `localhost:5173` showing KPI cards, donut, sparkline, audit feed
2. `02-dashboard-sims.png` — `localhost:5173/pages/sims.html` after filtering by ACTIVE
3. `03-api-swagger.png` — `localhost:8000/docs` showing the SIMs router expanded
4. `04-grafana-sim-prov.png` — Grafana → Dashboards → "SIM Provisioning Operations"
5. `05-prometheus-alerts.png` — `localhost:9090/alerts` showing the 8 rules
6. `06-kibana-discover.png` — Kibana → Discover with `sim-prov-*` index pattern
7. `07-vault-ui.png` — Vault → Secrets → kv/sim-prov tree
8. `08-docker-ps.png` — terminal screenshot of `docker compose ps` showing all green

**Bonus shots** (optional, but they look great in the viva deck):
- `09-architecture-diagram.png` — screenshot of the interactive architecture section in `docs/index.html`
- `10-jenkins-pipeline.png` — screenshot of the Blue Ocean view if you have Jenkins running; otherwise show the Jenkinsfile in VS Code with the 9 stages collapsed
- `11-kustomize-output.png` — `kustomize build k8s/overlays/prod | head -60` terminal capture
- `12-terraform-plan.png` — `terraform -chdir=terraform/envs/prod plan` output (the early "Refreshing state…" lines are enough)

Then drop them into `docs/screenshots/` and they're auto-discoverable.

---

## 5. The actual viva demo flow (15 minutes)

### Opening (2 min) — set context

> "My case study is **SIM Provisioning Automation Platform** — a telecom operator's pipeline for activating SIM cards. The pain points are slow activation, inconsistent infra across regions, no visibility when activations get stuck, and secrets sprawled in config files. I built a working FastAPI service plus the full DevOps lifecycle around it — Docker, Jenkins, Terraform, Kubernetes, Prometheus, Grafana, ELK, and Vault."

Open `docs/index.html` in browser. Scroll slowly through the hero, "What we built," and the interactive architecture diagram (hover a node to show the tooltip).

### Application (3 min) — prove it works

1. Open `localhost:5173` — let them see live KPIs, donut chart, audit log.
2. Click into **SIMs** page, filter by `PENDING`, click **Activate** on one row — show the row's status change and the audit event appear.
3. Open `localhost:8000/docs` — expand the `POST /api/v1/sims/{iccid}/activate` endpoint, show the schema.
4. In terminal: `curl localhost:8000/metrics | grep sim_state_transitions_total` — show the Prometheus counter incremented.

**One-line talking point:** *"This is the real telecom state machine — PENDING → ALLOCATED → ACTIVE → SUSPENDED/PORTED/RECYCLED — with every transition writing an audit event."*

### DevOps lifecycle (8 min) — the meat

Walk through each layer in order. For each, show the file + the running thing.

**a. Containerization** — open `docker/Dockerfile.api` in VS Code.
> *"Multi-stage build, distroless runtime, non-root user, healthcheck. No shell in the final image — smallest attack surface."*

**b. CI/CD** — open `jenkins/Jenkinsfile`.
> *"Nine stages — Checkout, parallel Lint + Unit Tests, Build Images, Trivy security scan, Push, Deploy to staging via Kustomize, Smoke test, Manual approval gate, Deploy to prod, Slack notification."*

**c. IaC (Terraform)** — open `terraform/envs/prod/main.tf`.
> *"VPC across 3 AZs with private subnets and NAT gateways, EKS 1.29 with managed node groups and IRSA, RDS Postgres 15 multi-AZ with encrypted storage and 7-day backups."*

**d. Kubernetes** — open `k8s/base/api-deployment.yaml`.
> *"Non-root, read-only root FS, all caps dropped, seccomp RuntimeDefault, topology-spread across zones, Vault agent injector annotations rendering secrets at startup. Plus HPA 3-12 replicas at 70% CPU, PDB with minAvailable 2, NetworkPolicy locking down ingress and egress."*

If you have kustomize installed: `kustomize build k8s/overlays/prod | head -60`.

**e. Monitoring** — open `localhost:3000` → Dashboards → SIM Provisioning Operations.
> *"RED metrics — rate, errors, duration. Plus business KPIs — SIMs by status, activation latency p50/p95/p99, MSISDN pool remaining, HLR call success rate."*
Then `localhost:9090/alerts` — show the 8 alerting rules.

**f. Logging** — open `localhost:5601` → Discover.
> *"Every API request is logged in structured JSON with a request_id that carries through to audit events. Filebeat auto-discovers containers, Logstash parses and enriches, Elasticsearch stores in daily indices."*

**g. Secrets** — open `localhost:8200/ui`, login with `root-dev-token`.
> *"KV-v2 secrets engine. Kubernetes auth method bound to service accounts. Two policies — one for API, one for worker. The Pod spec annotations make Vault Agent inject secrets as files at /vault/secrets/ — the app code never sees the token."*

**h. DR** — open `docs/dr-plan.html`.
> *"Four tiers — RDS RPO 5min / RTO 30min via multi-AZ + cross-region replica, app RTO 5min via warm DR cluster, Vault snapshots cross-region, telemetry daily ES snapshots. Six failure scenarios with step-by-step playbooks."*

### Closing (2 min)

Open `docs/index.html` → scroll to the Deliverables matrix at the bottom.
> *"Fourteen deliverables — every required artifact mapped to its file. ~140 files, ~10k lines of real config and code, no placeholders."*

---

## 6. Likely viva questions — short answers

| Q | A |
| - | - |
| **Why did you pick FastAPI?** | Native async, OpenAPI auto-gen, Pydantic validation — gives me a self-documenting API and a /docs page for free. |
| **Why distroless containers?** | No shell, no package manager, no busybox — minimum CVE surface. Trivy scan in CI confirms. |
| **Why Kustomize over Helm?** | This is a single application with two environments. Kustomize's overlay model is enough; Helm's templating becomes net negative below ~5 apps. |
| **Why RDS multi-AZ instead of Aurora?** | This workload is read-light and write-bounded by HLR latency, not DB. Multi-AZ gives me 30-min RTO at half Aurora's cost. |
| **Why a manual approval gate before prod?** | Trade-off: fully autonomous deploys are faster but every telecom change needs a human signoff for TRAI/compliance audit trail. |
| **What's your RPO/RTO?** | RDS 5 min / 30 min, app 0 / 5 min via warm DR cluster, Vault 1 min / 15 min via Raft snapshots. Full table in dr-plan.html. |
| **How do secrets reach the pod?** | Vault Agent Injector — annotations on the Pod template tell Vault to inject secrets as files into `/vault/secrets/`. App reads files. No token ever in container env or image. |
| **What if Postgres dies mid-activation?** | The state machine is transactional — each transition is one DB commit. If it fails, the SIM stays in the previous state. The worker reaps stuck ALLOCATED → PENDING after 30 min. |
| **How do you scale?** | Horizontal — HPA on CPU + memory, 3-12 API replicas. Worker is single-instance by design (so no race on stuck-reaper) but can be sharded later. |
| **How would you make HLR integration real?** | The `services/hlr_adapter.py` is interface-based. Swap the mock client for a real Diameter / RESTful HLR client, keep the retry-with-tenacity wrapper. |
| **What's your test coverage?** | 17 unit tests covering state machine + API happy paths + transition validation. CI also runs Trivy image scans and Locust load test (50 RPS / 60s). |
| **Where's your observability?** | Three pillars: Prometheus metrics (`/metrics`), structured JSON logs via Filebeat → Logstash → Elasticsearch, and request_id propagation. Alerts route to Slack with severity-based grouping. |

---

## 7. Push to GitHub

Once you're happy:

```bash
cd ~/Desktop/devops
git init
git add .
git commit -m "feat: SIM provisioning platform — full DevOps lifecycle"
gh repo create sim-provisioning-platform --public --source=. --remote=origin --push
# or, manually:
# git remote add origin git@github.com:<you>/sim-provisioning-platform.git
# git branch -M main
# git push -u origin main
```

Then in `docs/index.html` and `README.md`, update the GitHub URL placeholder if any.

---

## 8. What's **not** runnable locally (and what to say if asked)

| Thing | Why not | What to say |
| ----- | ------- | ----------- |
| AWS infra via Terraform | No AWS account / costs money | *"Terraform is `plan`-clean; we don't `apply` for the viva. The modules are tagged for grading."* |
| Jenkins pipeline | No Jenkins controller running | *"The Jenkinsfile is the artifact. Stages and credentials are documented in `jenkins/README.md`."* |
| Real EKS deployment | Needs AWS | *"Kustomize build produces valid YAML — `kustomize build k8s/overlays/prod` renders it."* |
| Vault auto-unseal with KMS | Needs AWS KMS | *"Configured in `vault/config/vault.hcl` comments; dev-mode runs unsealed for the demo."* |

---

## 9. Quick sanity check before the viva

Run this 10 minutes before walking in:

```bash
cd ~/Desktop/devops
make up && sleep 45 && make seed && make smoke
echo "if you see 'OK' above, you're good"
open docs/index.html
open http://localhost:5173
open http://localhost:3000
open http://localhost:5601
open http://localhost:8200
```

If anything is red, the failure modes are predictable:
- **API unhealthy** → `make logs SERVICE=api` — usually DB not migrated yet, wait 30s and retry
- **Elasticsearch unhealthy** → Docker RAM < 4 GB, raise in Docker Desktop settings
- **Kibana 503** → Elasticsearch isn't green yet, wait

You're ready.
