# THE VIVA BIBLE — SIM Provisioning Automation Platform

> Everything in this document, in your own words, calm voice, no rushing. If you understand the *why* behind a tool, you can never be cornered on the *what*.

---

## THE 60-SECOND PITCH (memorise this)

> *"My case study is a SIM Provisioning Automation Platform — a real telecom-operator pipeline for activating SIM cards. The pain points I solved are slow activations, inconsistent infra across regions, no visibility when activations get stuck, and secrets sprawled in config files. I built a working FastAPI service with the actual telecom state machine — `PENDING → ALLOCATED → ACTIVE → SUSPENDED / PORTED / RECYCLED` — and around it the full DevOps lifecycle: Docker for packaging, Jenkins for CI/CD, Terraform for cloud infrastructure, Kubernetes for orchestration, Prometheus + Grafana for metrics, ELK for logs, and Vault for secrets. Every transition writes an audit event; every layer has a screenshot in my deck proving it works."*

That's your opening. Land it cleanly, and 40 % of the viva is already over.

---

## THE PROBLEM (why this project exists at all)

A telecom operator activates SIM cards by the millions. Each card has to go through a lifecycle: stock → assigned to a customer → activated on the network → eventually suspended or recycled. In reality this involves a database, a Home Location Register (HLR — the telecom network's identity database), a number pool (MSISDNs = phone numbers), and several teams.

**The four pain points I quote in the viva:**
1. **Slow activations** — minutes per card, costing operator revenue.
2. **Inconsistent infrastructure** — every regional data centre runs a slightly different copy. When something breaks in Bangalore, the Mumbai fix doesn't apply.
3. **Zero visibility** — operators don't know *where* a stuck activation is stuck.
4. **Secrets sprawl** — DB passwords, HLR API keys, JWT signing material spread across config files, .env files, sometimes even checked into git.

The whole project is the answer to those four problems.

---

## THE DOMAIN — the SIM state machine

This is the actual business model. Memorise the transitions.

```
PENDING ─── allocate ──▶ ALLOCATED ─── activate ──▶ ACTIVE
                                                      │
                              ┌──────── suspend ──────┤
                              ▼                       │
                          SUSPENDED ── resume ────────┘
                              │
                              │  port_out
                              ▼
                          PORTED
                              │
                              │  recycle
                              ▼
                          RECYCLED
```

- **PENDING** — the SIM is in stock; no customer assigned.
- **ALLOCATED** — assigned to a plan + customer; not yet usable on the network.
- **ACTIVE** — provisioned in the HLR, has an MSISDN (phone number), works.
- **SUSPENDED** — temporarily disabled (non-payment, fraud).
- **PORTED** — number ported out to another operator.
- **RECYCLED** — sat unused long enough; goes back into the pool.

**Every transition writes an audit event.** That's the immutable log of what happened to every card — for compliance, for debugging.

---

## PART 1 — THE APPLICATION (what actually runs)

### 1.1 FastAPI

**What it is:** Python web framework. Like Flask but modern — built on `Starlette` + `Pydantic`. Async by default. Auto-generates OpenAPI / Swagger from your type hints.

**Why we use it:** Speed (async I/O), free OpenAPI docs at `/docs`, request/response validation comes for free with type hints, ecosystem fit (asyncpg, structlog, prometheus_client all integrate cleanly).

**Where you see it:** `localhost:8000/docs` — that's the Swagger UI auto-generated from the code. Every endpoint, every schema, every status code is discoverable.

### 1.2 uvicorn

**What it is:** The actual server that runs FastAPI. FastAPI is the framework (decides what to do per request); uvicorn is the engine that listens on port 8000, accepts TCP connections, and hands requests to FastAPI.

**Workers:** We run with **2 uvicorn workers** — two processes each handling requests independently. In production you'd run more, sized to CPU.

### 1.3 SQLAlchemy (async) + asyncpg

**SQLAlchemy** is the ORM (Object Relational Mapper) — Python classes map to SQL tables. We use the async variant so DB calls don't block the event loop.

**asyncpg** is the actual async PostgreSQL driver.

**Why async?** A SIM activation makes 2-3 DB calls + 1 HLR call. Async means while we're waiting for one I/O, the worker can serve another request. Without async, 2 workers can serve maybe 50 req/s; with async, the same 2 workers handle 500+.

### 1.4 The Worker (async tick loop, 5s cadence)

**What it does:** Every 5 seconds, polls the DB for SIMs in ALLOCATED state. For each, calls the mock HLR API (`POST /hlr/provision`), and if the HLR returns success, transitions the SIM to ACTIVE.

**Why a worker (and not just inline in the API)?** Because the HLR call is slow and unreliable in real life. If a customer hits "Activate" and the HLR is having a bad day, we don't want their browser hanging for 30 seconds. So the API just sets state to ALLOCATED and returns; the worker does the heavy lifting asynchronously.

This is **the classic async-job pattern** — also called "outbox", "task queue", or "reconciliation loop".

### 1.5 Postgres

**What it is:** A relational database (SQL).

**Why Postgres specifically (not MySQL)?**
- Strong support for enums (we use `SimStatus` as a Postgres enum).
- JSONB columns (useful for audit metadata).
- ACID transactions — critical for state machine correctness.
- Row-level locking for the MSISDN pool allocation.

**Tables we have:**
- `plans` — what data/voice/SMS bundle each SIM is on.
- `sims` — the SIMs themselves, indexed by status and `last_transition_at`.
- `msisdn_pool` — pool of phone numbers ready to allocate.
- `audit_events` — immutable log of every state change.
- `alembic_version` — schema version tracking (see Alembic below).

### 1.6 Alembic

**What it is:** Database migration tool for SQLAlchemy. Like git for your schema.

**Why:** You can't just edit your `models.py` and hope production catches up. Migrations let you upgrade/downgrade schema with versioned scripts.

**Where:** `app/backend/app/migrations/`. The `migrate` service in compose runs `alembic upgrade head` before the API starts.

### 1.7 The Mock HLR

**What it is:** A separate FastAPI service running on port 9000 that pretends to be a telecom HLR.

**Why we mocked it:** Real HLRs are operator-internal hardware (Ericsson, Nokia). We can't talk to one in college. The mock returns a fake `provisioning_ref` and occasionally simulates failures so our HLR-success-rate metric is interesting.

### 1.8 The Frontend (Operator Console)

**Stack:** Vite + vanilla JavaScript + Chart.js for the donut.

**Why vanilla, not React?** A: To keep the demo small and reviewable. B: I wanted to prove I can build a UI without a 200 MB node_modules.

**What it shows:** KPI cards (active SIMs, 24h activations, pending queue, mean activation latency), a 24h activation series, MSISDN pool gauge, inventory donut, real-time audit log polling every second.

### 1.9 structlog

**What it is:** A structured logging library. Every log line is JSON.

**Why JSON logs:** Because Logstash and Elasticsearch can index them by field. `level`, `event`, `request_id`, `iccid`, `duration_ms` — all queryable in Kibana.

**The request_id trick:** A middleware assigns a UUID to every incoming request, propagates it through context, and includes it in every log line. So when something goes wrong, you grep one request_id and see every step.

---

## PART 2 — CONTAINERIZATION

### 2.1 What is a Docker image?

> **An image is a frozen, layered filesystem + a default command to run.** It is *not* a virtual machine. There is no kernel inside it.

Think of an image as a stack of read-only `.tar` files (layers), plus a tiny manifest saying "when you run this, execute `/usr/bin/python /app/main.py` as user `app`".

### 2.2 What is a container?

> **A container is a running instance of an image** — a process (or process tree) running on the host kernel, but isolated using Linux namespaces (PID, network, mount, etc.) and limited using cgroups.

**Key fact for the viva:** Containers share the host's kernel. They're not VMs. That's why they boot in milliseconds and a Docker image is tens of MB, not gigabytes.

### 2.3 Image vs Container

| Image | Container |
|-------|-----------|
| Static, on disk | Running, in memory |
| Like a class | Like an instance |
| Built once, run many times | One process tree, ephemeral |
| Identified by SHA digest | Identified by PID + container ID |

### 2.4 Layers

Every line in a Dockerfile that *changes the filesystem* creates a new layer. Layers are cached. If you change one line near the bottom of the Dockerfile, only that layer and below rebuild — that's why our API rebuilds in 5 seconds even though the base image is huge.

**Example layer order in our `Dockerfile.api`:**
1. `FROM python:3.11-slim` — the base layer.
2. `RUN apt-get install libpq5 curl` — system deps (rarely change, top of cache).
3. `COPY requirements.txt . && pip install` — Python deps (changes when you bump a library).
4. `COPY app/ .` — your actual code (changes every commit — bottom of cache).

If you reverse step 3 and 4, every code change reinstalls all your pip packages. That's a rookie mistake.

### 2.5 Multi-stage build

**Concept:** You build in one stage (with compilers, build tools), then *copy* only the output into a smaller runtime stage.

```dockerfile
FROM python:3.11 AS builder
RUN pip install --target=/install <deps>

FROM python:3.11-slim AS runtime
COPY --from=builder /install /usr/local/lib/python3.11/site-packages
COPY app/ /app/
USER app
CMD ["uvicorn", "app.main:app"]
```

**Why:** The final image doesn't have gcc, make, or any of the compilers. Smaller, fewer CVEs, harder to escape from if compromised.

### 2.6 tini as PID 1

**Why:** In Linux, PID 1 has special responsibilities — handling signals, reaping zombie children. Python doesn't do this well. `tini` is a 30-line init that does. Without it, your container ignores `SIGTERM` (Docker stop) for 10 seconds before getting killed.

### 2.7 Non-root user

We create a user `app` with uid 1001 and `USER app` in the Dockerfile. **Why:** If your app is compromised (RCE via a Python deserialize bug), the attacker only has user-level access inside the container, not root. Combined with read-only filesystem in K8s, this is the second layer of defence.

### 2.8 Healthcheck

```dockerfile
HEALTHCHECK CMD curl -f http://localhost:8000/healthz || exit 1
```

Docker/K8s know *if your container is alive*. If healthcheck fails for X seconds, the orchestrator kills and restarts it.

We expose **`/healthz`** (liveness — is the process running?) and **`/readyz`** (readiness — can it serve traffic? hits the DB to confirm).

### 2.9 docker-compose

**What it is:** Declarative tool to define a multi-container stack in YAML (`docker-compose.yml`) and bring it up with one command.

**Why we use it:** Local dev. In prod, K8s does this; locally, compose. They're not competitors — they solve the same problem at different scales.

**Our 13 services:**
| Service | Port | Purpose |
|---------|------|---------|
| `api` | 8000 | FastAPI |
| `worker` | — | Background HLR provisioner |
| `postgres` | 5432 | Database |
| `mock-hlr` | 9000 | Fake HLR |
| `frontend` | 5173 | Operator dashboard |
| `vault` | 8200 | Secrets |
| `prometheus` | 9090 | Metrics scraping |
| `alertmanager` | 9093 | Alert routing |
| `grafana` | 3001 | Dashboards |
| `elasticsearch` | 9200 | Log store |
| `logstash` | 5044 | Log processor |
| `kibana` | 5601 | Log UI |
| `filebeat` | — | Log shipper |

---

## PART 3 — CI/CD with Jenkins

### 3.1 What is CI/CD?

- **CI (Continuous Integration)** — every push to git triggers automated build + test. Catches bugs early.
- **CD (Continuous Deployment / Delivery)** — every passing build can be deployed automatically (or with one click).

### 3.2 What is Jenkins?

Open-source automation server. Reads a `Jenkinsfile` from your repo and executes the pipeline you've defined in Groovy.

### 3.3 The 9 stages (memorise the order)

1. **Checkout** — pull code from git (~4s).
2. **Lint** — `ruff check` for Python style/bug-finding (~18s). Runs in parallel with tests.
3. **Test** — `pytest` (~52s).
4. **Build** — `docker build` of the API + worker images (~1m 12s).
5. **Scan** — `trivy image` scans for CVEs (~34s). Fails the build on HIGH/CRITICAL.
6. **Push** — to ECR (Amazon's image registry).
7. **Stage Deploy** — `kustomize build k8s/overlays/staging | kubectl apply -f -`.
8. **Manual Approval** — Jenkins pauses, asks a human. Required for prod.
9. **Prod Deploy + Slack** — `kustomize build k8s/overlays/prod | kubectl apply -f -`, then Slack message.

### 3.4 Why each stage matters

- **Lint** — catches dead code, unused imports, typos. Cheap and fast.
- **Trivy scan** — catches `python:3.11-slim` with a known CVE in `libpq` before it ships. **This is the security gate.**
- **Manual approval before prod** — humans should always sign off on production deploys. It's not a bottleneck, it's a checkpoint.

### 3.5 Kustomize (not Helm)

**Kustomize** layers YAML on top of YAML — base manifests + per-env overlays. No templating language (unlike Helm). Built into `kubectl` since 1.14.

```
k8s/
├── base/             # common to all envs
└── overlays/
    ├── staging/      # staging overrides
    └── prod/         # prod overrides
```

`kustomize build k8s/overlays/prod` produces the final manifest for prod.

---

## PART 4 — IaC (Infrastructure as Code) with Terraform

### 4.1 What is IaC?

> Infrastructure defined in version-controlled text files, not by clicking buttons in the AWS console.

**Why:** Reproducibility, peer review, rollback, drift detection.

### 4.2 What is Terraform?

A tool from HashiCorp. You write `.tf` files describing what you want (VPC, EKS cluster, RDS database). You run `terraform plan` to see what will change, then `terraform apply` to make it real.

### 4.3 The Terraform State File

Terraform keeps a JSON file (`terraform.tfstate`) mapping your `.tf` resources to real AWS resource IDs. **This is the most important file in Terraform.** If you lose it, Terraform doesn't know which AWS resources it created.

**Best practice:** Store it in S3 with versioning + DynamoDB lock. Never check it into git.

### 4.4 What we provision (production target)

```hcl
module "vpc"    { azs = 3   cidr = "10.20.0.0/16" }
module "eks"    { version = "1.29"  irsa = true }
module "rds_pg" { multi_az = true   backup_retention = 7 }
```

- **VPC across 3 AZs (Availability Zones)** — even if a whole AWS data centre dies, 2 AZs survive.
- **Private subnets + NAT gateway** — pods can reach the internet, but the internet can't reach pods directly.
- **EKS 1.29 with IRSA** — IRSA = IAM Roles for Service Accounts. Lets a K8s pod assume an AWS IAM role without storing AWS keys.
- **Managed node groups** — AWS handles the EC2 instances under the K8s nodes.
- **RDS Postgres 15 multi-AZ** — standby in another AZ; automatic failover on master death; 7-day backups; encrypted storage.

### 4.5 The classic Terraform commands

| Command | What it does |
|---------|--------------|
| `terraform init` | Download provider plugins, set up state backend. |
| `terraform plan` | Show diff between desired (`.tf`) and current (state). |
| `terraform apply` | Make the changes. |
| `terraform destroy` | Tear it all down. |

---

## PART 5 — KUBERNETES (the deep one — be ready for grilling)

### 5.1 Why K8s exists

Docker tells you *how* to package one process. K8s tells you *how to run hundreds of those across a fleet of machines reliably*. Self-healing, autoscaling, rolling updates, service discovery, secret injection.

### 5.2 The 5 objects you MUST know

#### Pod
The smallest deployable unit. One or more containers sharing network + storage. Almost always you run **one main container per pod** plus maybe a sidecar.

#### Deployment
Manages a set of identical pods (a `ReplicaSet`). You declare "I want 3 replicas of this pod template"; the Deployment makes it true. Rolling updates: it kills old pods one at a time, replacing with new ones.

#### Service
A stable network address (DNS name + ClusterIP) that load-balances across pods. Pods come and go (their IPs change); the Service stays.
- **ClusterIP** (default) — internal only.
- **NodePort** — exposes on each node's IP.
- **LoadBalancer** — provisions a cloud load balancer.

#### Ingress
HTTP/HTTPS routing on top of Services. `*.sim-prov.example.com` → routed to the right Service. Managed by an Ingress Controller (we'd use nginx-ingress or AWS ALB).

#### ConfigMap / Secret
Key-value stores mounted into pods. ConfigMaps for plaintext config; Secrets for credentials (base64-encoded, encrypted at rest in etcd).

### 5.3 Our hardened pod spec — every line is intentional

```yaml
securityContext:
  runAsNonRoot: true            # block running as root
  runAsUser: 1001
  readOnlyRootFilesystem: true  # block writes to / (except mounted volumes)
  allowPrivilegeEscalation: false
  capabilities:
    drop: ["ALL"]               # drop every Linux capability
  seccompProfile:
    type: RuntimeDefault        # block dangerous syscalls
```

**Why each line:**
- `runAsNonRoot` — even if container build forgets `USER app`, K8s blocks root.
- `readOnlyRootFilesystem` — attacker can't write a webshell.
- `drop ALL caps` — no `CAP_NET_RAW`, no `CAP_SYS_ADMIN`, nothing.
- `seccomp RuntimeDefault` — kernel-level syscall filter.

### 5.4 HPA — Horizontal Pod Autoscaler

```yaml
minReplicas: 3
maxReplicas: 12
targetCPUUtilizationPercentage: 70
```

K8s metrics-server measures pod CPU. If average crosses 70%, HPA adds pods (up to 12). When traffic drops, scales back down. **Horizontal** = more pods (not bigger pods — that's VPA).

### 5.5 PDB — Pod Disruption Budget

```yaml
minAvailable: 2
```

When a node has to be drained (e.g., AWS upgrade), K8s respects: "always keep at least 2 pods of this app running, even if you have to wait."

### 5.6 NetworkPolicy

> Default in K8s: every pod can talk to every pod.

NetworkPolicy locks that down. We say: "API pod accepts ingress only from frontend + ingress controller; egresses only to Postgres + Vault + mock-hlr."

### 5.7 IRSA — IAM Roles for Service Accounts

The clean way to give K8s pods AWS permissions. Instead of stuffing AWS keys into env vars, you:
1. Create an IAM role with a trust policy that says "this OIDC subject can assume me."
2. Annotate the K8s ServiceAccount with that role ARN.
3. Pods using that ServiceAccount get temporary AWS creds via the IMDS endpoint.

**Why elite:** zero long-lived credentials. Rotation is automatic.

### 5.8 Vault Agent Injector

A K8s mutating webhook from HashiCorp. You annotate your pod with `vault.hashicorp.com/agent-inject: "true"` and it:
1. Injects a sidecar container running `vault agent`.
2. The agent authenticates to Vault (via K8s ServiceAccount JWT).
3. Reads `secret/sim-prov/db` and writes it as a file in a shared `tmpfs` volume.
4. Your app reads the file at startup.

**Result:** secrets never appear in env vars, never in `kubectl describe pod`, never in logs.

---

## PART 6 — OBSERVABILITY (the three pillars)

> *"You can't fix what you can't see."*

Observability has three pillars: **metrics, logs, traces.** We do the first two. Traces (Jaeger / Tempo) are listed as out of scope.

### 6.1 Metrics — Prometheus

#### What is Prometheus?
A time-series database + scraper. It **pulls** metrics over HTTP at a regular interval (every 15s by default) from `/metrics` endpoints. Data is stored locally with a labelset + timestamp + float value.

#### Why pull (not push)?
- Discovery — Prometheus knows what's *meant* to exist; if a target is missing, that's an alert (`up == 0`).
- Easier ops — you don't need apps to know about Prometheus.

#### The 4 metric types

| Type | What it is | Example |
|------|-----------|---------|
| **Counter** | Only ever goes up (or resets to 0 on restart) | `sim_state_transitions_total` |
| **Gauge** | Goes up or down — instantaneous value | `msisdn_pool_remaining` |
| **Histogram** | Bucketed counts of observations | `sim_activation_latency_seconds` |
| **Summary** | Like histogram but client-side quantiles (don't aggregate well across instances) | rare |

#### Histograms and percentiles
A histogram stores counts per bucket: "how many observations were < 0.05s, < 0.1s, < 0.25s, ... < 30s". Prometheus computes p50/p95/p99 via `histogram_quantile()`. **Critical to remember:** percentiles cannot be averaged. You must aggregate the *buckets*, then compute the quantile. Our recording rules do exactly this:

```promql
sim:activation_latency_seconds:p95 =
  histogram_quantile(0.95, sum by (le) (rate(sim_activation_latency_seconds_bucket[5m])))
```

#### Recording rules
A recording rule is a pre-computed query stored as its own metric. Why? Two reasons:
1. Dashboards become faster (you query the pre-computed series, not the raw one).
2. Long alert queries become readable.

Naming convention: `<namespace>:<metric>:<aggregation>` — like `sim:hlr_call_success_rate:5m`.

#### Alert rules
A PromQL expression that, when truthy for a `for:` duration, fires an alert.

```yaml
- alert: HighActivationLatency
  expr: sim:activation_latency_seconds:p95 > 5
  for: 15m
  labels: { severity: warning }
  annotations: { summary: "p95 > 5s for 15m" }
```

Our 8 rules:
| Rule | Fires when | Sev |
|------|-----------|------|
| HighErrorRate | 5xx ratio > 5% for 10m | critical |
| HighActivationLatency | p95 > 5s for 15m | warning |
| MsisdnPoolLow | remaining < 1000 | warning |
| MsisdnPoolExhausted | remaining < 100 | critical |
| DBDown | `pg_up == 0` for 2m | critical |
| PodCrashLooping | restart rate > 0 for 10m | warning |
| CertExpiringSoon | < 14 days remaining | warning |
| HlrCallFailureRateHigh | HLR success < 95% for 10m | warning |

### 6.2 Alertmanager
Prometheus *fires* alerts; Alertmanager *routes* them. It deduplicates, groups, silences, and forwards to PagerDuty / Slack / email. Without Alertmanager, every flapping alert would page on-call 200 times in 5 minutes.

### 6.3 Grafana
Visualisation. Queries Prometheus (or any datasource), renders panels.

**Our dashboard "SIM Provisioning Operations" has 10 panels:**
1. SIMs by status (stat)
2. SIM status distribution (donut)
3. MSISDN pool remaining (gauge)
4. Activation rate (timeseries, req/s)
5. Activation latency p50/p95/p99
6. HLR call success rate (5m stat)
7. State transitions (5m rate)
8. API CPU
9. API resident memory
10. Recent alerts (table)

#### RED metrics
A famous SRE shorthand for *what* to monitor in a service:
- **Rate** — requests per second
- **Errors** — failed requests per second
- **Duration** — latency distribution

Plus **business KPIs** layered on top — pool remaining, status counts, HLR success.

### 6.4 Logs — the ELK stack

**E**lasticsearch + **L**ogstash + **K**ibana + (Filebeat, the 'F' that should make it 'FELK').

#### The pipeline
```
App stdout (structlog JSON) → Docker logs
    → Filebeat (autodiscover, tails container logs)
    → Logstash (parse + enrich + drop noise)
    → Elasticsearch (index "sim-prov-2026.06.21")
    → Kibana (search UI)
```

#### Each tool, one line
- **Filebeat** — log shipper. Tails files, ships to Logstash. Very light Go binary.
- **Logstash** — parser/transformer. We have it: parse JSON message into fields, drop `/healthz` noise, rename container labels to `service`.
- **Elasticsearch** — distributed search index. Stores logs as JSON documents in indices (we use one per day: `sim-prov-2026.06.21`).
- **Kibana** — the UI. `localhost:5601/app/discover`.

#### Indexing pattern
- One index per day so older indices can be deleted cheaply (storage management).
- Fields like `level`, `logger`, `service`, `event`, `request_id` are searchable.
- KQL (Kibana Query Language): `level: ERROR AND service: "sim-prov-api"`.

---

## PART 7 — SECRETS WITH VAULT

### 7.1 What is HashiCorp Vault?

A secrets store. Speaks HTTP API. Supports multiple "secret engines" (kv, AWS dynamic creds, database creds with rotation, transit encryption-as-a-service).

### 7.2 KV v2 secret engine

The basic engine — you write `secret/sim-prov/db` and later read it back. v2 supports versioning so you can roll back to a previous value.

**Our tree:**
- `secret/sim-prov/db` — host, port, user, password, dbname.
- `secret/sim-prov/hlr` — endpoint, API key.
- `secret/sim-prov/jwt` — signing key, algorithm.
- `secret/sim-prov/audit-signing` — HMAC key for audit-event signing.

### 7.3 The dev token

`root-dev-token` — Vault running in `-dev` mode auto-unseals, gives you a root token. **Never in production.** In prod you unseal Vault with Shamir-shared keys held by 5 different humans, of whom 3 must consent to unseal.

### 7.4 Authentication methods (in production)
- **K8s auth** — pods authenticate using their ServiceAccount JWT.
- **AppRole** — for services outside K8s.
- **AWS IAM auth** — let an EC2 instance authenticate via its instance role.

### 7.5 Read pattern (what our API does at startup)
1. Read `VAULT_TOKEN` from env (in prod, this is rendered by Vault Agent — see §5.8).
2. Call `GET /v1/secret/data/sim-prov/db`.
3. Build SQLAlchemy DSN from the response.
4. Drop the token (never re-use it).

---

## PART 8 — URL CHEAT SHEET (have this open during the demo)

| URL | What it is | What you see |
|-----|-----------|--------------|
| `http://localhost:5173` | Operator dashboard | KPIs, donut, audit feed |
| `http://localhost:5173/pages/sims.html` | Inventory page | Filterable SIM table |
| `http://localhost:8000/docs` | FastAPI Swagger | All endpoints, schemas |
| `http://localhost:8000/metrics` | Prometheus scrape target | Raw Prometheus text format |
| `http://localhost:8000/healthz` | Liveness probe | `{"status":"ok"}` |
| `http://localhost:8000/readyz` | Readiness probe | Hits DB; `{"status":"ready"}` |
| `http://localhost:9000/docs` | Mock HLR Swagger | Provision/deprovision endpoints |
| `http://localhost:9090` | Prometheus UI | `/graph`, `/alerts`, `/targets` |
| `http://localhost:9090/alerts` | Alert rules | The 8 rules + their state |
| `http://localhost:9090/targets` | Scrape targets | Which jobs are up/down |
| `http://localhost:9093` | Alertmanager UI | Active + silenced alerts |
| `http://localhost:3001` | Grafana | login admin/admin |
| `http://localhost:3001/d/sim-prov-ops/...` | Our dashboard | 10 panels |
| `http://localhost:5601/app/discover` | Kibana Discover | Search logs |
| `http://localhost:8200/ui/` | Vault UI | login token `root-dev-token` |
| `http://localhost:9200/_cat/indices?v` | Elasticsearch API | List indices |
| `postgres://simprov:simprov_dev_pw@localhost:5432/simprov` | DB connection string | psql in |

---

## PART 9 — CONCEPT GLOSSARY (rapid-fire)

- **ACID** — Atomicity, Consistency, Isolation, Durability. The four properties of a sane transactional database.
- **Aurora-like cover gradient** — just CSS radial-gradients overlapping. No images.
- **AZ (Availability Zone)** — an isolated data centre within an AWS region. We deploy across 3.
- **Blue/green deployment** — run new version alongside old; switch traffic instantly. (Not what we do; we use rolling.)
- **Canary** — release new version to a small % of traffic first.
- **Cardinality** — the number of unique label combinations on a metric. High cardinality (e.g., per-user labels) kills Prometheus.
- **cgroup** — Linux feature limiting CPU/memory/IO per process group. How Docker enforces resource limits.
- **CSRF** — Cross-Site Request Forgery. Mitigated via SameSite cookies + CSRF tokens.
- **CVE** — Common Vulnerabilities & Exposures. Trivy scans for these.
- **DNS** — Domain Name System. K8s has internal DNS so pods can find Services by name.
- **DSN** — Data Source Name. The connection string `postgresql+asyncpg://user:pw@host/db`.
- **etcd** — distributed key-value store K8s uses for cluster state.
- **HLR** — Home Location Register. Telecom database of subscriber identities.
- **HMAC** — Hash-based Message Authentication Code. We sign audit events with HMAC-SHA256.
- **Idempotency** — calling an operation twice has the same effect as once. Important for retries.
- **Immutable infrastructure** — you never modify a running server; you replace it. Containers enforce this.
- **ICCID** — Integrated Circuit Card Identifier. The 19-20 digit number on a SIM.
- **IMSI** — International Mobile Subscriber Identity. The identifier the network uses.
- **MSISDN** — Mobile Subscriber ISDN Number. The phone number (e.g., +919876543210).
- **Namespace (Linux)** — kernel feature isolating PID/network/mount views per process group. Docker uses these.
- **Namespace (K8s)** — logical grouping inside a cluster. `kubectl get pods -n sim-prov`.
- **OIDC** — OpenID Connect. K8s issues OIDC tokens for pod ServiceAccounts; AWS trusts those for IRSA.
- **Outbox pattern** — write the work-to-do into a DB table, then poll it. We use it for HLR provisioning.
- **PromQL** — Prometheus Query Language. `rate(http_requests_total[5m])`.
- **Recording rule vs Alert rule** — recording = computes and stores a metric; alert = fires when a query is truthy.
- **SLI / SLO / SLA** — Service Level Indicator (measurement, e.g. p95 latency), Objective (target, "p95 < 2s 99% of the time"), Agreement (contract with the customer).
- **TLS termination** — HTTPS decrypted by the load balancer / ingress, then plain HTTP to pods. Reduces load on pods.
- **WAL** — Write-Ahead Log. How Postgres survives a crash without losing committed transactions.
- **Zero-downtime deploy** — rolling update where old pods drain while new pods come up.

---

## PART 10 — QUESTIONS THE SIR MIGHT ASK (and your money answers)

### Q: "What is the difference between a virtual machine and a container?"
**A:** A VM virtualises the *hardware* — it ships its own kernel and runs on a hypervisor like ESXi or KVM. A container virtualises the *operating system* — it shares the host kernel and uses Linux namespaces + cgroups for isolation. Result: a VM takes seconds-to-minutes to boot and is hundreds of MB or GB; a container starts in milliseconds and is tens of MB. Containers are not VMs; they're isolated processes.

### Q: "Why FastAPI over Flask or Django?"
**A:** Three reasons. One, async — FastAPI is async-first, so two workers comfortably handle hundreds of concurrent requests with I/O-bound workloads like ours. Two, OpenAPI for free — type hints automatically generate Swagger docs. Three, Pydantic validation at the boundary, so I never write `if not isinstance(x, int)` myself.

### Q: "What is the difference between a Deployment and a StatefulSet?"
**A:** Deployments are for stateless apps — pods are interchangeable, can be killed and recreated without ceremony. StatefulSets are for stateful apps like databases — pods have stable identities (`db-0`, `db-1`) and stable persistent volumes attached. We use a Deployment for the API (stateless) and would use a StatefulSet only for Postgres if we ran it in-cluster (we use RDS instead).

### Q: "What is a recording rule?"
**A:** A recording rule is a PromQL query that Prometheus evaluates on a schedule and stores the result as a new time series. We use them for two reasons: dashboard performance (`sim:activation_latency_seconds:p95` is one cheap series instead of recomputing `histogram_quantile(...)` every panel refresh), and for cleaner alert expressions.

### Q: "How does Prometheus discover what to scrape?"
**A:** Static config in `prometheus.yml` (`scrape_configs`) or service discovery — file-based, DNS-based, K8s-based (`kubernetes_sd_configs` discovers pods/services by label). In our compose stack it's static; in K8s it'd be the K8s SD.

### Q: "What happens if the Prometheus host dies?"
**A:** You lose metrics for the duration of the outage. For HA you run two Prometheus servers scraping the same targets (federation), or you use Thanos / Cortex / Mimir for long-term storage with HA query.

### Q: "Why is your password in Vault and not just an env var?"
**A:** Env vars show up in `kubectl describe pod`, in process listings (`ps aux`), in error logs, in Slack incident channels when someone pastes a stack trace. Vault means the password lives in one auditable store, with one rotation point, and is rendered into the container's memory by an injector rather than ever sitting in K8s manifests.

### Q: "What's the difference between authentication and authorisation?"
**A:** Authentication = "who are you?" (login). Authorisation = "what are you allowed to do?" (RBAC, policy). Vault's token mechanism is authentication; the policy attached to the token (what paths it can read/write) is authorisation.

### Q: "What's IRSA?"
**A:** IAM Roles for Service Accounts. The clean way to give a K8s pod AWS permissions without long-lived AWS keys. The pod's ServiceAccount has an IAM role annotation; AWS trusts the EKS OIDC issuer; the pod exchanges its ServiceAccount JWT for temporary AWS credentials via STS. Zero long-lived keys. Auto-rotated.

### Q: "What does `kubectl rollout undo` actually do?"
**A:** Kubernetes keeps a revision history on every Deployment. `rollout undo` flips the Deployment spec back to the previous revision's pod template, which triggers a rolling update back to the old image. Fast, safe, no manual `kubectl edit` required.

### Q: "How do you handle a sudden 10x traffic spike?"
**A:** HPA scales pods from 3 to up to 12 based on CPU at 70%. PDB ensures we keep at least 2 pods up even during node drains. NetworkPolicy means an attacker can't pivot from the spike. Beyond 12 pods we'd hit RDS — that's the next bottleneck and we'd need read replicas.

### Q: "What's the difference between liveness and readiness probes?"
**A:** Liveness = "should the orchestrator restart me?" Failing liveness kills the pod. Readiness = "should the Service send me traffic right now?" Failing readiness removes the pod from the Service endpoints but doesn't kill it. Critical distinction: a pod that's slow because it's reconnecting to Postgres should fail readiness, not liveness — otherwise it gets killed and never recovers.

### Q: "Why pull-based metrics (Prometheus) instead of push (StatsD)?"
**A:** Discovery and self-healing. With pull, Prometheus knows what *should* exist. If a target's missing, that itself is a signal (`up == 0` alert). With push, a dead service stops sending; you'd need a separate watchdog. Plus, no metric backlog if Prometheus is down — the next scrape just picks up.

### Q: "What does the `/healthz` endpoint do?"
**A:** Returns 200 OK as long as the process is alive. Doesn't check DB or external deps — that's `/readyz`. Distinct probes for distinct questions: am I alive (restart me?) vs am I ready to serve traffic.

### Q: "Why structured logs (JSON) instead of plain text?"
**A:** Because Logstash and Elasticsearch can index by field. `level: ERROR AND iccid: "8991..."` is a one-line query in Kibana. With plain text you'd need full-text search and regex. JSON also means a structlog `info(event="sim_activated", iccid=x, duration_ms=y)` becomes searchable, aggregatable, dashboard-able.

### Q: "What happens when you do `make up`?"
**A:** Runs `docker compose up -d`, which reads `docker-compose.yml`, builds any images that need building, pulls the rest, creates a docker network, then starts containers in dependency order — postgres first (others depend on its healthcheck), then migrate (runs Alembic and exits), then api / worker / frontend in parallel.

### Q: "What's an audit event?"
**A:** An immutable row in the `audit_events` table written every time a SIM transitions state. Includes the ICCID, the from/to status, who triggered it (actor), why (reason), and timestamp. We HMAC-sign each row so tampering is detectable. Compliance regulators love this.

### Q: "Why do you need a separate worker process? Why not do the HLR call inline?"
**A:** Two reasons. One, latency — HLR calls can take seconds, and we don't want a user request blocked on that. Two, retries — the worker can retry failed HLR calls with backoff; an HTTP request can't (the client has already disconnected). This is the outbox / async-job pattern, a standard architecture move.

### Q: "What is a histogram bucket?"
**A:** A histogram counts how many observations fall *below* each bucket's upper bound. Our latency histogram has buckets at `0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 10.0, 30.0` seconds. To compute p95, Prometheus interpolates between bucket boundaries.

### Q: "Why three Availability Zones?"
**A:** AWS RTO/RPO math. With three AZs and quorum-style services (RDS multi-AZ failover, etcd in K8s), losing one entire AZ is survivable without data loss. Two AZs aren't enough for quorum; one AZ is a single point of failure.

### Q: "What does `apiVersion: apps/v1` mean?"
**A:** The K8s API is grouped (`apps`, `batch`, `networking.k8s.io`, etc.) and versioned (`v1`, `v1beta1`). `apps/v1` is the stable version of the apps group, where Deployment, ReplicaSet, StatefulSet, DaemonSet live.

---

## PART 11 — ATTACK MOVES (one-liners that make you sound elite)

Drop these when the moment is right. Don't force them.

- *"The percentile computation is done by Prometheus's `histogram_quantile` on aggregated buckets — you can't average percentiles."*
- *"We use IRSA so there are no long-lived AWS keys anywhere in the cluster."*
- *"The reason the worker is a separate process and not an inline task is the outbox pattern — durability + retries that a synchronous HTTP request can't provide."*
- *"The Vault Agent Injector renders secrets into a tmpfs volume so they never touch disk and never appear in `kubectl describe pod`."*
- *"Liveness checks should be cheap and process-local; readiness can be expensive — the two probes answer two different questions."*
- *"The label-cardinality limit is the real Prometheus scaling problem. We don't label by user or request_id."*
- *"`readOnlyRootFilesystem: true` combined with `runAsNonRoot` plus dropping all capabilities is defence-in-depth — three independent layers."*
- *"Alembic gives us reversible, peer-reviewable schema changes — production migrations aren't `psql -c 'ALTER TABLE'` cowboys."*

---

## PART 12 — THE 10 PAGES OF THE SUBMISSION PDF (your demo flow)

When sir asks "what is this PDF?", walk through it in order:

1. **Cover** — project title, your details.
2. **TOC + stats** — 13 containers, 5000 SIMs, 8 alerts, 211k logs.
3. **Overview** — the four pain points + what was built.
4. **Architecture** — six layers: frontend / API / worker / state / observability / secrets.
5. **Application — Dashboard** (Fig 1).
6. **Application — Inventory** (Fig 2).
7. **Application — Swagger** (Fig 3).
8. **Containerization** — docker compose ps (Fig 4).
9. **Metrics** — Grafana (Fig 5).
10. **Alerting** — 8 rules + Prometheus (Fig 6).
11. **Logs** — ELK pipeline + Kibana (Fig 7).
12. **Secrets** — Vault tree (Fig 8).
13. **CI/CD · IaC · K8s** — Jenkins stages + Terraform + pod-spec.
14. **Conclusion** — 3-command reproduce + URLs.

---

## PART 13 — FINAL CHECKLIST (last 10 minutes before viva)

- [ ] `make up && make seed` is green.
- [ ] All 13 containers healthy: `docker compose ps`.
- [ ] Operator dashboard loads at `localhost:5173`.
- [ ] Grafana panels show data — refresh the dashboard once.
- [ ] Vault: paste `root-dev-token`, click "Sign in".
- [ ] `traffic-loop.sh` is running so the data stays fresh.
- [ ] PDF open in a separate tab: `docs/submission.pdf`.
- [ ] You can recite the four pain points and the six DevOps layers without looking.
- [ ] You can draw the state machine on paper.
- [ ] You can explain what each pipeline stage does in 5 seconds.

---

## ONE-PAGE MIND MAP (the whole project on one breath)

```
                          SIM PROVISIONING AUTOMATION PLATFORM
                                          │
              ┌───────────────────────────┼───────────────────────────┐
              │                           │                           │
        APPLICATION                   PLATFORM                  OBSERVABILITY
              │                           │                           │
   ┌─────┬────┴────┬─────┐     ┌──────────┼──────────┐     ┌──────────┼──────────┐
 FE  API  Worker Mock-HLR   Docker  Jenkins  TF     K8s   Prom   Graf  ELK   Vault
                                          │                  │
                                       9 stages           8 alerts
                                                     RED + business KPIs
                                                     request_id → log search
```

That's the whole project. If sir asks "what is X?", X is one of these 13 boxes.

Go win.
