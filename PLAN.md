# SIM Provisioning Automation Platform — Master Plan

**Case Study 20 · ITM Skills University · B.Tech CSE 2024-28 · DevOps Sem IV**
**Owner:** Sayuj · **Repo:** `~/Desktop/devops`

---

## 1. Problem framing

Telecom operators provision millions of SIM cards per day. Manual or legacy provisioning pipelines suffer from:

| Pain point                       | Production impact                              |
| -------------------------------- | ---------------------------------------------- |
| Slow activation (hours-days)     | Customer churn at point-of-sale                |
| Inconsistent infra across rings  | Cannot ship region-specific compliance changes |
| Fragmented monitoring            | MTTR > 1 hour for stuck activations            |
| Secrets in config files          | Audit failures (TRAI / GDPR)                   |
| No automated DR                  | RTO measured in days                           |

**Our deliverable** is a production-shaped, IaC-driven SIM Provisioning Automation Platform with a working web application, full DevOps lifecycle, and a polished documentation site.

---

## 2. Scope — what we build

### 2.1 Business application (the "thing being DevOps'd")

A SIM Provisioning service with:

- **REST API** (FastAPI) — activate / suspend / port / query / bulk-provision endpoints
- **Worker** — async state-machine moving SIMs through `PENDING → ALLOCATED → ACTIVE → SUSPENDED → PORTED`
- **PostgreSQL** persistence (SIM inventory, MSISDN pool, audit log)
- **Web dashboard** (vanilla HTML + Tailwind + vanilla JS, no build step) — operator console showing SIM inventory, live activation feed, KPIs, audit log
- **Mock HLR/HSS adapter** so we demonstrate integration without telco hardware

### 2.2 DevOps lifecycle (the deliverable matrix)

| Layer            | Tooling                                       | File(s)                              |
| ---------------- | --------------------------------------------- | ------------------------------------ |
| Source control   | GitHub + branch protection + PR template      | `.github/`                           |
| Containerization | Multi-stage Dockerfile (distroless runtime)   | `docker/`                            |
| CI/CD            | Jenkins declarative pipeline + GH Actions     | `jenkins/Jenkinsfile`, `.github/workflows/ci.yml` |
| IaC              | Terraform — VPC, EKS, RDS, S3, IAM, ALB       | `terraform/`                         |
| Orchestration    | Kubernetes — Deployment, Service, Ingress, HPA, PDB, NetworkPolicy | `k8s/`            |
| Monitoring       | Prometheus + Grafana + Alertmanager           | `monitoring/`                        |
| Logging          | ELK (Elasticsearch + Logstash + Kibana) + Filebeat | `logging/`                      |
| Secrets          | HashiCorp Vault + Vault Agent Injector        | `vault/`                             |
| Docs             | Static HTML "command center" site             | `docs/`                              |

### 2.3 Required artifacts (from college brief, mapped)

- [x] Working Application → `app/`
- [x] Source Code Repo → this repo
- [x] Dockerfile + Images → `docker/Dockerfile.api`, `docker/Dockerfile.worker`
- [x] Jenkins CI/CD → `jenkins/Jenkinsfile`
- [x] Terraform → `terraform/`
- [x] Kubernetes → `k8s/`
- [x] Prometheus + Grafana → `monitoring/`
- [x] ELK → `logging/`
- [x] Vault → `vault/`
- [x] Architecture Diagram → `docs/diagrams/architecture.svg`
- [x] Deployment Diagram → `docs/diagrams/deployment.svg`
- [x] Disaster Recovery Plan → `docs/dr-plan.html`
- [x] Demonstration Screenshots → `docs/screenshots/`
- [x] Project Documentation → `docs/index.html` (the "sexy docs")

---

## 3. Architecture

