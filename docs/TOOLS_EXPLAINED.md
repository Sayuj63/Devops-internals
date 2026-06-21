# EVERY TOOL IN THE PROJECT — EXPLAINED LIKE YOU'RE 15 (BUT WITH DEPTH)

> One definition per tool. No fluff, no jargon without explaining it.
> Each tool gets: what it is, a real-world analogy, what it does, why we use it, and where you see it in this project.

---

## QUICK MENTAL MAP (read this once, the rest will make sense)

Imagine you're building a restaurant chain:

| Restaurant analogy | Tool in our project |
|--------------------|---------------------|
| The kitchen (cooks food = serves API requests) | **FastAPI** + **uvicorn** |
| The recipe books (rules for what to cook when) | The **state machine** in our code |
| The pantry / fridge (stores ingredients = data) | **Postgres** |
| The waiter who takes orders to the kitchen | The **frontend dashboard** |
| The errand-runner who calls suppliers | The **worker** (talks to mock HLR) |
| The shipping container that packs your kitchen | **Docker** |
| The blueprint for opening many restaurants at once | **docker-compose** / **Kubernetes** |
| The clipboard you use to manage many kitchens | **Kubernetes** |
| The construction company that builds new locations | **Terraform** |
| The training manual that hires + trains new staff | **Jenkins** (CI/CD) |
| Security cameras + thermometer | **Prometheus** + **Grafana** |
| The complaint hotline + dispatcher | **Alertmanager** |
| The day-by-day diary every staff writes | **ELK** (logs) |
| The safe where the master keys are kept | **HashiCorp Vault** |

That's the whole project in one table. Now let's go tool by tool.

---

# PART 1 — APPLICATION TOOLS (the actual food being cooked)

## 🐍 FastAPI

**What it is:**
A modern Python framework for building APIs (Application Programming Interfaces — basically, the "language" computers use to talk to each other over HTTP).

**Think of it like:**
A super-smart kitchen manager. You tell it "when someone orders a burger, here's the recipe." FastAPI handles taking the order, checking the menu (validating input), cooking it (your code), and delivering it back as JSON.

**What it actually does:**
- Receives HTTP requests (GET, POST, etc.)
- Parses the URL and body
- Calls *your* Python function with the parsed data
- Validates input automatically using your type hints (e.g., `iccid: str`)
- Returns a response in JSON

**Why we use it:**
1. **Speed** — it's async (more on async below); two workers handle hundreds of requests.
2. **Auto docs** — visit `/docs` and you get a full interactive UI (Swagger) listing every endpoint. You didn't write that — FastAPI generated it from your code.
3. **Type safety** — if you say a parameter is `int`, FastAPI rejects strings with a clear error.

**In our project:**
The whole API at `localhost:8000` is FastAPI. Open `localhost:8000/docs` and you see the auto-generated Swagger.

---

## 🚀 Uvicorn

**What it is:**
A web server that runs Python web applications. Specifically, an ASGI server (Asynchronous Server Gateway Interface — the standard way Python async web apps talk to web servers).

**Think of it like:**
The microphone the kitchen manager (FastAPI) uses. FastAPI says "I want to serve API requests" — but FastAPI itself doesn't open ports or accept TCP connections. Uvicorn does that and hands each request to FastAPI.

**What it does:**
- Listens on a port (we use 8000)
- Accepts incoming HTTP connections
- Hands the request to FastAPI to handle
- Sends FastAPI's response back to the client

