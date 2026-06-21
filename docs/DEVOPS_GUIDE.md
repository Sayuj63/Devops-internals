# DEVOPS — THE COMPLETE CONCEPTS & TERMINOLOGY GUIDE

> A foundational reference. Not project-specific. Reads top-to-bottom for a full mental model, or jump to any section as a glossary.

---

## TABLE OF CONTENTS

1. [Philosophy — What DevOps Actually Is](#1-philosophy)
2. [The Software Lifecycle](#2-the-software-lifecycle)
3. [Linux Fundamentals](#3-linux-fundamentals)
4. [Networking Essentials](#4-networking-essentials)
5. [Version Control (Git)](#5-version-control-git)
6. [Containerization (Deep)](#6-containerization)
7. [Container Orchestration (Kubernetes)](#7-orchestration-kubernetes)
8. [CI/CD Patterns](#8-cicd-patterns)
9. [Infrastructure as Code](#9-infrastructure-as-code)
10. [Cloud Architecture](#10-cloud-architecture)
11. [Observability (Metrics, Logs, Traces)](#11-observability)
12. [Security](#12-security)
13. [Reliability & SRE](#13-reliability--sre)
14. [Databases](#14-databases)
15. [Web & APIs](#15-web--apis)
16. [Alphabetical Glossary](#16-alphabetical-glossary)
17. [Acronym Cheat Sheet](#17-acronym-cheat-sheet)

---

## 1. PHILOSOPHY

### What is DevOps?

DevOps is a **culture + practice + tooling** combination where the people who write the software (Dev) and the people who run it (Ops) share responsibility for the whole lifecycle. It's not a job title. It's not a set of tools. The tools are how you implement the culture.

**The core insight:** when developers throw code over the wall to ops, both sides lose. Dev gets blamed when ops can't run the code; ops gets blamed when their fixes break new deploys. The fix is shared ownership + automation that makes "build, test, deploy, monitor" cheap enough to do dozens of times per day.

### Three foundational principles

1. **Flow** — work flows from idea to production with as little friction as possible. Eliminate handoffs, queues, and manual gates that don't add value.
2. **Feedback** — every stage tells the previous one when something is wrong. Failing tests, alerts, customer complaints — all loop back.
3. **Continuous learning** — failures are studied (postmortems, blameless), and the system gets harder to break each time.

### What DevOps is **not**

- Not just CI/CD.
- Not just "we hired DevOps engineers".
- Not just "we use Kubernetes".
- Not a department.

### Related movements

- **DevSecOps** — security baked into every stage, not bolted on at the end.
- **GitOps** — git is the single source of truth for both code *and* infra state. Changes happen by merging PRs, not by clicking in consoles.
- **SRE (Site Reliability Engineering)** — Google's flavour of DevOps. Heavy on measurement (SLI/SLO/SLA) and on treating ops as a software problem.
- **Platform Engineering** — building an internal "platform" that gives developers self-service infrastructure. The next step beyond DevOps for big orgs.

---

## 2. THE SOFTWARE LIFECYCLE

### The classical SDLC

`Plan → Code → Build → Test → Release → Deploy → Operate → Monitor`

In DevOps each arrow becomes a feedback loop, not a one-way flow.

### Methodologies you should be able to name

- **Waterfall** — finish each phase before the next. Slow, no feedback, almost dead in 2026.
- **Agile** — short iterations (sprints), continuous feedback, working software over docs.
- **Scrum** — Agile with rituals: standups, sprint planning, retrospectives. 2-week sprints.
- **Kanban** — continuous flow, WIP limits, no fixed sprints.
- **XP (Extreme Programming)** — Agile + TDD + pair programming + frequent releases.

### Environment progression

`Local dev → Dev → Staging (or QA / UAT) → Pre-prod → Production`

Each environment exists to catch a class of bug before the next one. **Staging should mirror production as closely as possible.** Differences ("oh it works in staging") are usually because staging isn't *actually* mirroring prod.

### Deployment frequency

A surprising metric — the best DevOps orgs deploy **multiple times per day**. Worst orgs deploy quarterly. High frequency = small, low-risk changes; low frequency = scary releases with hundreds of changes batched up.

---

## 3. LINUX FUNDAMENTALS

You will deploy on Linux 99% of the time. You don't need to be a kernel hacker, but you need this.

### Processes

A **process** is a running program. Every process has a PID (process ID). PID 1 is special — it's the init process (systemd on most distros).

```
ps aux              # list all processes
top / htop          # live view of CPU/memory
kill <pid>          # send SIGTERM (graceful stop)
kill -9 <pid>       # send SIGKILL (force)
```

### Signals

A signal is an interrupt sent to a process. Important ones:
- **SIGTERM (15)** — politely asks the process to shut down. Catchable.
- **SIGKILL (9)** — immediate termination. Cannot be caught.
- **SIGINT (2)** — what Ctrl-C sends.
- **SIGHUP (1)** — historically "terminal closed"; often reused as "reload config" (nginx, prometheus).

### File permissions

```
-rwxr-xr--   1 alice  staff   1234  Jun 22 08:00  script.sh
```

- `-` = file (or `d` for directory, `l` for symlink)
- `rwx` = owner can read, write, execute
- `r-x` = group can read, execute
- `r--` = others can only read

Numeric form: `rwx = 7`, `rw- = 6`, `r-x = 5`, `r-- = 4`. So `chmod 755` = `rwxr-xr-x`.

### File descriptors

Every open file/socket has a number. Three are special:
- **0** = stdin (input)
- **1** = stdout (normal output)
- **2** = stderr (errors)

Redirect: `cmd > out.log 2>&1` = "send stdout to out.log, and send stderr wherever stdout is going."

### Pipes

`|` connects the stdout of one command to the stdin of the next. Build powerful one-liners:
```
docker compose logs api | grep ERROR | head -20
```

### The filesystem hierarchy

| Path | What lives here |
|------|----------------|
| `/bin`, `/usr/bin` | Programs |
| `/etc` | Config files |
| `/var` | Variable data — logs, databases |
| `/var/log` | Logs |
| `/tmp` | Temporary files (cleared on reboot) |
| `/home/<user>` | User home directories |
| `/opt` | Optional / third-party software |
| `/proc`, `/sys` | Kernel-exposed pseudo-filesystems |
| `/dev` | Device files |

### Package managers

- **apt** (Debian/Ubuntu) — `apt install <pkg>`
- **yum / dnf** (RedHat/CentOS/Fedora) — `dnf install <pkg>`
- **apk** (Alpine, what most slim containers use) — `apk add <pkg>`
- **brew** (macOS) — `brew install <pkg>`

### Shells

- **bash** — most common.
- **zsh** — default on modern macOS; bash-compatible with extras.
- **sh** — POSIX standard; what `#!/bin/sh` runs. More portable, fewer features.

### systemd (the init system)

Manages services on most modern Linux distros.
```
systemctl start <service>     # start now
systemctl enable <service>    # start on boot
systemctl status <service>    # what's it doing
journalctl -u <service> -f    # tail its logs
```

### Useful commands to know cold

| Cmd | Purpose |
|-----|---------|
| `ls -la` | List files with details |
| `cd`, `pwd` | Change/show directory |
| `cat`, `less`, `head`, `tail` | Read files |
| `grep <pattern>` | Search text |
| `find <dir> -name '*.py'` | Search filesystem |
| `awk`, `sed` | Text transformation |
| `curl -s <url>` | HTTP client |
| `jq` | JSON processor |
| `tar`, `gzip` | Archives |
| `df -h`, `du -sh` | Disk usage |
| `free -h` | Memory |
| `ss -tlnp` | List listening ports |
| `tcpdump` | Packet capture |
| `strace` | Trace system calls |
| `lsof` | List open files |

---

## 4. NETWORKING ESSENTIALS

### The OSI / TCP-IP layers

| Layer | TCP/IP | Examples |
|-------|--------|----------|
| 7 Application | Application | HTTP, DNS, SSH, gRPC |
| 6 Presentation | (combined) | TLS, JSON, Protobuf |
| 5 Session | (combined) | |
| 4 Transport | Transport | TCP, UDP |
| 3 Network | Internet | IP, ICMP |
| 2 Data Link | Link | Ethernet, MAC addresses |
| 1 Physical | Link | Cables, wifi radios |

You mostly care about layers 3, 4, 7.

### IP addresses

- **IPv4**: `192.168.1.100` — 4 octets, ~4 billion addresses (running out).
- **IPv6**: `2001:db8::1` — 128-bit, effectively infinite. Slower to roll out.

### CIDR notation

`10.0.0.0/16` means "the first 16 bits are the network; the last 16 bits are addresses." So `/16` = 65,536 addresses, `/24` = 256 addresses, `/32` = a single address.

### Private IP ranges

Reserved for internal use, never routed on the public internet:
- `10.0.0.0/8`
- `172.16.0.0/12`
- `192.168.0.0/16`

VPCs are built inside these ranges.

### Ports

A port is a 16-bit number (0-65535) on top of an IP that identifies a specific service.
- **0-1023** — well-known (require root): 22 SSH, 25 SMTP, 53 DNS, 80 HTTP, 443 HTTPS.
- **1024-49151** — registered: 3306 MySQL, 5432 Postgres, 6379 Redis, 9090 Prometheus.
- **49152-65535** — ephemeral: client-side outbound connections.

### TCP vs UDP

| TCP | UDP |
|-----|-----|
| Connection-oriented (handshake) | Connectionless |
| Reliable, ordered, retransmitted | Best-effort |
| Slower setup | Lightweight |
| HTTP, SSH, databases | DNS, video streaming, VOIP, QUIC |

### DNS

Translates hostnames to IPs. Hierarchical:
- `.` = root
- `.com` = TLD (Top-Level Domain)
- `google.com` = second-level
- `mail.google.com` = subdomain

Record types:
- **A** — name → IPv4
- **AAAA** — name → IPv6
- **CNAME** — name → another name
- **MX** — mail servers
- **TXT** — arbitrary text (used for SPF/DKIM, domain verification)
- **NS** — which DNS servers are authoritative for this zone

TTL (Time To Live) controls how long resolvers cache the answer.

### HTTP

Stateless request/response protocol.

**Methods (verbs):**
| Method | Meaning | Idempotent? |
|--------|---------|-------------|
| GET | Read | Yes |
| POST | Create / non-idempotent action | No |
| PUT | Replace (idempotent) | Yes |
| PATCH | Partial update | No |
| DELETE | Remove | Yes |
| HEAD | GET without body | Yes |
| OPTIONS | What's allowed | Yes |

**Status codes:**
| Class | Meaning | Examples |
|-------|---------|----------|
| 1xx | Informational | 100 Continue |
| 2xx | Success | 200 OK, 201 Created, 204 No Content |
| 3xx | Redirection | 301 Moved Permanently, 302 Found, 304 Not Modified |
| 4xx | Client error | 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found, 429 Too Many Requests |
| 5xx | Server error | 500 Internal Server Error, 502 Bad Gateway, 503 Service Unavailable, 504 Gateway Timeout |

### TLS / HTTPS

TLS (Transport Layer Security) provides encryption + identity verification on top of TCP. Modern version: TLS 1.3.

**Handshake (simplified):**
1. Client says hello, lists supported ciphers.
2. Server responds with chosen cipher + its certificate.
3. Client verifies the certificate against trusted CAs.
4. Both derive a shared session key (using Diffie-Hellman or similar).
5. Encrypted data flows.

**Certificates** are signed by a Certificate Authority (CA). Let's Encrypt is the most common free CA. Cert-manager is the K8s tool that auto-renews them.

### Common ports cheat sheet

| Port | Service |
|------|---------|
| 22 | SSH |
| 25 | SMTP |
| 53 | DNS |
| 80 | HTTP |
| 110 | POP3 |
| 143 | IMAP |
| 443 | HTTPS |
| 587 | SMTPS |
| 993 | IMAPS |
| 995 | POP3S |
| 3306 | MySQL |
| 5432 | Postgres |
| 6379 | Redis |
| 8080 | HTTP alternative |
| 9000 | various |
| 9090 | Prometheus |
| 27017 | MongoDB |

### NAT (Network Address Translation)

Lets many devices share one public IP. Your home router does this. In cloud, a NAT Gateway lets private-subnet resources reach the internet without being reachable themselves.

### Firewalls

Filter traffic by rule (source IP, port, direction). Two flavours:
- **Stateless** — each packet evaluated independently. Fast, simple.
- **Stateful** — tracks connections, allows return traffic automatically. (AWS Security Groups, iptables `conntrack`.)

---

## 5. VERSION CONTROL (GIT)

### The mental model

Git is a **content-addressable filesystem with a version control UI bolted on**. Every commit is a snapshot, identified by a SHA-1 hash of its contents. The same content always gets the same hash.

### The three areas

```
Working dir ──add──▶ Staging area ──commit──▶ Local repo ──push──▶ Remote
                ▲                                    │
                └────────────── checkout ────────────┘
```

### Essential commands

```bash
git clone <url>            # copy a repo
git status                 # what's changed
git diff                   # show changes
git add <file>             # stage changes
git commit -m "msg"        # snapshot the staging area
git log --oneline          # history
git push                   # send to remote
git pull                   # fetch + merge from remote
git branch <name>          # create branch
git checkout <branch>      # switch branch (older syntax)
git switch <branch>        # switch branch (newer)
git merge <branch>         # merge another branch in
git rebase <branch>        # replay your commits on top of another
git reset --soft HEAD~1    # undo last commit, keep changes staged
git reset --hard HEAD~1    # NUKE last commit + changes (be careful)
git stash                  # park unfinished work
git stash pop              # bring it back
```

### Branching strategies

- **GitFlow** — `develop`, `main`, `feature/*`, `release/*`, `hotfix/*` branches. Heavy. Falling out of fashion.
- **Trunk-based development** — everyone commits to `main` (or short-lived branches). Requires good CI + feature flags. Modern default at high-velocity orgs.
- **GitHub Flow** — `main` is always deployable; feature branches → PR → merge.

### Merge vs rebase

- **Merge** preserves history including branches. Creates a merge commit.
- **Rebase** rewrites your commits to sit on top of the target branch. Linear history.

> Golden rule: never rebase commits that are already pushed and someone else has based work on.

### Pull Requests / Merge Requests

Not a git feature — a GitHub/GitLab feature. A PR is a proposal to merge one branch into another, with code review, CI status, and conversation attached.

### .gitignore

A file listing patterns to ignore. Standard for any project:
```
node_modules/
__pycache__/
*.pyc
.env
*.log
.terraform/
```

### Conflict resolution

When two branches change the same lines, git can't auto-merge. It writes conflict markers into the file:
```
<<<<<<< HEAD
your version
=======
their version
>>>>>>> their-branch
```
You edit the file to pick one (or combine), then `git add` and `git commit`.

---

## 6. CONTAINERIZATION

### The "before containers" pain

Before containers, deploying an app meant: SSH to the server, install dependencies, hope they don't conflict with what's already there, configure system services, write deployment scripts that almost work. Environments drifted; "works on my machine" was the universal joke.

### What containers solve

A container packages an app + all its dependencies into one shippable unit that runs identically anywhere a container runtime exists.

### How containers actually work (Linux primitives)

Containers are **not VMs**. They're processes on the host kernel, isolated using:

1. **Namespaces** — kernel feature giving each process group its own view of:
   - `pid` — process IDs (your PID 1 is just a normal PID on the host)
   - `net` — network interfaces (your container has its own `eth0`)
   - `mnt` — mount points (your `/` is actually a layered filesystem)
   - `uts` — hostname
   - `ipc` — inter-process communication
   - `user` — UIDs (your `root` inside is a non-root UID on the host)
   - `cgroup` — cgroup view

2. **cgroups (control groups)** — limit and account for CPU, memory, IO, network. "This container gets at most 200m CPU and 512Mi RAM."

3. **Union filesystems** (overlay2, btrfs) — stack read-only layers + a thin writable layer on top. This is what makes images layered.

### The OCI standard

The **Open Container Initiative** defines:
- **Image format** — how a container image is laid out.
- **Runtime spec** — how a runtime starts a container from an image.

Docker, Podman, containerd, CRI-O all implement OCI. Images are portable across them.

### Image vs container — say this in your sleep

| Image | Container |
|-------|-----------|
| Frozen layered filesystem + metadata | Running process tree |
| Static, on disk | Active, in memory |
| Like a class | Like an instance |
| Identified by SHA digest | Identified by container ID |

### The Dockerfile

The recipe for building an image. Each instruction creates a layer.

```dockerfile
FROM python:3.11-slim          # base image
WORKDIR /app                   # set working directory
COPY requirements.txt .        # copy file
RUN pip install -r requirements.txt   # run command (cached layer)
COPY app/ .                    # copy source code
USER 1001                      # non-root
EXPOSE 8000                    # documentation only — does NOT publish ports
HEALTHCHECK CMD curl -f http://localhost:8000/healthz || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0"]
```

### Common Dockerfile mistakes

1. **Wrong COPY order** — copying source code before installing deps invalidates the cache on every code change.
2. **Running as root** — security risk.
3. **Using `latest` tag** — non-reproducible builds.
4. **Installing build tools in the final image** — bloats size, adds CVEs.
5. **Not using multi-stage builds** when you have a build step.
6. **Putting secrets in the image** — they leak. Use BuildKit secrets or runtime injection.

### Multi-stage builds

```dockerfile
FROM golang:1.21 AS builder
WORKDIR /src
COPY . .
RUN go build -o /out/app

FROM gcr.io/distroless/static-debian12
COPY --from=builder /out/app /
ENTRYPOINT ["/app"]
```

Final image has no compiler, no shell, ~5 MB. Hard to attack.

### Image registries

Where built images live. Public ones:
- **Docker Hub** — `docker.io/library/postgres`
- **GitHub Container Registry** — `ghcr.io/<owner>/<image>`
- **gcr.io / quay.io** — Google / Red Hat

Private:
- **AWS ECR** (Elastic Container Registry)
- **GCP Artifact Registry**
- **Azure ACR**
- Self-hosted: Harbor, Nexus.

### Image tags vs digests

- **Tag** — `myapp:v1.2.3` — mutable. Same tag can point to different images over time.
- **Digest** — `myapp@sha256:abc123...` — immutable. Always the same content.

Production should reference by digest for reproducibility.

### docker-compose

YAML file that defines multi-container apps for local development.

```yaml
services:
  api:
    image: myapp:dev
    build: .
    ports: ["8000:8000"]
    depends_on:
      postgres:
        condition: service_healthy
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_PASSWORD: dev
    healthcheck:
      test: pg_isready -U postgres
```

`docker compose up` brings the whole stack up. `docker compose down -v` tears it all down including volumes.

### Volumes vs bind mounts

- **Volume** — managed by Docker, lives in `/var/lib/docker/volumes/`. Use for persistent data.
- **Bind mount** — maps a host directory directly. Use for dev (live-reload code).

### Networks

By default Docker creates a bridge network per compose project. Services on the same network can reach each other by service name (`postgres:5432`).

### Common Docker commands

```bash
docker build -t name:tag .              # build
docker run --rm -p 8000:8000 name:tag   # run with port mapping
docker ps                                # list running
docker ps -a                             # list all (incl. stopped)
docker logs <ctn>                        # logs
docker exec -it <ctn> sh                 # shell into
docker inspect <ctn>                     # detailed info
docker image prune                       # delete dangling images
docker system prune -a                   # nuke everything unused
```

---

## 7. ORCHESTRATION (KUBERNETES)

### Why K8s exists

Docker tells you *how* to package one process. K8s tells you *how to reliably run thousands of containers across a fleet of machines* — self-healing, autoscaling, rolling deploys, service discovery, secret injection, networking.

### Architecture

```
┌───────────────── Control Plane ─────────────────┐
│  kube-apiserver     ◀── kubectl                  │
│  etcd               ◀── cluster state            │
│  scheduler          ◀── assigns pods to nodes    │
│  controller-manager ◀── reconciles desired state │
└──────────────────────────────────────────────────┘
                       │
              ┌────────┼────────┐
              ▼        ▼        ▼
          ┌─Node─┐ ┌─Node─┐ ┌─Node─┐
          │kubelet│ │kubelet│ │kubelet│
          │kube-proxy│ ...│
          │runtime│ ...
          └──────┘ └──────┘ └──────┘
```

- **kube-apiserver** — the only thing that talks to etcd. Every other component talks to the API server.
- **etcd** — distributed key-value store. Cluster's source of truth.
- **scheduler** — picks which node a new pod runs on.
- **controller-manager** — runs the controllers (Deployment controller, ReplicaSet controller, etc.) that watch the API and reconcile.
- **kubelet** — node agent. Talks to container runtime, reports status.
- **kube-proxy** — implements Services on each node (iptables/IPVS).

### The core objects

#### Pod
Smallest deployable unit. One or more containers sharing network + storage.

#### ReplicaSet
Ensures N copies of a pod are running. You rarely create this directly.

#### Deployment
Manages ReplicaSets to provide rolling updates and rollback.

#### StatefulSet
Like Deployment but pods have stable names (`db-0`, `db-1`) and stable storage. For databases.

#### DaemonSet
Runs one pod per node. For log shippers, node-exporters, CNI agents.

#### Job
Runs to completion. For batch tasks.

#### CronJob
Schedules Jobs on a cron expression.

#### Service
Stable virtual IP + DNS name that load-balances across pods matching a label selector.

Service types:
- **ClusterIP** (default) — internal cluster-only.
- **NodePort** — exposes on each node IP at a high port.
- **LoadBalancer** — provisions an external cloud LB.
- **ExternalName** — DNS alias.

#### Ingress
HTTP/HTTPS routing — usually one external endpoint that fans out to many Services by host/path.

#### ConfigMap
Plain-text config injected as env vars or files.

#### Secret
Base64-encoded sensitive data (passwords, keys). Encrypted at rest if you configure etcd encryption.

#### PersistentVolume / PersistentVolumeClaim
PV = a piece of storage; PVC = a request for storage. K8s binds them.

#### Namespace
Logical grouping inside a cluster. Most resources are namespaced.

### Pod lifecycle

`Pending → ContainerCreating → Running → Succeeded / Failed`

Plus `CrashLoopBackOff` (container keeps crashing) and `ImagePullBackOff` (can't pull image).

### Probes

- **livenessProbe** — "is the process alive?" Failing = restart.
- **readinessProbe** — "ready to serve traffic?" Failing = remove from Service endpoints.
- **startupProbe** — "still starting up?" Used for slow-starting apps; disables other probes until it succeeds.

### Resource requests vs limits

- **request** — minimum guaranteed (scheduler ensures the node has this).
- **limit** — maximum allowed (CPU is throttled, memory exceeding the limit triggers OOMKill).

### Quality of Service (QoS) classes

- **Guaranteed** — requests == limits. Evicted last.
- **Burstable** — requests < limits.
- **BestEffort** — no requests/limits. Evicted first.

### Scaling

- **HPA (Horizontal Pod Autoscaler)** — more pods.
- **VPA (Vertical Pod Autoscaler)** — bigger pods.
- **Cluster Autoscaler** — more nodes.
- **KEDA** — event-driven autoscaling (scale on queue depth, Kafka lag, etc.)

### Deployment strategies

- **Recreate** — kill all old, start all new. Downtime.
- **RollingUpdate** — gradual replacement. Default.
- **Blue/Green** — run old + new side by side, flip traffic at once.
- **Canary** — route a small % of traffic to new version first.

### kubectl essentials

```
kubectl get pods                          # list pods in current namespace
kubectl get pods -n sim-prov              # in a specific namespace
kubectl get pods -A                       # in all namespaces
kubectl describe pod <name>               # detailed info incl events
kubectl logs <pod>                        # logs
kubectl logs -f <pod>                     # follow
kubectl logs <pod> -c <container>         # multi-container pod
kubectl exec -it <pod> -- sh              # shell in
kubectl apply -f manifest.yaml            # create/update
kubectl delete -f manifest.yaml           # delete
kubectl rollout status deploy/<name>      # watch a rollout
kubectl rollout undo deploy/<name>        # roll back
kubectl scale deploy/<name> --replicas=5  # manual scale
kubectl port-forward svc/<name> 8080:80   # tunnel a service to localhost
kubectl top pods                          # CPU/mem (needs metrics-server)
kubectl explain deployment.spec.replicas  # API docs from CLI
```

### CNI — Container Network Interface

Plugin that gives each pod an IP and connects them. Common ones: Calico, Cilium, Flannel, Weave. AWS uses VPC-CNI (each pod gets a real VPC IP).

### CSI — Container Storage Interface

Plugin model for storage drivers (AWS EBS, GCP PD, Ceph, etc.)

### CRD — Custom Resource Definition

Extend K8s with your own object types. Operators (like Prometheus Operator, cert-manager) use CRDs to manage their domain.

### Operators

A controller that watches CRDs and reconciles. "Software that runs software." Pattern: declare what you want (e.g., a Prometheus CR), operator makes it happen.

### Helm

The K8s package manager. A Helm "chart" is a templated bundle of YAML. `helm install <release> <chart>` deploys it.

```
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prom prometheus-community/kube-prometheus-stack
```

### Kustomize

Alternative to Helm. No templating — just layered overlays. Built into kubectl.

```
k8s/
├── base/
│   ├── deployment.yaml
│   ├── service.yaml
│   └── kustomization.yaml
└── overlays/
    ├── staging/
    │   ├── kustomization.yaml
    │   └── replicas-patch.yaml
    └── prod/
        ├── kustomization.yaml
        └── replicas-patch.yaml
```

### Service Mesh

A layer of infrastructure for inter-service communication. Sidecars (often Envoy) handle TLS, retries, circuit breaking, observability.

Tools: **Istio**, **Linkerd**, **Consul Connect**.

When you need it: many microservices, complex traffic policies, mTLS between services.

---

## 8. CI/CD PATTERNS

### CI vs CD

- **CI (Continuous Integration)** — every push triggers automated build + test. Catches integration bugs immediately.
- **CD** has two meanings:
  - **Continuous Delivery** — every passing build is *deployable* (one click).
  - **Continuous Deployment** — every passing build is *deployed* automatically.

### The classic pipeline

```
Trigger (push/PR)
  ↓
Checkout
  ↓
Install deps
  ↓
Lint + Format check
  ↓
Unit tests
  ↓
Build artifact (image, jar, binary)
  ↓
Security scan (SAST, SCA, image scan)
  ↓
Push to registry
  ↓
Deploy to staging
  ↓
Integration / smoke tests
  ↓
Manual approval (for prod)
  ↓
Deploy to prod
  ↓
Smoke test + observability check
```

### Test pyramid

- **Unit tests** (lots) — fast, isolated, no I/O. 70%+ of tests.
- **Integration tests** — test components together (incl. real DB).
- **E2E tests** (few) — full system from outside. Slow, brittle.

### CI/CD tools

- **Jenkins** — old, self-hosted, infinitely flexible, plugin ecosystem.
- **GitHub Actions** — YAML-defined workflows in `.github/workflows/`.
- **GitLab CI** — `.gitlab-ci.yml`, runs on GitLab runners.
- **CircleCI** — hosted CI service.
- **Argo CD** — GitOps deployment to K8s.
- **Flux CD** — same idea as Argo, also K8s GitOps.
- **Spinnaker** — Netflix's CD platform, fancy deployment strategies.
- **Travis CI** — older, declining.

### GitOps

Workflow where the desired state of your infra/apps lives in git, and an agent (Argo / Flux) continuously syncs the cluster to match. Benefits:
- Full audit trail (git log).
- Easy rollback (revert commit).
- PR-based review of infra changes.
- The cluster can't drift silently.

### Feature flags

Toggle features on/off without redeploying. Crucial for trunk-based development — you merge unfinished code behind a flag, then turn it on gradually.

Tools: LaunchDarkly, Unleash, GrowthBook, ConfigCat.

### Deployment patterns recap

- **Blue/green** — two environments, flip a load balancer.
- **Canary** — route 1% → 10% → 50% → 100% over time, with health checks.
- **Rolling** — replace pods gradually.
- **Shadow / mirror** — send a copy of prod traffic to new version for testing.
- **Dark launch** — deploy but don't expose; warm caches.

### Rollback strategies

- **Immutable releases** — keep old versions; rollback = redeploy old image.
- **Database migrations** — must be backwards-compatible across rollback (expand-then-contract pattern).
- **`kubectl rollout undo`** for K8s.

---

## 9. INFRASTRUCTURE AS CODE

### What IaC is

Define infrastructure (servers, networks, databases, IAM) in text files, store in git, apply with tooling. **Don't click in consoles.**

### Why

- **Reproducibility** — staging and prod from the same code.
- **Review** — infra changes get PRs.
- **Rollback** — revert a commit.
- **Documentation** — the code IS the documentation.
- **Drift detection** — tooling can detect manual changes.

### Declarative vs Imperative

- **Imperative** — "create EC2 instance, then attach volume, then..." (Ansible playbooks, shell scripts).
- **Declarative** — "I want one EC2 with this volume; figure out how" (Terraform, K8s YAML).

Declarative wins because the tool handles drift, dependency ordering, partial failures, and incremental changes.

### The major tools

| Tool | What it does | Style |
|------|-------------|-------|
| **Terraform** | Cloud provisioning (VPC, EC2, etc.) | Declarative, HCL |
| **Pulumi** | Same as Terraform but in real programming languages | Declarative, Python/TS/Go |
| **AWS CloudFormation** | AWS-only; native | Declarative, YAML/JSON |
| **AWS CDK** | CloudFormation with code (Python/TS) | Imperative-flavoured-declarative |
| **Ansible** | Config management — install/configure inside servers | Imperative, YAML |
| **Chef / Puppet** | Config management (older) | Declarative-ish |
| **Packer** | Build VM/container images | Imperative |
| **Helm / Kustomize** | K8s manifests | Declarative |

### Terraform concepts

- **Provider** — plugin for a service (AWS, Azure, GCP, GitHub, Datadog).
- **Resource** — a thing to create (`aws_instance`, `aws_vpc`).
- **Data source** — read-only lookup.
- **Module** — reusable bundle of resources.
- **State file** — JSON mapping `.tf` resources to real-world IDs. Critical artefact.
- **Backend** — where state lives (local, S3, Terraform Cloud).
- **Workspace** — multiple states for the same code (dev, staging, prod).

### Terraform workflow

```bash
terraform init       # download providers, init backend
terraform fmt        # auto-format
terraform validate   # syntax check
terraform plan       # show diff
terraform apply      # make it real
terraform destroy    # tear down
terraform state list # what's in state
terraform import     # bring an existing resource under management
```

### State management best practices

- Store state in S3 with versioning.
- Lock state with DynamoDB (prevents two `apply`s at once).
- Never edit state by hand.
- Never commit state to git (contains secrets).

### Drift detection

Run `terraform plan` periodically. If anyone clicked in the console, the plan shows changes Terraform would make to undo them.

### Atlantis

Auto-runs Terraform on PRs. Comments back the plan output. Approval gates apply.

---

## 10. CLOUD ARCHITECTURE

### The big three (and the others)

- **AWS** — biggest, most services, originator.
- **Azure** — Microsoft's; strong with enterprise + .NET.
- **GCP** — Google; strong in data + Kubernetes (they invented it).
- Plus: DigitalOcean, Linode, Hetzner (simpler/cheaper), Oracle Cloud, Alibaba.

### Region / Availability Zone / Edge

- **Region** — geographic area (e.g., `us-east-1` = N. Virginia). Cross-region traffic is expensive.
- **Availability Zone (AZ)** — isolated data centre within a region. Usually 3+ per region. Disasters affecting one AZ usually don't hit others.
- **Edge location / PoP** — small data centre for CDN/DNS (CloudFront, Cloudflare).

### Multi-AZ vs Multi-Region

- **Multi-AZ** — high availability inside one region. Standard for prod.
- **Multi-region** — disaster recovery and global low-latency. Hard. Expensive.

### IAM (Identity and Access Management)

The cloud's permission system. Components:
- **User** — a human identity.
- **Role** — an identity that can be assumed (by users, services, or compute).
- **Policy** — JSON document granting/denying actions on resources.
- **Group** — collection of users sharing policies.

**Principle of least privilege** — grant the minimum permissions needed.

### Compute options

| Type | What it is | When to use |
|------|-----------|-------------|
| **VM (EC2)** | Full virtual machine | Maximum control, legacy apps |
| **Container (ECS / Fargate)** | Managed containers | Stateless services without K8s overhead |
| **Kubernetes (EKS / GKE / AKS)** | Managed K8s control plane | Standard for new workloads |
| **Serverless (Lambda / Cloud Functions)** | Event-driven functions | Glue code, spiky workloads |
| **App services (Beanstalk / App Service)** | "Just deploy my code" | Quick, simple apps |

### Storage options

| Type | Latency | Cost | Use |
|------|---------|------|-----|
| **Block** (EBS, Persistent Disk) | µs | $$ | Database volumes |
| **File** (EFS, Filestore) | ms | $$ | Shared filesystems |
| **Object** (S3, GCS) | 10-100ms | $ | Backups, static assets, data lakes |
| **Archive** (Glacier) | hours | ¢ | Long-term retention |

### Networking primitives

- **VPC** — Virtual Private Cloud. Your isolated network inside AWS.
- **Subnet** — slice of a VPC, lives in one AZ.
  - **Public subnet** — has route to internet gateway.
  - **Private subnet** — no direct internet route; uses NAT.
- **Internet Gateway** — connects VPC to public internet.
- **NAT Gateway** — lets private subnets reach internet outbound.
- **Security Group** — stateful firewall at instance/ENI level.
- **NACL** — stateless firewall at subnet level.
- **VPC Peering** — connect two VPCs.
- **Transit Gateway** — hub for many VPCs.
- **Route 53** — AWS DNS.
- **CloudFront** — AWS CDN.

### Managed databases

- **RDS** — AWS-managed SQL (Postgres, MySQL, etc.)
- **Aurora** — AWS-built MySQL/Postgres-compatible, faster + cheaper at scale.
- **DynamoDB** — AWS NoSQL key-value/document.
- **ElastiCache** — managed Redis/Memcached.
- Similar in GCP: Cloud SQL, Spanner, Firestore, Memorystore.

### Messaging / Queues

- **SQS** (AWS) — simple queue.
- **SNS** (AWS) — pub/sub.
- **EventBridge** (AWS) — event bus.
- **Kinesis / Kafka** — streaming.
- **Pub/Sub** (GCP) — equivalent of SNS+SQS.

### Identity federation

Let users / services from one identity provider authenticate to another. K8s ServiceAccount → AWS IAM Role via IRSA is one example. Azure AD → AWS is another.

### Cost concepts

- **On-demand** — pay per second/hour. Most flexible.
- **Reserved Instances / Savings Plans** — commit for 1-3 years for big discount.
- **Spot Instances** — bid for spare capacity; can be reclaimed with 2-min warning. Cheapest.
- **Egress** — data leaving the cloud. The expensive direction. Stay in-region when you can.

---

## 11. OBSERVABILITY

### Monitoring vs Observability

- **Monitoring** — watching known signals you've decided matter ("CPU > 80%? alert").
- **Observability** — the ability to ask new questions of your system after deployment, from outside.

Observability is a *property* of the system. Monitoring is a *practice*.

### The three pillars

1. **Metrics** — numeric measurements over time. Cheap, aggregable, low cardinality.
2. **Logs** — discrete events with context. Higher cardinality, more detail per item.
3. **Traces** — the path of a single request through many services.

### Metrics

#### The four golden signals (Google SRE)
- **Latency** — how long requests take.
- **Traffic** — how much demand.
- **Errors** — what's failing.
- **Saturation** — how full the system is.

#### RED method (for services)
- **Rate**, **Errors**, **Duration**. Subset of golden signals.

#### USE method (for resources)
- **Utilisation**, **Saturation**, **Errors**. For CPU, disks, networks.

#### Time-series database (TSDB)
Storage optimized for `(metric, labels, timestamp, value)`. Examples: Prometheus, InfluxDB, VictoriaMetrics, Mimir, TimescaleDB.

#### Metric types
- **Counter** — only goes up. `requests_total`.
- **Gauge** — up or down. `memory_used_bytes`.
- **Histogram** — bucketed counts. `request_duration_seconds_bucket`.
- **Summary** — client-side quantiles.

#### Cardinality
The number of distinct label combinations. High cardinality kills TSDBs. **Never** label by user ID, request ID, or anything unbounded.

### Logs

#### Structured vs unstructured
- **Unstructured**: `"2026-06-22 INFO request completed in 12ms"` — needs regex to query.
- **Structured (JSON)**: `{"level":"info","event":"request","duration_ms":12}` — query by field.

#### Log levels (most to least severe)
`FATAL > ERROR > WARN > INFO > DEBUG > TRACE`

Production usually runs at INFO. DEBUG for trouble-shooting.

#### Log aggregation tools
- **ELK / Elastic Stack** — Elasticsearch + Logstash + Kibana + Beats.
- **OpenSearch** — Amazon's fork of Elasticsearch.
- **Loki** — Grafana Labs. Indexes only metadata; lighter than ELK.
- **Splunk** — enterprise; expensive but powerful.
- **Datadog, New Relic, Sumo Logic** — SaaS observability platforms.

### Traces

A trace is a request's journey through your services. Made of **spans** (each span is one operation).

#### OpenTelemetry (OTel)
The vendor-neutral standard. Replaces Jaeger client libs, Zipkin libs, etc. Instrument your code once, export to any backend.

#### Distributed tracing backends
- **Jaeger** — open source, CNCF.
- **Tempo** (Grafana Labs).
- **Zipkin** — older.
- **Datadog APM, New Relic, Honeycomb** — SaaS.

#### Trace context propagation
Pass `traceparent` HTTP header across service calls. Standard: W3C Trace Context.

### Alerting

#### Tools
- **Prometheus Alertmanager** — routes, groups, silences alerts.
- **PagerDuty / Opsgenie / VictorOps** — on-call paging.
- **Slack / Teams** — chat-ops notifications.

#### Alert design
- **Alert on symptoms, not causes** — alert on "users see errors", not on "CPU is high".
- **Pageable alerts must require human action.** If it doesn't, it's noise.
- **Every alert must have a runbook.**
- **`for:`** — require the condition to hold for N minutes before firing. Reduces flapping.

### SLI / SLO / SLA / SLA penalties

- **SLI (Service Level Indicator)** — what you measure. "Request success rate over 5 min."
- **SLO (Service Level Objective)** — internal target. "99.9% of requests succeed."
- **SLA (Service Level Agreement)** — external contract. "We refund if availability < 99.9%."
- **Error budget** — `100% - SLO`. If SLO is 99.9%, you can afford 0.1% errors. When the budget runs out, slow down releases.

### MTTR / MTBF / MTTD

- **MTTR** — Mean Time To Recover.
- **MTBF** — Mean Time Between Failures.
- **MTTD** — Mean Time To Detect.

Modern DevOps doesn't try to eliminate failure — it minimises MTTR.

---

## 12. SECURITY

### Defense in depth

No single layer is enough. Stack mitigations so an attacker has to defeat several:

```
Network    Cloud security groups + NACLs + WAF
Cluster    NetworkPolicy + mTLS + RBAC
Pod        runAsNonRoot + readOnlyRootFS + dropped caps + seccomp
Process    Memory-safe languages, least privilege, audit logs
Data       Encryption at rest + in transit
Identity   Short-lived creds, MFA, IRSA-style federation
Supply     Image signing, SBOMs, CVE scanning, dep pinning
```

### The CIA triad

- **Confidentiality** — only authorised eyes see data.
- **Integrity** — data isn't tampered with undetected.
- **Availability** — legitimate users can access the service.

### Authentication vs Authorisation

- **AuthN** — who are you? (login, certificates, tokens)
- **AuthZ** — what can you do? (policies, RBAC, scopes)

### Common authentication mechanisms

- **Basic auth** — username:password in header (only over TLS).
- **API keys** — long-lived secrets in headers. Vulnerable if leaked.
- **JWT (JSON Web Token)** — signed, self-contained. Stateless.
- **OAuth 2.0** — authorization framework. Token-based, multiple grant types.
- **OIDC (OpenID Connect)** — identity layer on top of OAuth 2.0.
- **mTLS** — mutual TLS. Both sides have certificates.
- **SAML** — old enterprise SSO standard.

### Secrets management

Rules:
- Never check secrets into git.
- Never put them in env vars on disk.
- Rotate them regularly.
- Use short-lived tokens where possible.

Tools:
- **HashiCorp Vault** — multi-engine secrets store + dynamic secrets.
- **AWS Secrets Manager / Parameter Store**.
- **GCP Secret Manager**.
- **Azure Key Vault**.
- **Doppler, Infisical** — SaaS.

### Scanning categories

- **SAST (Static Application Security Testing)** — analyse source code. Examples: SonarQube, Snyk Code, Semgrep, CodeQL.
- **DAST (Dynamic AST)** — black-box test the running app. OWASP ZAP.
- **SCA (Software Composition Analysis)** — scan dependencies for known CVEs. Snyk, Dependabot, Renovate.
- **Image scanning** — scan container images. Trivy, Grype, Clair.
- **IaC scanning** — scan Terraform / K8s manifests for misconfig. tfsec, Checkov, Kubescape.
- **Secret scanning** — find leaked secrets in code/history. Gitleaks, TruffleHog.

### OWASP Top 10 (web app risks)

1. Broken access control
2. Cryptographic failures
3. Injection (SQLi, command injection)
4. Insecure design
5. Security misconfiguration
6. Vulnerable and outdated components
7. Identification and authentication failures
8. Software and data integrity failures
9. Security logging and monitoring failures
10. Server-side request forgery (SSRF)

### Supply chain attacks

Attacker compromises an upstream dependency (npm package, Docker image, GitHub Action). Mitigations:
- Pin dependencies by hash, not version.
- Sign images (cosign, sigstore).
- Generate SBOMs (Software Bill of Materials) with syft/cyclonedx.
- Audit third-party Actions/Plugins.

### Encryption

- **At rest** — encrypted on disk (EBS encryption, S3 SSE, etcd encryption).
- **In transit** — TLS everywhere, mTLS between services.
- **In use** — homomorphic encryption / SGX enclaves (rare, advanced).

### Key management

- **HSM (Hardware Security Module)** — physical/virtual device holding crypto keys. AWS CloudHSM, KMS.
- **KMS (Key Management Service)** — managed keys; you call KMS to encrypt/decrypt without seeing the key.
- **Envelope encryption** — encrypt data with a DEK (data encryption key), then encrypt the DEK with a KEK (key encryption key) in KMS.

### Zero Trust

"Never trust, always verify." Don't assume anything inside the network is safe. Authenticate + authorise every request. Identity-based instead of network-based perimeter.

---

## 13. RELIABILITY & SRE

### Reliability concepts

- **Availability** — uptime as a percentage. "Three nines" = 99.9% = 8.76 hours of downtime per year. "Five nines" = 99.999% = 5 minutes per year.
- **Durability** — data loss probability. S3 advertises 11 nines (a file lost every 10,000,000 years).
- **Latency** — request time. Usually expressed as p50/p95/p99.
- **Throughput** — work per unit time. Req/s, MB/s.

### Single Point of Failure (SPOF)

Any component whose failure brings the whole system down. Find and eliminate them with redundancy.

### Redundancy patterns

- **Active-passive** — backup waiting to take over. Failover triggers it.
- **Active-active** — both serve traffic; if one dies, the other absorbs.
- **Quorum** — N nodes; need majority to commit. (Raft, Paxos.)
- **Sharding** — partition data; each shard has its own redundancy.

### Replication

- **Synchronous** — write isn't acknowledged until all replicas confirm. Strong consistency, higher latency.
- **Asynchronous** — primary acknowledges; replicas catch up. Lower latency, possible data loss.

### CAP theorem

In a distributed system, you can only have two of:
- **Consistency** — all nodes see the same data at the same time.
- **Availability** — every request gets a response.
- **Partition tolerance** — system keeps working despite network splits.

Real systems trade C and A under partitions. Postgres = CP. DynamoDB = AP.

### Disaster Recovery

- **RPO (Recovery Point Objective)** — maximum acceptable data loss. "Up to 5 min."
- **RTO (Recovery Time Objective)** — maximum acceptable downtime. "Up to 1 hour."

Strategies:
- **Backup & restore** — slowest, cheapest.
- **Pilot light** — minimal infra always running.
- **Warm standby** — scaled-down full copy.
- **Multi-site active-active** — both regions live.

### Backups

- **3-2-1 rule** — 3 copies, 2 different media, 1 offsite.
- **Test restores** — backups you can't restore aren't backups.
- **Point-in-time recovery (PITR)** — restore to any second within a retention window. Standard for managed DBs.

### Chaos engineering

Deliberately inject failures in production to find weaknesses. Tools: **Chaos Monkey** (Netflix), **Chaos Mesh**, **Litmus**, **Gremlin**.

### Postmortems

After every incident:
1. What happened?
2. What was the impact?
3. What did we do to mitigate?
4. What was the root cause?
5. What will we change so it doesn't happen again?

**Blameless** — focus on systems, not individuals. The person who pushed the bad config isn't the problem; the system that let bad config reach prod is.

### Toil

> Manual, repetitive, automatable work with no enduring value.

SRE goal: keep toil below 50% of engineering time. The other 50% is engineering away the toil.

### Error budgets

If your SLO is 99.9%, you have a 0.1% "error budget." When you've burned through it, **stop pushing risky changes** and invest in reliability. This is how SRE balances velocity vs stability.

---

## 14. DATABASES

### Categories

- **Relational (SQL)** — tables, rows, schemas, ACID. Postgres, MySQL, SQL Server, Oracle.
- **Document** — JSON-like documents. MongoDB, CouchDB.
- **Key-value** — Redis, DynamoDB, etcd.
- **Wide-column** — Cassandra, ScyllaDB, HBase.
- **Graph** — Neo4j, Amazon Neptune.
- **Time-series** — Prometheus, InfluxDB, TimescaleDB.
- **Search** — Elasticsearch, OpenSearch.
- **Vector** — pgvector, Pinecone, Weaviate (for ML embeddings).

### ACID

- **Atomicity** — transaction is all-or-nothing.
- **Consistency** — DB constraints always hold.
- **Isolation** — concurrent transactions don't interfere.
- **Durability** — committed transactions survive crashes.

### BASE (NoSQL trade-off)

- **Basically Available**
- **Soft state**
- **Eventually consistent**

### Isolation levels (SQL standard)

| Level | Dirty read | Non-repeatable read | Phantom read |
|-------|-----------|----------------------|--------------|
| Read uncommitted | possible | possible | possible |
| Read committed | no | possible | possible |
| Repeatable read | no | no | possible |
| Serializable | no | no | no |

Postgres default: Read Committed. Higher levels cost more.

### Indexes

- **B-tree** — default. Good for equality + range.
- **Hash** — only equality.
- **GIN / GiST** — full-text, JSONB, arrays.
- **Composite** — multi-column.
- **Partial** — only some rows.

> Every index speeds up reads but slows writes. Index purposefully.

### Normalisation

- **1NF** — atomic columns.
- **2NF** — no partial dependencies on composite keys.
- **3NF** — no transitive dependencies.

In practice: normalise for correctness, denormalise for read performance.

### Replication

- **Primary-replica** (master-slave) — one writer, many readers.
- **Multi-primary** — multiple writers. Harder; conflict resolution needed.
- **Read replicas** — scale reads horizontally.

### Sharding (partitioning)

Split data across machines by some key. Hard to do well. Pick the shard key carefully — wrong key = hot spots.

### Connection pooling

Opening a DB connection is expensive (TCP + TLS + auth). Pool them. Tools: **PgBouncer** for Postgres, **HikariCP** for JVM, **SQLAlchemy** has built-in.

### Migrations

Version-controlled schema changes. Tools: **Alembic** (Python/SQLAlchemy), **Flyway** (Java), **Liquibase**, **golang-migrate**.

> Migrations must be backwards-compatible across one deploy — old code must work with new schema (expand) and new code must work with old data (until cleaned up). This is the "expand-and-contract" pattern.

### WAL / write-ahead log

Postgres writes every change to a log file before changing the data file. On crash, replay the log. This is also how replication works (stream the WAL).

---

## 15. WEB & APIs

### REST

REST = Representational State Transfer. Architectural style for HTTP APIs.

Properties:
- **Resource-oriented** — URLs identify nouns.
- **HTTP verbs** for actions (GET/POST/PUT/PATCH/DELETE).
- **Stateless** — server doesn't remember between requests.
- **Standard status codes** for responses.

Example:
```
GET    /api/v1/sims          # list
POST   /api/v1/sims          # create
GET    /api/v1/sims/123      # read one
PATCH  /api/v1/sims/123      # update
DELETE /api/v1/sims/123      # delete
```

### REST conventions

- Use plural nouns (`/sims`, not `/sim`).
- Nest related: `/sims/123/audit_events`.
- Filter via query string: `?status=ACTIVE&limit=20`.
- Version in URL: `/api/v1/...` (or in headers — both have fans).

### Other API styles

- **GraphQL** — single endpoint, client requests exactly the fields it wants. Good for flexible UIs.
- **gRPC** — RPC over HTTP/2 with Protobuf. Fast, strongly typed, hard to debug.
- **WebSocket** — bidirectional over a single TCP connection. For real-time.
- **SSE (Server-Sent Events)** — server pushes events over HTTP. Simpler than WebSocket for one-way.

### OpenAPI (formerly Swagger)

A YAML/JSON spec that describes a REST API. Tools generate docs, client SDKs, server stubs from it. FastAPI generates OpenAPI from your code.

### Idempotency

A request is idempotent if calling it N times has the same effect as calling it once. PUT, DELETE, GET should be idempotent. POST is typically not.

**Why it matters:** retries on flaky networks. If you don't know if the request succeeded, idempotent requests are safe to retry.

### Pagination

- **Offset/limit** — `?offset=20&limit=10`. Easy; slow on big tables.
- **Cursor-based** — `?after=<token>&limit=10`. Stable across inserts.
- **Keyset / seek** — `?after_id=12345&limit=10`. Fastest.

### Rate limiting

Cap requests per user/IP to prevent abuse. Algorithms:
- **Fixed window** — N reqs per minute, reset on the minute. Bursty.
- **Sliding window** — smooths bursts.
- **Token bucket** — refill at rate R, max burst B.
- **Leaky bucket** — smooth out spikes.

Return HTTP 429 Too Many Requests + `Retry-After` header.

### CORS (Cross-Origin Resource Sharing)

Browser security feature blocking JS on `evil.com` from calling `bank.com`. Server must explicitly allow origins via `Access-Control-Allow-Origin` header.

### Caching headers

- **Cache-Control: max-age=3600** — cache for 1 hour.
- **ETag** — fingerprint; client sends `If-None-Match`, server returns 304 Not Modified.
- **Last-Modified** + `If-Modified-Since`.
- **no-store** — don't cache at all (for sensitive responses).
- **CDN caches** respect these.

### Webhooks

A reverse API call. You give someone an HTTPS URL; they POST events to it. Examples: Stripe webhooks for payment events, GitHub webhooks for repo events.

Best practices: verify signatures, return fast (2xx), process async.

---

## 16. ALPHABETICAL GLOSSARY

**A/B testing** — show two variants to different user groups, measure which performs better.

**ABAC** (Attribute-Based Access Control) — permissions based on attributes (department, time of day, location). More flexible than RBAC.

**API Gateway** — front door for APIs: routes, authenticates, rate-limits.

**APM** (Application Performance Monitoring) — tracking app-level metrics (latency, errors, traces). New Relic, Datadog APM, Honeycomb.

**Argo CD** — GitOps tool for K8s.

**Artifact** — output of a build (jar, image, binary).

**Backup** — copy of data for restore. ≠ replication.

**Bastion host (jump box)** — gateway server for SSH'ing into private networks.

**Big-O** — algorithmic complexity. O(1), O(log n), O(n), O(n²).

**Blue-green deployment** — switch traffic between two parallel environments.

**Bolted-on observability** — bad pattern. Add metrics/logs/traces *while* building, not after.

**Branch protection** — git rule preventing direct pushes to `main`; requires PR + reviews + passing CI.

**Bucket** (S3 etc.) — top-level container for objects.

**Build artifact** — output of compile/package step.

**Cache hit ratio** — % of requests served from cache vs backend.

**Canary release** — route a small % of traffic to a new version.

**CDN** (Content Delivery Network) — geographically distributed cache for static assets. CloudFront, Cloudflare, Fastly.

**Cgroup** — Linux kernel feature to limit and account for resources.

**ChatOps** — operations via chat (Slack/Teams) — `/deploy prod`, `@bot scale api 10`.

**Checksum** — small fingerprint to detect corruption. SHA-256 etc.

**Cipher suite** — combo of algorithms TLS negotiates (key exchange, encryption, MAC).

**CIDR** — Classless Inter-Domain Routing notation: `10.0.0.0/16`.

**Circuit breaker** — pattern: stop calling a failing dependency for a while, let it recover.

**Cloud-native** — designed for cloud from day one — containers, microservices, declarative APIs.

**Cluster** — group of machines acting as one (K8s cluster, Postgres cluster, Redis cluster).

**Cold start** — slow first invocation (serverless, JVM startup).

**Compaction** — reorg data on disk (Cassandra, LSM trees).

**Compliance** — meeting regulations: SOC2, ISO 27001, PCI-DSS, HIPAA, GDPR.

**Configuration drift** — when actual config diverges from declared. IaC + GitOps prevent this.

**Container** — running instance of an image.

**Container runtime** — software that runs containers (containerd, CRI-O).

**Cookie** — small data the server asks the browser to store and resend.

**CSRF** (Cross-Site Request Forgery) — attacker tricks logged-in browser into making a request on the user's behalf.

**CSP** (Content Security Policy) — header restricting what resources a page can load.

**CSRF token** — random value tied to the session; required in forms.

**Daemon** — long-running background process.

**Data lake** — large pool of raw data (often S3 + Athena/Presto/Spark).

**Data warehouse** — structured, query-optimised analytic store. Snowflake, BigQuery, Redshift.

**Debounce** — collapse a burst of events into one (after N ms of quiet).

**Decoupling** — letting components evolve independently. Queues, events, well-defined APIs.

**Dependency injection** — pass dependencies in (vs creating them inside). Easier to test.

**Deprecation** — mark an API as outdated. Don't break it immediately — give consumers time.

**Deserialization** — turning bytes/JSON into objects. Common vuln source.

**DevSecOps** — security embedded in DevOps.

**DHCP** (Dynamic Host Configuration Protocol) — auto-assign IPs.

**Diff** — difference between two versions.

**Distributed lock** — lock across multiple processes/machines. Redis, ZooKeeper, etcd.

**DNS-01 challenge** — Let's Encrypt verification via TXT record (useful for wildcard certs).

**Docker layer caching** — image build optimisation.

**DSL** (Domain-Specific Language) — small language for one purpose (HCL for Terraform, Jenkinsfile Groovy).

**Eventual consistency** — given enough time without new updates, all replicas agree.

**Exponential backoff** — retry delay doubles each attempt.

**ETL / ELT** — Extract, Transform, Load (or Extract-Load-Transform). Data pipeline.

**Fanout** — one message → many consumers (pub/sub).

**Fault tolerance** — system keeps working despite component failures.

**Feature branch** — short-lived branch for one feature.

**FinOps** — financial operations. Optimising cloud spend.

**Forward proxy** — proxy for clients (outbound). vs reverse proxy (inbound).

**Function-as-a-Service** — serverless functions. Lambda, Cloud Functions.

**Garbage collection** — automatic memory reclamation. Tunable in JVM/Go/Python.

**GitOps** — git as the source of truth for infra/apps.

**GraphQL** — query language for APIs.

**Graceful shutdown** — finish in-flight requests before stopping.

**Hardening** — reduce attack surface (disable services, remove tools, enable security features).

**Hash** — function turning data into a fixed-size fingerprint.

**Health check** — endpoint reporting if the service is alive/ready.

**Heartbeat** — periodic "I'm alive" signal between nodes.

**Hot vs cold storage** — frequently-accessed vs rarely-accessed; cold is cheaper.

**HTTP/2, HTTP/3** — newer HTTP versions. HTTP/2 multiplexes streams over one TCP connection; HTTP/3 runs over QUIC (UDP).

**Idempotent** — calling N times = calling once.

**Immutable infrastructure** — never modify, always replace.

**Ingress** — incoming traffic; also K8s object for HTTP routing.

**Integration test** — tests interactions between components.

**JSON** — JavaScript Object Notation. Ubiquitous data format.

**JWT** — JSON Web Token. Signed token, self-contained.

**Kubernetes** — container orchestration platform. K8s = Kubernetes (K + 8 letters + s).

**Latency budget** — how much time you have. p95 must be < 200ms.

**Load balancer** — distributes traffic across many backends. L4 (TCP) or L7 (HTTP).

**Logical volume** — virtual disk on top of physical disks. LVM.

**Manifest** — declarative description (K8s YAML, Docker image manifest).

**Memcached** — simple in-memory cache (vs Redis which is more featureful).

**Metrics-server** — K8s component reporting pod/node metrics; powers HPA.

**Microservice** — small, independently-deployable service. Opposite of monolith.

**Migration** — versioned schema/data change.

**Monolith** — single large deployable.

**Multi-tenant** — one system serving many customers, isolated logically.

**Mutex** — mutual exclusion lock.

**Namespace** (Linux) — kernel isolation feature.

**Namespace** (K8s) — logical grouping inside a cluster.

**Network policy** (K8s) — pod-level firewall rules.

**Observability** — ability to ask new questions of a running system.

**OCI** (Open Container Initiative) — container standards.

**On-call rotation** — schedule of who responds to alerts.

**Operator** (K8s) — controller managing a domain via CRDs.

**Orchestration** — coordinating many containers/services. K8s.

**Patch** — small, targeted update.

**Payload** — data being transmitted.

**Persistent volume** — storage that survives pod restarts.

**Pinning** — locking a dependency to an exact version.

**Pod** — smallest K8s deployable unit.

**Polling** — repeatedly checking. Often replaced by webhooks/events for efficiency.

**Pre-commit hook** — git hook that runs before each commit (lint, format).

**Pre-receive hook** — server-side git hook.

**Preemptible / spot instance** — cheap compute that can be reclaimed.

**Progressive delivery** — canary + feature flags + observability-driven rollouts.

**Promotion** — moving an artifact from one env to the next (dev → staging → prod).

**Proxy** — intermediary that forwards traffic.

**Pull-based** — consumer fetches (Prometheus). vs push-based.

**Pull request (PR)** — proposal to merge code.

**Queue** — FIFO data structure. Decouples producers from consumers.

**Quota** — limit on resources (K8s ResourceQuota, AWS service quotas).

**RBAC** (Role-Based Access Control) — permissions by role.

**Race condition** — bug due to unsynchronised concurrent access.

**Reconciliation loop** — controller pattern: observe state, compare to desired, fix the diff.

**Redis** — in-memory data store. Cache, queue, pub/sub.

**Reentrant lock** — same thread can re-acquire its own lock.

**Refactor** — restructure code without changing behaviour.

**Region** — geographic cloud area.

**Replica** — copy of a pod / data.

**Repo** — repository (git).

**Reverse proxy** — proxy in front of backend servers. Nginx, Envoy, HAProxy.

**Rollback** — go back to the previous version.

**Rolling update** — replace pods/instances gradually.

**Round-robin** — load balancing algorithm: cycle through backends.

**Runbook** — step-by-step doc for handling an incident or task.

**Sandbox** — restricted execution environment.

**SAST / DAST / SCA** — see Security section.

**SBOM** (Software Bill of Materials) — inventory of components in a build.

**Schema** — structure of data (DB tables, JSON schema, OpenAPI).

**Secret rotation** — periodically changing secrets.

**Self-hosted runner** — your own machine running CI jobs.

**Semantic versioning (SemVer)** — `MAJOR.MINOR.PATCH`. Major = breaking change.

**Service discovery** — finding service instances dynamically. DNS, K8s Services, Consul.

**Service mesh** — sidecar-based infrastructure for service-to-service comms.

**Sharding** — partitioning data across machines.

**Sidecar** — helper container running alongside the main one (Envoy proxy, Vault agent).

**SLA / SLO / SLI** — see Observability.

**Smoke test** — quick post-deploy sanity check.

**Snapshot** — point-in-time copy of state (EBS snapshot, DB snapshot).

**SSH** — Secure Shell. Encrypted remote login.

**SSL** — old name for TLS.

**Stateless** — keeps no info between requests. Easy to scale horizontally.

**Stateful** — does keep state. Harder to scale.

**Sticky session** — load balancer pins a user to one backend.

**Subnet** — slice of a VPC.

**Sync vs async** — blocking vs non-blocking.

**TCP** — Transmission Control Protocol. Reliable, ordered.

**Telemetry** — metrics + logs + traces emitted by software.

**Tenant** — customer/org in a multi-tenant system.

**TLS** — Transport Layer Security.

**Toil** — see Reliability section.

**Token bucket** — rate-limit algorithm.

**TTL** (Time To Live) — how long something is valid (DNS, cache, K8s objects).

**UDP** — User Datagram Protocol. Unreliable, fast.

**Unit test** — tests one function/class in isolation.

**Upstream** — toward the source (upstream service, upstream branch).

**Uptime** — % of time the system is available.

**VPC** (Virtual Private Cloud) — isolated cloud network.

**Vault** — HashiCorp's secrets store.

**VLAN** — Virtual LAN. Layer-2 network segmentation.

**Vulnerability** — flaw that can be exploited.

**Warm standby** — DR pattern: scaled-down copy ready to scale up.

**Watchdog** — process that monitors others and restarts them on failure.

**Webhook** — incoming HTTP call triggered by an event.

**WebSocket** — bidirectional TCP-over-HTTP.

**Worker node** — K8s node running pods (vs control plane).

**X-Forwarded-For** — header showing original client IP behind a proxy.

**YAML** — Yet Another Markup Language. Indentation-sensitive config format.

**Zero-downtime deployment** — deploy without users noticing.

**Zone (DNS)** — set of DNS records for a domain.

**Zone (availability)** — see AZ.

---

## 17. ACRONYM CHEAT SHEET

### A
- **ACK** — Acknowledgement (TCP)
- **ACL** — Access Control List
- **AKS** — Azure Kubernetes Service
- **ALB** — Application Load Balancer (AWS, L7)
- **AMI** — Amazon Machine Image
- **API** — Application Programming Interface
- **APM** — Application Performance Monitoring
- **ARN** — Amazon Resource Name
- **ASG** — Auto Scaling Group
- **AZ** — Availability Zone

### B
- **BGP** — Border Gateway Protocol
- **BPMN** — Business Process Model and Notation

### C
- **CA** — Certificate Authority
- **CDN** — Content Delivery Network
- **CGI** — Common Gateway Interface (mostly historical)
- **CI/CD** — Continuous Integration / Delivery (or Deployment)
- **CIDR** — Classless Inter-Domain Routing
- **CLI** — Command-Line Interface
- **CNI** — Container Network Interface
- **CORS** — Cross-Origin Resource Sharing
- **CRD** — Custom Resource Definition
- **CRI** — Container Runtime Interface
- **CRL** — Certificate Revocation List
- **CRUD** — Create, Read, Update, Delete
- **CSI** — Container Storage Interface
- **CSP** — Content Security Policy / Cloud Service Provider
- **CSRF** — Cross-Site Request Forgery
- **CVE** — Common Vulnerabilities and Exposures

### D
- **DAG** — Directed Acyclic Graph
- **DBA** — Database Administrator
- **DDoS** — Distributed Denial of Service
- **DLP** — Data Loss Prevention
- **DLQ** — Dead-Letter Queue
- **DNS** — Domain Name System
- **DRY** — Don't Repeat Yourself
- **DSL** — Domain-Specific Language

### E
- **EBS** — Elastic Block Store (AWS)
- **EC2** — Elastic Compute Cloud (AWS)
- **ECR** — Elastic Container Registry (AWS)
- **ECS** — Elastic Container Service (AWS)
- **EFS** — Elastic File System (AWS)
- **EKS** — Elastic Kubernetes Service (AWS)
- **ELB** — Elastic Load Balancer (AWS, generic)
- **ELK** — Elasticsearch, Logstash, Kibana

### F
- **FIPS** — Federal Information Processing Standards
- **FQDN** — Fully Qualified Domain Name
- **FUSE** — Filesystem in Userspace

### G
- **GC** — Garbage Collection
- **GCP** — Google Cloud Platform
- **GKE** — Google Kubernetes Engine
- **GUI** — Graphical User Interface

### H
- **HA** — High Availability
- **HCL** — HashiCorp Configuration Language
- **HMAC** — Hash-based Message Authentication Code
- **HPA** — Horizontal Pod Autoscaler
- **HSM** — Hardware Security Module
- **HTTPS** — HTTP Secure

### I
- **IaC** — Infrastructure as Code
- **IAM** — Identity and Access Management
- **ICMP** — Internet Control Message Protocol (ping)
- **IDS** — Intrusion Detection System
- **IDE** — Integrated Development Environment
- **IMDS** — Instance Metadata Service (AWS)
- **IOPS** — Input/Output Operations per Second
- **IP** — Internet Protocol
- **IPS** — Intrusion Prevention System
- **IRSA** — IAM Roles for Service Accounts
- **ISP** — Internet Service Provider

### J
- **JIT** — Just-In-Time (compilation)
- **JSON** — JavaScript Object Notation
- **JVM** — Java Virtual Machine
- **JWT** — JSON Web Token

### K
- **K8s** — Kubernetes
- **KMS** — Key Management Service
- **KPI** — Key Performance Indicator

### L
- **LB** — Load Balancer
- **LDAP** — Lightweight Directory Access Protocol
- **LRU** — Least Recently Used (cache eviction)

### M
- **MFA** — Multi-Factor Authentication
- **MITM** — Man In The Middle
- **MTLS** — Mutual TLS
- **MTBF** — Mean Time Between Failures
- **MTTR** — Mean Time To Recover

### N
- **NAT** — Network Address Translation
- **NFS** — Network File System
- **NLB** — Network Load Balancer (AWS, L4)
- **NoSQL** — Non-SQL / Not Only SQL
- **NTP** — Network Time Protocol

### O
- **OAuth** — Open Authorization
- **OCI** — Open Container Initiative
- **OIDC** — OpenID Connect
- **OOM** — Out Of Memory
- **OS** — Operating System
- **OTEL** — OpenTelemetry

### P
- **PaaS** — Platform as a Service
- **PCI-DSS** — Payment Card Industry Data Security Standard
- **PDB** — Pod Disruption Budget
- **PII** — Personally Identifiable Information
- **PITR** — Point-In-Time Recovery
- **PKI** — Public Key Infrastructure
- **POP** — Point of Presence
- **PR** — Pull Request
- **PV / PVC** — Persistent Volume / Claim

### Q
- **QPS** — Queries Per Second
- **QoS** — Quality of Service

### R
- **RAID** — Redundant Array of Independent Disks
- **RBAC** — Role-Based Access Control
- **RCE** — Remote Code Execution
- **RDS** — Relational Database Service (AWS)
- **REPL** — Read-Eval-Print Loop
- **REST** — Representational State Transfer
- **RFC** — Request For Comments
- **RPC** — Remote Procedure Call
- **RPO** — Recovery Point Objective
- **RPS** — Requests Per Second
- **RTO** — Recovery Time Objective

### S
- **S3** — Simple Storage Service (AWS)
- **SaaS** — Software as a Service
- **SAST** — Static Application Security Testing
- **SBOM** — Software Bill of Materials
- **SCA** — Software Composition Analysis
- **SDLC** — Software Development Lifecycle
- **SG** — Security Group (AWS)
- **SLA / SLO / SLI** — see Observability
- **SMTP** — Simple Mail Transfer Protocol
- **SNI** — Server Name Indication (TLS)
- **SOC2** — Service Organization Control 2 (audit)
- **SPA** — Single-Page Application
- **SPOF** — Single Point of Failure
- **SQL** — Structured Query Language
- **SRE** — Site Reliability Engineering
- **SSH** — Secure Shell
- **SSL** — Secure Sockets Layer (now TLS)
- **SSO** — Single Sign-On
- **SSRF** — Server-Side Request Forgery
- **STS** — Security Token Service (AWS)

### T
- **TCP** — Transmission Control Protocol
- **TLD** — Top-Level Domain
- **TLS** — Transport Layer Security
- **TSDB** — Time-Series Database
- **TTL** — Time To Live

### U
- **UDP** — User Datagram Protocol
- **UID / GID** — User / Group ID (Linux)
- **URL / URI** — Uniform Resource Locator / Identifier
- **UUID** — Universally Unique Identifier

### V
- **VLAN** — Virtual LAN
- **VM** — Virtual Machine
- **VPC** — Virtual Private Cloud
- **VPN** — Virtual Private Network

### W
- **WAF** — Web Application Firewall
- **WAL** — Write-Ahead Log
- **WSGI / ASGI** — Web / Async Server Gateway Interface (Python)

### X / Y / Z
- **XML** — eXtensible Markup Language
- **XSS** — Cross-Site Scripting
- **YAML** — YAML Ain't Markup Language

---

## CLOSING — HOW TO USE THIS DOCUMENT

1. **Read top to bottom once** — even sections that feel basic. The vocabulary builds on itself.
2. **Bookmark the glossary** — when a term comes up at work or in a paper, look it up here.
3. **Pair with hands-on practice** — read the K8s section, then `minikube start` and try it.
4. **Add to it** — when you learn something new, write your own definition here. Active recall beats passive reading.
5. **Don't memorise; understand** — the field has 100x more acronyms than this list. The point is patterns, not vocabulary.

Most DevOps knowledge is **breadth, not depth**. You don't need to be a Postgres internals expert, a kernel hacker, AND a K8s contributor. You need enough vocabulary to *understand* what the experts are saying and *recognise* when you need them.

Good luck.
