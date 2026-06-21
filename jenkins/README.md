# Jenkins pipeline

Declarative pipeline for the SIM Provisioning Automation Platform.

## Agent requirements

- A Linux agent labelled `docker` with Docker 24+, `kubectl` 1.29+, and `curl` available on `PATH`.
- Outbound network access to the container registry, Vault, and target Kubernetes clusters.

## Required Jenkins credentials

| Credential ID         | Kind                 | Used for                                                |
| --------------------- | -------------------- | ------------------------------------------------------- |
| `docker-registry`     | Username + password  | `docker login` to `ghcr.io/itm-skills/sim-prov`        |
| `kubeconfig-staging`  | Secret file          | `kubectl` against the staging EKS cluster              |
| `kubeconfig-prod`     | Secret file          | `kubectl` against the production EKS cluster           |
| `vault-token`         | Secret text          | Vault auth for fetching deploy-time secrets            |
| `slack-webhook`       | Secret text          | Incoming webhook URL for `#sim-prov-cicd`              |

## Stage map

1. Checkout
2. Quality gates (parallel) — `ruff`, `hadolint`, `pytest + coverage`
3. Build images (parallel) — `api`, `worker`, `mock-hlr`, `frontend`
4. Security scan — `trivy image` (HIGH, CRITICAL, ignore-unfixed)
5. Push to registry — only on `main` or `v*` tag
6. Deploy to staging via `kustomize build k8s/overlays/staging`
7. Smoke test (`scripts/smoke-test.sh`)
8. Manual approval (30 minute timeout)
9. Deploy to production via `kustomize build k8s/overlays/prod`
10. Slack notification (success / failure / unstable)

## Branch behaviour

- Pull request: stages 1-4 only.
- `main`: full pipeline through production with manual approval gate.
- Tags `v*`: build + push only (release pipeline picks up artefacts).