**Why we use it:**
- Fast (written in C-extensions internally)
- Supports async (matches FastAPI's style)
- Standard choice — almost every FastAPI project uses it

**In our project:**
We run uvicorn with 2 workers. Two processes, each running a copy of the API.

---

## 📐 Pydantic

**What it is:**
A Python library for data validation using type hints.

**Think of it like:**
A strict bouncer at the door of every API endpoint. You tell Pydantic "the request body must have an `iccid` (string), `actor` (string), `reason` (string)" and it checks every incoming request. Bad data? Auto-rejected with a 422 error and a clear message.

**What it does:**
- Defines schemas with Python classes:
  ```python
  class TransitionRequest(BaseModel):
      actor: str
      reason: str
  ```
- Parses incoming JSON into Python objects
- Validates types, ranges, formats
- Generates JSON schema (which feeds the Swagger docs)

**Why we use it:**
- You never write `if not isinstance(x, str)` yourself.
- Errors are uniform and machine-readable.
- It's how FastAPI knows what an endpoint expects.

**In our project:**
Every request body in `app/schemas.py` is a Pydantic model.

---

## 🗄️ SQLAlchemy

**What it is:**
An ORM — Object-Relational Mapper. Translates between Python classes and SQL tables.

**Think of it like:**
A translator between English and SQL. You write Python like:
```python
session.execute(select(SIM).where(SIM.status == "ACTIVE"))
```
SQLAlchemy converts that to actual SQL:
```sql
SELECT * FROM sims WHERE status = 'ACTIVE';
```

**What it does:**
- Lets you define database tables as Python classes
- Builds SQL queries from method calls
- Handles connection pooling (re-uses DB connections)
- Supports both sync and async

**Why we use it:**
- You write Python, not raw SQL strings (easier to read, refactor, test).
- SQL injection is harder to introduce because parameters are escaped automatically.
- Works with any SQL database (Postgres, MySQL, SQLite).

**In our project:**
`app/models.py` defines the tables (Sim, Plan, MsisdnPool, AuditEvent) as classes.

---

## ⚡ asyncpg

**What it is:**
A high-performance async PostgreSQL driver for Python.

**Think of it like:**
The actual phone line to Postgres. SQLAlchemy says "I want to send this query"; asyncpg sends the bytes over the network and reads the bytes back.

**Why we use it:**
- Async — non-blocking, fits our async FastAPI architecture
- Fastest Python Postgres driver (the C-extension is hand-tuned)
- Native Postgres protocol support (binary, not the slow text format)

**In our project:**
The database URL is `postgresql+asyncpg://...` — that `+asyncpg` tells SQLAlchemy "use asyncpg as the driver."

---

## 🏗️ Alembic

**What it is:**
A database migration tool for SQLAlchemy.

**Think of it like:**
Git, but for your database schema. Every change to the table structure is a "migration" — a versioned, reviewable script that says "add this column, drop this index."

**Why it exists:**
If you just edit your `models.py` and ship it, your code expects new columns that don't exist in the live database yet. Boom — production breaks. Migrations make schema changes deliberate, reversible, and applied in order.

**How it works:**
1. You edit `models.py`.
2. Run `alembic revision --autogenerate` — Alembic compares your models to the DB and writes a migration script.
3. You review the script.
4. Run `alembic upgrade head` — applies the script to the database.

**In our project:**
The `migrate` container in compose runs `alembic upgrade head` before the API starts. Migrations live in `app/backend/app/migrations/`.

---

## 📝 structlog

**What it is:**
A Python library that produces structured (JSON) log lines instead of plain text.

**Plain text log:**
```
2026-06-22 21:00:01 INFO Activated SIM 8991... in 1245ms
```

**Structured log (what we use):**
```json
{"timestamp": "2026-06-22T21:00:01Z", "level": "info", "event": "sim_activated", "iccid": "8991...", "duration_ms": 1245, "request_id": "abc123"}
```

**Why structured logs win:**
Elasticsearch can index the JSON fields. You can search "all errors where iccid = X" in one click. With plain text you'd need ugly regex.

**Bonus feature — request_id:**
A middleware assigns a unique ID to every incoming request. Every log line for that request includes that ID. When something goes wrong, grep one ID and you see the whole story.

**In our project:**
All API + worker logs are JSON. Logstash parses them; Kibana lets you search them by field.

---

# PART 2 — DATABASE

## 🐘 PostgreSQL (Postgres)

**What it is:**
A relational database. Stores data in tables (like spreadsheets with foreign-key relationships between them).

**Think of it like:**
A super-organised filing cabinet with strict rules. You can ask it "give me all SIMs with status = ACTIVE that were activated in the last week" and it gives you exactly that, instantly, even with billions of rows — thanks to indexes.

**Why Postgres specifically (not MySQL, not MongoDB):**

1. **It's free and open source.**
2. **It's the most feature-rich free SQL database.** JSON columns, full-text search, geo data, ENUMs.
3. **ACID guarantees** — atomic, consistent, isolated, durable transactions. (We need this — you can't lose an audit event.)
4. **Row-level locking** — when our MSISDN pool gives out a phone number, two workers can't grab the same number.
5. **WAL (Write-Ahead Log)** — every change is logged before it's applied. Crash → replay the log → data safe.

**Key concepts:**
- **Table** — like a spreadsheet (e.g., `sims`).
- **Row** — one record in a table.
- **Column** — one field.
- **Primary key** — column(s) uniquely identifying each row (`iccid` for SIMs).
- **Foreign key** — column pointing to another table's primary key (`sims.plan_id → plans.id`).
- **Index** — a lookup structure that speeds up specific queries (we index by `status` and `last_transition_at`).

**In our project:**
- Container: `sim-prov-postgres`
- Port: 5432
- Database: `simprov`
- Username/password: `simprov` / `simprov_dev_pw`
- Tables: `plans`, `sims`, `msisdn_pool`, `audit_events`, `alembic_version`

---

# PART 3 — CONTAINER TOOLS

## 🐳 Docker

**What it is:**
The most popular tool for building and running containers.

**Think of it like:**
Shipping containers (the physical kind). Before shipping containers, every cargo type was loaded differently — bananas in crates, machines in nets — and offloading was chaos. Standard containers changed that: every container is the same size, can stack, can ship by any truck/ship/train.

Software was the same — every app installed differently. Docker = standard container for software. Same image runs identically on your laptop, on a colleague's machine, and in production.

**What it does:**
- **Builds** images from a `Dockerfile` (recipe describing the container's filesystem)
- **Runs** containers (running instances of images)
- **Manages** the lifecycle: start, stop, remove, view logs

**Critical concepts:**

### Image vs Container
- **Image** = the recipe + ingredients, frozen on disk. Like a `.zip` file you can run.
- **Container** = an image being executed; an actual running process tree.
- One image → many containers can run from it.

### Layers
A Docker image is a stack of read-only layers. Each line in the Dockerfile that changes files creates a new layer. Layers are *cached* — if only your code changed, only the bottom layer rebuilds. Smart layer order = builds in seconds, not minutes.

### How is it not a virtual machine?
A VM ships its own kernel and runs on a hypervisor. Heavy (GBs, boots in minutes). A container shares the host's Linux kernel and uses *namespaces* (kernel feature) for isolation. Light (MBs, boots in milliseconds).

**The Dockerfile (recipe) — what each line means:**
```dockerfile
FROM python:3.11-slim       # Base layer: Python 3.11 on slim Debian
WORKDIR /app                # Set working directory inside container
COPY requirements.txt .     # Copy file from host into container
RUN pip install -r requirements.txt   # Run command, creates new layer
COPY app/ .                 # Copy source code
USER 1001                   # Switch to non-root user (security)
CMD ["uvicorn", "app.main:app"]   # Default command when container starts
```

**Why we use it:**
- "Works on my machine" disease — cured.
- Same image runs on developer laptop, CI, staging, prod.
- Tiny memory footprint vs. VMs.
- Fast to start, fast to ship.

**In our project:**
We have 4 custom-built images: `sim-prov/api`, `sim-prov/worker`, `sim-prov/mock-hlr`, `sim-prov/frontend`. We also use ~9 third-party images for Postgres, Vault, Prometheus, etc.

---

## 🎼 Docker Compose

**What it is:**
A tool to define and run multi-container applications. The YAML file (`docker-compose.yml`) lists every service, network, and volume.

**Think of it like:**
A conductor for an orchestra. Each container is a musician. Compose tells everyone when to start, what order, who depends on whom, and ensures they're all playing in sync.

**What it does:**
- Reads `docker-compose.yml`
- Builds any images that need building
- Starts containers in dependency order (e.g., wait for Postgres to be healthy before starting the API)
- Creates a shared network so containers can find each other by name (e.g., the API connects to `postgres:5432`, not an IP)
- Manages volumes for persistent data

**Why we use it:**
- One command (`make up`) starts the entire 13-service stack
- Local dev parity with production (almost) — same images, same versions
- No need to learn Kubernetes for local dev

**Compose vs Kubernetes:**
| Compose | Kubernetes |
|---------|------------|
| Local dev, small | Production, large |
| Single machine | Cluster (many machines) |
| Simple YAML | Complex (Pods, Services, Deployments, Ingress...) |
| Free, included with Docker | Heavy, needs a cluster |

**In our project:**
`docker-compose.yml` defines all 13 services. `make up` = `docker compose up -d`.

---

# PART 4 — CI/CD (Continuous Integration / Delivery)

## 🛠️ Jenkins

**What it is:**
An automation server that runs your build pipeline whenever code is pushed.

**Think of it like:**
A factory robot. You tell it "every time the boss pushes code: pull it, build it, test it, scan it, deploy it." It does that forever, without sleep, without forgetting steps.

**What it does:**
- Watches git for changes (or gets triggered by a webhook)
- Reads a `Jenkinsfile` from the repo describing the pipeline
- Executes each stage on its agents (worker machines)
- Reports status, logs, artifacts, test results
- Can pause for manual approval (e.g., "deploy to prod?")

**The 9 stages in our pipeline:**
| # | Stage | What happens |
|---|-------|--------------|
| 1 | Checkout | Pull code from git (~4s) |
| 2 | Lint | Run `ruff check` for style/bugs (~18s) |
| 3 | Test | Run `pytest` (~52s) |
| 4 | Build | `docker build` the API + worker images (~1m 12s) |
| 5 | Scan | Trivy scans images for known CVEs (~34s) |
| 6 | Push | Push to AWS ECR (image registry) |
| 7 | Deploy staging | `kustomize build … | kubectl apply` |
| 8 | **Manual approval** | A human says "yes, ship to prod" |
| 9 | Deploy prod | Push to prod K8s + Slack notification |

**Why Jenkins (vs GitHub Actions, GitLab CI):**
- Open source, self-hosted (no vendor lock-in)
- Most plugins of any CI tool
- Survives outages of GitHub etc. (it's on your hardware)
- Cons: clunky UI, plugin sprawl can become a security risk

**In our project:**
The `jenkins/Jenkinsfile` defines the pipeline. We don't run Jenkins locally (overkill); it lives in code, ready to be wired to a real Jenkins instance.

---

## 🧰 Make (Makefile)

**What it is:**
A 40-year-old tool that runs labelled shell commands. Originally for compiling C; now used everywhere as a simple task runner.

**Think of it like:**
A bookmark list for terminal commands. Instead of typing `docker compose up -d && ./scripts/seed-postgres.sh && ...`, you type `make up && make seed`.

**Our Makefile shortcuts:**
| Command | What it does |
|---------|--------------|
| `make up` | Start the stack |
| `make down` | Stop the stack |
| `make seed` | Load 5000 SIMs + 1000 phone numbers |
| `make smoke` | Run smoke test (health checks + sample API call) |
| `make logs` | Tail container logs |

**Why a Makefile:**
Everyone on the team types `make up`. No need to remember the actual 20-character compose command.

---

## 🔒 Trivy

**What it is:**
A vulnerability scanner from Aqua Security. Scans Docker images for known security flaws (CVEs).

**Think of it like:**
The metal detector at airport security. Before letting your image fly to production, it checks every package inside for known vulnerabilities.

**What it scans:**
- OS packages (Debian/Alpine packages with known CVEs)
- Language packages (Python pip, Node npm, Java jars)
- Misconfigured Dockerfiles (running as root, etc.)
- IaC files (Terraform, K8s YAML)

**How it works:**
1. Pulls the image apart layer by layer.
2. Lists every installed package.
3. Cross-references against the National Vulnerability Database (NVD) and other CVE feeds.
4. Reports findings with severity (LOW / MEDIUM / HIGH / CRITICAL).

**Why critical:**
Builds fail on HIGH or CRITICAL findings. Forces you to update dependencies before shipping.

**In our project:**
Stage 5 of the Jenkins pipeline runs `trivy image sim-prov/api:dev`.

---

# PART 5 — INFRASTRUCTURE AS CODE

## 🏛️ Terraform

**What it is:**
A tool by HashiCorp to define cloud infrastructure (VPC, servers, databases, IAM roles) in text files, version-controlled, applied with one command.

**Think of it like:**
An architectural blueprint that also builds the building. You write "I want 3 servers, a load balancer, and a database in 3 zones." You run `terraform apply`. AWS provisions exactly that.

**The big idea — declarative:**
You describe **what you want**, not **how to get there**. Terraform figures out the order: create VPC first, then subnets, then security groups, then EKS, then RDS. If you change one thing later, it computes the *minimum diff* to update.

**The classic workflow:**
```bash
terraform init     # Download provider plugins
terraform plan     # Show me what would change
terraform apply    # Make the changes
terraform destroy  # Tear it all down
```

**The state file:**
Terraform keeps a JSON file mapping your `.tf` files to actual AWS resource IDs. **This is the most important file in Terraform.** Lose it and Terraform doesn't know what it owns. Best practice: store it in S3 with versioning.

**Why Terraform (vs CloudFormation, Pulumi):**
- Works with every cloud (AWS, GCP, Azure, and many SaaS providers)
- Massive community + module ecosystem
- HCL (its config language) is readable; not as smart as a real programming language but simple
- Free and open source

**In our project:**
`terraform/envs/prod/main.tf` provisions a VPC (3 AZs), EKS cluster (Kubernetes), RDS Postgres (multi-AZ). We didn't actually `terraform apply` it (no real AWS budget) but the code is real.

---

# PART 6 — KUBERNETES (THE ORCHESTRATOR)

## ☸️ Kubernetes (K8s)

**What it is:**
A container orchestrator. The platform that runs containers across many machines reliably.

**Why "K8s":**
"K" + 8 letters ("ubernete") + "s". Like "i18n" for internationalization.

**Think of it like:**
The brain of a smart datacenter. You say "I need 3 copies of this app running, with autoscaling up to 12, and they should never all be down." Kubernetes manages it — places containers on machines, replaces failed ones, scales up under load, scales down when quiet.

**The story of why it exists:**
Docker tells you *how to package one process*. Kubernetes tells you *how to run thousands of those processes across a fleet of machines reliably*. Self-healing, scaling, rolling updates, networking, secret injection — all declarative.

**Core objects you must know:**

### Pod
The smallest deployable unit. One or more containers sharing network + storage. Usually one main container + maybe a sidecar (helper container).

### Deployment
Manages a fleet of identical pods. "I want 3 replicas of this pod template." It handles rolling updates (replaces one pod at a time without downtime).

### Service
A stable internal IP + DNS name that load-balances across pods. Pods come and go (IPs change); the Service is stable.

### Ingress
HTTP/HTTPS routing from outside the cluster. "Requests to `api.sim-prov.com` go to the API service; requests to `grafana.sim-prov.com` go to the Grafana service."

### ConfigMap / Secret
Key-value stores mounted into pods. ConfigMaps for plaintext config; Secrets for credentials.

### Namespace
Logical grouping inside the cluster. We'd have a `sim-prov` namespace for our app.

**Other features we use:**
- **HPA (Horizontal Pod Autoscaler)** — automatically scale 3 → 12 pods based on CPU
- **PDB (Pod Disruption Budget)** — "always keep at least 2 pods up during maintenance"
- **NetworkPolicy** — firewall between pods ("API can only talk to Postgres + Vault")

**Why use K8s (not just docker-compose):**
- Runs across many machines (compose is single machine)
- Self-healing (if a node dies, pods reschedule elsewhere)
- Built-in rolling updates with rollback
- Industry standard (every major cloud has managed K8s — EKS, GKE, AKS)

**In our project:**
We define K8s manifests in `k8s/` (base + staging + prod overlays). We didn't run a real K8s cluster locally; we use compose for local. The K8s code is production-ready.

---

## 🎨 Kustomize

**What it is:**
A tool to customise Kubernetes YAML manifests without templates.

**Think of it like:**
Photoshop layers. You have a base image (your manifests), and you stack overlays on top: "for staging, use 1 replica and small RAM; for prod, use 5 replicas and big RAM."

**How it works:**
```
k8s/
├── base/             # Common to all environments
│   ├── deployment.yaml
│   └── service.yaml
└── overlays/
    ├── staging/
    │   └── replicas-patch.yaml   # "Override replicas to 1"
    └── prod/
        └── replicas-patch.yaml   # "Override replicas to 5"
```

Run `kustomize build k8s/overlays/prod` → outputs the final manifest for prod (base + prod overlay merged).

**Why Kustomize (vs Helm):**
- No templating language to learn — just YAML on YAML
- Built into kubectl (`kubectl apply -k k8s/overlays/prod`)
- Simpler for medium complexity

**Why Helm wins sometimes:**
- More powerful for sharing reusable charts
- Versioning, rollback baked in
- Bigger ecosystem of public charts

**In our project:**
`k8s/overlays/prod` and `k8s/overlays/staging` use Kustomize to customise the base manifests per environment.

---

# PART 7 — OBSERVABILITY (knowing what's happening)

## 📊 Prometheus

**What it is:**
A time-series database + monitoring tool. Stores numeric metrics over time (CPU, request rate, error count, etc.) and lets you query them.

**Think of it like:**
A super-smart thermometer that records temperatures every 15 seconds and lets you ask "what was the temperature 3 hours ago?" or "give me the 95th percentile of temperatures last week."

**How it works (the magic word: PULL):**
Prometheus doesn't wait for apps to send metrics. It **pulls** them — every 15 seconds, it hits each app's `/metrics` URL (the "scrape target") and saves whatever numbers it finds.

**Our API exposes metrics like:**
```
# HELP sim_state_transitions_total Count of SIM state transitions
# TYPE sim_state_transitions_total counter
sim_state_transitions_total{from_status="PENDING",to_status="ALLOCATED"} 70
sim_state_transitions_total{from_status="ALLOCATED",to_status="ACTIVE"} 66
```

Prometheus scrapes that every 15s, stores it as a time series.

**Why pull (not push)?**
- Discovery — Prometheus knows what *should* exist. If a target's missing, that's a signal (`up == 0` alert).
- Easier to debug — you can hit `/metrics` yourself to see what's there.
- No tight coupling — apps don't need to know about Prometheus.

**The 4 metric types:**

| Type | What it means | Example |
|------|---------------|---------|
| **Counter** | Only goes up | "Total requests served" |
| **Gauge** | Goes up or down | "Memory usage in bytes" |
| **Histogram** | Bucketed counts | "Requests by latency bucket: <50ms, <100ms, <200ms..." |
| **Summary** | Like histogram with client-side percentiles | Rare |

**PromQL — the query language:**
```
rate(sim_state_transitions_total[5m])          # Per-second rate over 5 min
sum by (status) (sim_count_by_status)          # Sum, grouped by status label
histogram_quantile(0.95, ...)                   # 95th percentile from histogram
```

**Recording rules and alert rules:**
- A **recording rule** precomputes a query and stores the result as a new metric (makes dashboards faster).
- An **alert rule** is a PromQL expression that fires when it's truthy for a duration (e.g., "error rate > 5% for 10 minutes").

**In our project:**
- Container: `sim-prov-prometheus`
- Port: 9090
- URL: `localhost:9090`
- Scrapes the API every 15s
- 8 alert rules loaded (HighErrorRate, MsisdnPoolLow, DBDown, etc.)

---

## 📈 Grafana

**What it is:**
A dashboard tool. Connects to data sources (Prometheus is most common) and renders beautiful, interactive charts.

**Think of it like:**
The dashboard inside a car. The engine has lots of sensors (Prometheus reads them); Grafana is the speedometer, fuel gauge, and warning lights that turn raw numbers into something you can act on at a glance.

**What it does:**
- Queries Prometheus (or any data source — MySQL, Elasticsearch, Loki, InfluxDB...)
- Renders graphs, gauges, tables, heatmaps
- Variables (e.g., "show this dashboard for service X") and annotations
- Alerting (overlaps with Alertmanager but Grafana can do basic alerts too)

**Our "SIM Provisioning Operations" dashboard has 10 panels:**
1. SIMs by status (number cards)
2. SIM status distribution (donut)
3. MSISDN pool remaining (semicircle gauge)
4. Activation rate (timeseries — req/s)
5. Activation latency p50/p95/p99
6. HLR call success rate
7. State transitions (5m rate, by from→to)
8. API CPU
9. API resident memory
10. Recent alerts

**Why Grafana:**
- Best-in-class visualization
- Open source
- Plays with everything
- Dashboards-as-code (JSON exportable)

**In our project:**
- Container: `sim-prov-grafana`
- Port: 3001
- Login: `admin` / `admin`
- URL: `localhost:3001`

---

## 🚨 Alertmanager

**What it is:**
The "dispatcher" for Prometheus alerts. Prometheus fires alerts; Alertmanager decides who to notify and how.

**Think of it like:**
A 911 dispatcher. Many alerts (calls) come in — Alertmanager groups them (multiple alerts from one outage into one notification), deduplicates them, silences them if a maintenance window is on, and routes them: critical to PagerDuty, warnings to Slack, etc.

**Why a separate component:**
- Prometheus has one job — evaluate rules and fire alerts.
- Routing logic is a different problem — different teams, different channels, different times of day.
- Alertmanager focuses on that.

**Key features:**
- **Grouping** — 50 pods crash-looping → one alert, not 50.
- **Inhibition** — if "AllAPIsDown" is firing, don't send the 200 alerts that depend on the API being up.
- **Silencing** — "mute alerts for the next 4 hours during this maintenance."
- **Routing tree** — match by labels, send to PagerDuty / Slack / email.

**In our project:**
- Container: `sim-prov-alertmanager`
- Port: 9093
- URL: `localhost:9093`
- Config in `monitoring/alertmanager/alertmanager.yml`

---

## 🔍 Elasticsearch

**What it is:**
A distributed search engine + JSON document store. Built on Apache Lucene.

**Think of it like:**
Google for your logs. Type a query, get hits in milliseconds even across terabytes.

**How it works:**
- Stores data as JSON "documents" inside "indices" (like tables).
- Indexes every field for fast searching (full-text + exact match + ranges).
- Distributes data across nodes (each index has shards; shards have replicas).
- Returns results sorted by relevance or any field.

**Where it fits in ELK:**
ELK = **E**lasticsearch + **L**ogstash + **K**ibana. Logstash sends parsed logs into Elasticsearch; Kibana queries Elasticsearch.

**Why Elasticsearch:**
- Fastest search-at-scale tool that's open source
- Industry standard for logs (also used for site search, product search, security analytics)
- Cluster-native (scales horizontally)

**In our project:**
- Container: `sim-prov-elasticsearch`
- Port: 9200
- Stores ~50k+ log documents in `sim-prov-2026.06.21` (one index per day)
- URL: `localhost:9200`

---

## 🔧 Logstash

**What it is:**
A log processor — a pipeline that parses, transforms, enriches, and routes log data.

**Think of it like:**
The mailroom at a big company. Raw mail comes in (raw log lines); Logstash sorts it, opens envelopes, stamps it, and forwards each piece to the right department (Elasticsearch).

**What it does:**
- **Input** — receives logs from Filebeat (port 5044) or other sources
- **Filter** — parses JSON, drops noise (e.g., healthcheck requests), enriches fields
- **Output** — sends parsed logs to Elasticsearch

**Our config:**
```
input { beats { port => 5044 } }            # Listen for Filebeat
filter {
  if [message] =~ /^\s*\{/ {                # If line looks like JSON
    json { source => "message" }            # Parse it
  }
  if [app][route] == "/healthz" { drop {} } # Drop healthcheck noise
}
output { elasticsearch { hosts => ["..."] } }
```

**Why Logstash (vs other options):**
- Pluggable (200+ input/filter/output plugins)
- Flexible config language
- Industry-standard for log pipelines

**In our project:**
- Container: `sim-prov-logstash`
- Port: 5044
- Config: `logging/logstash/pipeline/logstash.conf`

---

## 🔎 Kibana

**What it is:**
The web UI for Elasticsearch.

**Think of it like:**
The search bar + dashboard for Elasticsearch. You can't see Elasticsearch's data without a UI (well, you can via API but it's ugly); Kibana gives you Discover (search logs), Visualize (charts), Dashboard (combinations).

**What it does:**
- **Discover** — search logs with KQL (Kibana Query Language): `level: ERROR AND service: "sim-prov-api"`
- **Visualize** — bar charts, pie charts, time series
- **Dashboard** — combine visualizations
- **Dev Tools** — raw Elasticsearch API console (advanced)

**In our project:**
- Container: `sim-prov-kibana`
- Port: 5601
- URL: `localhost:5601/app/discover`
- Index pattern: `sim-prov-*` (matches `sim-prov-2026.06.21`, `sim-prov-2026.06.22`, etc.)

---

## 📦 Filebeat

**What it is:**
A lightweight log shipper. Tails files (or Docker container stdout) and forwards them to Logstash or Elasticsearch.

**Think of it like:**
A delivery truck. It picks up logs from every container and delivers them to the central mailroom (Logstash).

**Why a separate tool:**
- Filebeat is tiny (~30 MB), low CPU, low memory
- Runs on every machine that has logs
- Smart — remembers where it left off (resumable)
- Backpressure-aware — won't overwhelm Logstash

**How it discovers containers:**
"Autodiscover" mode — Filebeat watches Docker, and whenever a new container starts, it begins tailing that container's log file automatically.

**The full pipeline:**
```
App → stdout → Docker logs file → Filebeat → Logstash → Elasticsearch → Kibana
```

**In our project:**
- Container: `sim-prov-filebeat`
- Tails every container's `/var/lib/docker/containers/<id>/*.log`
- Ships to Logstash on port 5044

---

# PART 8 — SECRETS MANAGEMENT

## 🔐 HashiCorp Vault

**What it is:**
A secrets management tool. Stores passwords, API keys, certificates, and other sensitive data in one secure place with audit logs, access policies, and rotation.

**Think of it like:**
A bank vault. The master keys to your kingdom (DB passwords, AWS keys, signing certificates) all live in one heavily-guarded place. Apps prove their identity, request specific keys, and get them just-in-time.

**Why Vault exists (the problem it solves):**
The naive approach: put secrets in `.env` files or environment variables. Problems:
- They leak into logs (`kubectl describe pod` shows env vars in plaintext)
- They leak into shell history
- They sit on disk in `.env` files
- They're hard to rotate (need to redeploy every app using them)
- No audit trail of who accessed what

Vault fixes all of this. One source of truth, one rotation point, one audit log.

**Core concepts:**

### Secret engines
Vault has multiple "engines" for different kinds of secrets:
- **KV (Key-Value)** — basic store. Path → JSON value. That's what we use.
- **Database** — generates *short-lived* DB credentials. Vault talks to Postgres, creates a user with a random password, hands it to your app, deletes it 1 hour later.
- **AWS** — generates short-lived AWS credentials.
- **Transit** — encrypt/decrypt without storing the data (encryption-as-a-service).

### Authentication methods
How apps prove who they are to Vault:
- **Token** — root token (what we use in dev, never in prod)
- **AppRole** — role ID + secret ID
- **Kubernetes** — pod uses its ServiceAccount JWT to authenticate
- **AWS IAM** — EC2 instance's IAM role
- **LDAP**, **OIDC** — for humans logging in

### Policies
What an authenticated identity is allowed to do. JSON or HCL document. Example:
```
path "secret/data/sim-prov/db" {
  capabilities = ["read"]
}
```
"This token can read the DB secrets, nothing else."

### The seal
In production, Vault starts *sealed* — encrypted, can't read its own data. To unseal, multiple humans (often 3 of 5) must enter their key shares. This is **Shamir's Secret Sharing** — no one person can unseal alone. (We use `-dev` mode which auto-unseals.)

### Vault Agent Injector (the K8s magic)
The really clean way to use Vault in K8s:
1. Annotate your pod with `vault.hashicorp.com/agent-inject: "true"`.
2. K8s adds a sidecar to your pod running `vault agent`.
3. The agent authenticates to Vault using the pod's ServiceAccount JWT.
4. It reads `secret/sim-prov/db`, writes the values to a file in shared memory.
5. Your app reads the file at startup.

The secret never appears in env vars, never on disk, never in `kubectl describe pod`. Beautiful.

**Our Vault tree:**
| Path | Contains |
|------|----------|
| `secret/sim-prov/db` | Postgres host, port, username, password, dbname |
| `secret/sim-prov/hlr` | HLR endpoint, API key |
| `secret/sim-prov/jwt` | JWT signing key, algorithm |
| `secret/sim-prov/audit-signing` | HMAC key for audit-event signatures |

**In our project:**
- Container: `sim-prov-vault`
- Port: 8200
- URL: `localhost:8200/ui/`
- Dev token: `root-dev-token`

---

# PART 9 — FRONTEND

## ⚡ Vite

**What it is:**
A modern frontend build tool. Bundles JavaScript, CSS, HTML for browsers.

**Think of it like:**
A super-fast packaging machine for your web code. Source files in → polished, optimised, browser-ready bundle out.

**Why Vite (vs Webpack):**
- Much faster dev server (uses native ES modules during dev)
- Faster production builds (uses esbuild + Rollup)
- Less config

**In our project:**
The frontend at `localhost:5173` uses Vite. Vanilla JavaScript (no React/Vue) for simplicity. Chart.js for the donut chart.

---

# PART 10 — TESTING & CODE QUALITY

## 🧪 Pytest

**What it is:**
Python's most popular test framework.

**Think of it like:**
A QA inspector. You write test functions (`def test_can_activate_pending_sim()`); pytest runs them all and reports pass/fail.

**Key features:**
- Plain functions, no class boilerplate
- Powerful fixtures (reusable setup code via `@pytest.fixture`)
- Plugin ecosystem (pytest-asyncio for async, pytest-cov for coverage)
- Clear failure messages

**In our project:**
Tests live in `app/backend/tests/`. Run via `pytest tests/ -v`.

---

## 🧹 Ruff

**What it is:**
A super-fast Python linter (also formatter). Replaces flake8, isort, autopep8, and more.

**Think of it like:**
A grammar checker for Python code. Catches unused imports, bad style, common bugs.

**Why Ruff (vs flake8 etc.):**
- 10-100× faster (written in Rust)
- Combines many tools into one
- Drop-in replacement

**In our project:**
CI runs `ruff check app/ tests/` in the lint stage. Failed = build red.

---

# PART 11 — VERSION CONTROL

## 🌿 Git

**What it is:**
A distributed version control system. Tracks every change to every file, lets multiple people collaborate.

**Think of it like:**
Track Changes in Word, but for entire codebases, time-machine-style, with branches and merges.

**Core mental model:**
Every commit is a snapshot identified by a SHA hash. Branches are just named pointers to commits.

**The 3 areas:**
1. **Working directory** — files you're editing
2. **Staging area** — changes prepared for commit
3. **Repository** — committed history

**Essential commands:**
```bash
git status              # what's changed?
git add file.py         # stage
git commit -m "msg"     # snapshot
git push                # send to GitHub
git pull                # fetch from GitHub
git log                 # history
git branch new-feature  # create branch
git checkout new-feature # switch
git merge main          # bring main into your branch
```

**In our project:**
Repo: `github.com/Sayuj63/Devops-internals`. Main branch is `main`. Every change pushed via commits.

---

# PART 12 — TELECOM DOMAIN TERMS

These come up because the project is *about* telecom SIM provisioning. Examiner might ask: "What's an MSISDN?"

## SIM (Subscriber Identity Module)
The little card inside your phone. Authenticates you to the network.

## ICCID (Integrated Circuit Card Identifier)
The 19-20-digit number printed on the SIM card itself. The serial number. We use it as the primary key for the `sims` table.

Example: `8991700000000071`

## IMSI (International Mobile Subscriber Identity)
The identity the *network* uses to recognise you. 15 digits.
- First 3 digits = MCC (Mobile Country Code)
- Next 2-3 = MNC (Mobile Network Code)
- Rest = MSIN (subscriber's unique number on that network)

Example: `404100000004918` (India MCC=404, operator MNC=10)

## MSISDN (Mobile Subscriber ISDN Number)
The phone number — what people dial. ISDN = Integrated Services Digital Network (old telecom standard; the name stuck).

Example: `+919876543210`

## HLR (Home Location Register)
The central database of all subscribers on a telecom network. Stores: IMSI, current MSISDN, allowed services, current location (which cell tower). When you make a call, the network queries the HLR to find you.

In our project, we have a **mock HLR** because we can't talk to a real Ericsson/Nokia HLR.

## Plan
A bundle of voice / data / SMS allowance. We have three: Saver 1GB / Smart 25GB / Power 100GB.

## Provisioning
The act of registering a SIM in the HLR so it works on the network. That's what our worker does.

## SIM lifecycle states
| State | Meaning |
|-------|---------|
| **PENDING** | In stock, no customer |
| **ALLOCATED** | Assigned to a plan/customer, not yet activated |
| **ACTIVE** | Provisioned in HLR, has MSISDN, working |
| **SUSPENDED** | Temporarily disabled |
| **PORTED** | Number ported to another operator |
| **RECYCLED** | Returned to pool for re-use |

---

# PART 13 — KEY CONCEPTS USED ACROSS THE PROJECT

## State Machine
A model where a thing can only be in one defined state at a time, and only certain transitions between states are legal.

Our SIM state machine:
- From PENDING, only `allocate` is valid → ALLOCATED.
- From ALLOCATED, only `activate` is valid → ACTIVE.
- You can't go from PENDING straight to ACTIVE.

**Why important:** Prevents illegal transitions. You can't `activate` a RECYCLED SIM. Enforced in code.

## Async / await
A way for Python code to wait for slow things (network, disk) without blocking other code.

**Without async:**
```python
def get_sims():
    data = db.execute("SELECT ...")  # Blocks for 50ms
    return data
```
While `db.execute` is waiting, the worker can do nothing else.

**With async:**
```python
async def get_sims():
    data = await db.execute("SELECT ...")  # Hands control back during wait
    return data
```
While waiting, the worker can handle OTHER requests. Massive throughput improvement for I/O-heavy code.

## The Outbox / Async Worker Pattern
Instead of doing slow work inline (which blocks the user), write the work to do into a table (or just mark the row), and have a separate worker process it.

In our project: the API marks a SIM as ALLOCATED and returns immediately. The worker polls for ALLOCATED rows, calls the slow HLR, marks them ACTIVE.

**Why:** the user's HTTP request finishes in 50ms instead of 5s. The worker can retry if the HLR is down. Resilience.

## Healthcheck
An endpoint your app exposes that says "I'm OK" or "I'm not." Used by Docker, K8s, load balancers.

**Two flavours:**
- **Liveness** — am I alive? If not, restart me. (Our `/healthz`)
- **Readiness** — am I ready to handle traffic? If not, take me out of the load balancer pool. (Our `/readyz` — actually pings Postgres)

## RED metrics
SRE shorthand for the metrics every service should expose:
- **R**ate — requests/sec
- **E**rrors — failures/sec
- **D**uration — latency distribution

## Layer (Docker)
A read-only filesystem layer in a Docker image. Stacked together, they form the image. Cached individually for fast rebuilds.

## Image vs Container
- **Image** = recipe, stored on disk.
- **Container** = running instance of an image.
- Same image → many containers.

## REST API
A style of API design using HTTP verbs:
- `GET /sims` — list
- `GET /sims/123` — read one
- `POST /sims` — create
- `PATCH /sims/123` — update
- `DELETE /sims/123` — delete

URLs are nouns; methods are verbs.

## Swagger / OpenAPI
A standard for describing REST APIs in YAML/JSON. FastAPI generates this automatically; Swagger UI renders it as the interactive `/docs` page.

## JSON (JavaScript Object Notation)
The standard data format for APIs.
```json
{"iccid": "8991...", "status": "ACTIVE", "msisdn": "+91..."}
```

## YAML
A human-readable config format. Same data as JSON but easier to read/write. Used by docker-compose, K8s, Prometheus, Alertmanager.

## Request ID
A unique identifier (UUID) assigned to every incoming HTTP request. Propagated through logs so you can trace one request's journey through the system. Generated in our middleware; included in every structlog line.

---

# QUICK CROSS-REFERENCE TABLE

| You see this in the project | It's actually | Lives at |
|----------------------------|---------------|----------|
| `localhost:5173` | The Vite frontend (vanilla JS) | port 5173 |
| `localhost:8000/docs` | FastAPI auto-generated Swagger | port 8000 |
| `localhost:8000/metrics` | Prometheus scrape target | port 8000 |
| `localhost:9000/docs` | Mock HLR Swagger | port 9000 |
| `localhost:9090` | Prometheus | port 9090 |
| `localhost:9090/alerts` | Prometheus alert rules | port 9090 |
| `localhost:9093` | Alertmanager | port 9093 |
| `localhost:3001` | Grafana | port 3001 |
| `localhost:5601` | Kibana | port 5601 |
| `localhost:9200` | Elasticsearch | port 9200 |
| `localhost:8200` | Vault UI | port 8200 |
| `localhost:5432` | Postgres | port 5432 |

---

# CLOSING — HOW TO USE THIS DOC

- **Don't memorise.** Understand the *why* of each tool. The names of features change; the underlying problem they solve doesn't.
- **Match tool to problem.** When sir asks "why X?", answer "because we needed Y, and X solves it cleanly."
- **Cross-check** with `VIVA_PREP.md` (Q&A format) and `DEVOPS_GUIDE.md` (general concepts).

If you can explain what *every* container in `docker compose ps` does, and *why* it exists in this stack — you've already won.
