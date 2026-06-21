# Kubernetes manifests

Kustomize layout for the SIM Provisioning Automation Platform.

```
k8s/
  base/                ← canonical resources, namespace-scoped to sim-prov
  overlays/prod/       ← production overrides (replicas, host, image tags)
```

## Apply order

1. **Cluster prerequisites** (one-time per cluster):
   - `ingress-nginx` namespace (or AWS Load Balancer Controller) installed
   - `vault` namespace with Vault server + agent injector running
   - Vault Kubernetes auth method enabled, roles `sim-prov-api` and
     `sim-prov-worker` created (see `vault/scripts/bootstrap.sh`)
   - `monitoring` namespace with Prometheus deployed and labelled
     `app.kubernetes.io/name=prometheus`

2. **Render and apply**:

   ```bash
   kustomize build k8s/overlays/prod | kubectl apply -f -
   kubectl -n sim-prov rollout status deploy/api
   kubectl -n sim-prov rollout status deploy/worker
   kubectl -n sim-prov rollout status deploy/frontend
   ```

3. **Verify** with `scripts/smoke-test.sh` against the ingress hostname.

## What ships in base

| File                          | Purpose                                                      |
| ----------------------------- | ------------------------------------------------------------ |
| `namespace.yaml`              | Namespace + ResourceQuota + LimitRange + PodSecurity labels |
| `serviceaccount.yaml`         | IRSA + Vault annotations per workload                       |
| `configmap.yaml`              | Non-secret runtime config                                    |
| `api-deployment.yaml`         | API Deployment w/ Vault injector, probes, securityContext   |
| `api-service.yaml`            | ClusterIP for HTTP + metrics                                |
| `api-hpa.yaml`                | HPA (CPU 70%, memory 80%), 3-12 replicas                    |
| `api-pdb.yaml`                | PodDisruptionBudget minAvailable=2                          |
| `api-networkpolicy.yaml`      | Ingress from nginx/prometheus, egress to DB/Vault/HLR       |
| `worker-deployment.yaml`      | Async worker, no Service                                    |
| `mock-hlr-deployment.yaml`    | Mock HLR sidecar Deployment + Service                       |
| `frontend-deployment.yaml`    | Nginx-served static frontend                                |
| `ingress.yaml`                | AWS ALB ingress (HTTPS, HTTP→HTTPS redirect)                |

## Validation

```bash
kustomize build k8s/overlays/prod | kubeconform -strict -summary -
```