```
                                    ┌─────────────────────┐
                                    │   Operator Browser  │
                                    └──────────┬──────────┘
                                               │ HTTPS
                                    ┌──────────▼──────────┐
                                    │   AWS ALB (Ingress) │
                                    └──────────┬──────────┘
                                               │
                          ┌────────────────────┼────────────────────┐
                          │                    │                    │
                  ┌───────▼───────┐    ┌───────▼───────┐    ┌───────▼───────┐
                  │  Web (HTML)   │    │  API (FastAPI)│    │ Worker (FastAPI│
                  │  Pod ×2       │    │  Pod ×3 (HPA) │    │  state machine)│
                  └───────────────┘    └───────┬───────┘    └───────┬───────┘
                                               │                    │
                                  ┌────────────┴──────┐  ┌──────────┘
                                  │                   │  │
                          ┌───────▼─────┐   ┌─────────▼──▼──┐   ┌──────────────┐
                          │   Vault     │   │  PostgreSQL    │   │ Mock HLR/HSS │
                          │ (secrets)   │   │  (AWS RDS)     │   │  (sidecar)   │
                          └─────────────┘   └────────────────┘   └──────────────┘
                                               │
                                  ┌────────────┴────────────┐
                                  │   Observability plane    │
                                  │  Prometheus / Grafana    │
                                  │  Elasticsearch / Kibana  │
                                  │  Logstash / Filebeat     │
                                  │  Alertmanager → Slack    │
                                  └─────────────────────────┘
```

---

## 4. SIM provisioning domain model

```
SIM
 ├── iccid          (19 digits, primary key)
 ├── imsi           (15 digits)
 ├── msisdn         (E.164, nullable until activated)
 ├── status         (PENDING|ALLOCATED|ACTIVE|SUSPENDED|PORTED|RECYCLED)
 ├── plan_id        (FK → Plan)
 ├── activated_at   (timestamp)
 └── audit_events[] (event-sourced)

Plan
 ├── id, name, data_gb, voice_min, sms_count, monthly_inr
```

State machine:

```
PENDING ──allocate──▶ ALLOCATED ──activate──▶ ACTIVE
                                   │             │
                                   │             ├──suspend──▶ SUSPENDED ──resume──▶ ACTIVE
                                   │             └──port_out─▶ PORTED
                                   └──recycle──▶ RECYCLED
```

---

## 5. Disaster Recovery (summary, full HTML version in `docs/dr-plan.html`)

| Tier            | RPO  | RTO  | Mechanism                                       |
| --------------- | ---- | ---- | ----------------------------------------------- |
| RDS (Postgres)  | 5 m  | 30 m | Multi-AZ + cross-region read replica + PITR     |
| Application     | 0    | 5 m  | EKS multi-AZ + HPA + warm DR cluster (Pilot Light) |
| Secrets (Vault) | 1 m  | 15 m | Raft snapshots → S3 cross-region                |
| Telemetry       | 15 m | 1 h  | Daily Elasticsearch snapshots to S3             |

Game-day playbook ships in `docs/dr-plan.html`.

---

## 6. Build phases (execution order)

| Phase | Output                                            | Status |
| ----- | ------------------------------------------------- | ------ |
| 0     | Plan + directory scaffold                         | ✅     |
| 1     | FastAPI backend + Postgres model + seed data      | ⏳     |
| 2     | HTML operator dashboard                           | ⏳     |
| 3     | Docker + docker-compose (local stack)             | ⏳     |
| 4     | Jenkinsfile + GitHub Actions                      | ⏳     |
| 5     | Terraform (VPC, EKS, RDS)                         | ⏳     |
| 6     | Kubernetes manifests + Kustomize overlays         | ⏳     |
| 7     | Prometheus + Grafana dashboards                   | ⏳     |
| 8     | ELK stack + Filebeat                              | ⏳     |
| 9     | Vault config + policies                           | ⏳     |
| 10    | "Sexy docs" HTML site                             | ⏳     |
| 11    | Diagrams + DR plan + screenshots                  | ⏳     |

---

## 7. Quality bar (what "overkill but not slow" means)

- Every file is real, runnable, and would not embarrass a junior SRE.
- No placeholder code, no `# TODO` stubs in production paths.
- Multi-stage Dockerfiles, non-root containers, healthchecks.
- Terraform with remote state stub, tagged resources, security groups.
- K8s: resource limits, liveness/readiness, PDBs, HPAs, NetworkPolicies.
- Monitoring: RED/USE metrics, recording rules, named SLOs.
- Docs: dark-mode operator-grade UI, not a Bootstrap default.

---

## 8. Out of scope (declared intentionally)

- Real HLR/HSS integration (we mock it; calling out the seam in docs).
- Live AWS deployment (Terraform is `terraform plan`-clean, not applied).
- Real Vault unsealing with KMS (we configure the policies + show the flow).
- End-to-end load test (we provide the locustfile and one demo run).
