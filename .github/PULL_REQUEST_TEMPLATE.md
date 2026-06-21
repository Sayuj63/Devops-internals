## Summary

<!-- 2-3 sentences. What changes, and *why*. Link issues with "Closes #123". -->

## Test plan

- [ ] Unit tests pass locally (`make test`)
- [ ] `docker compose up` builds and `make smoke` passes
- [ ] `terraform plan` is clean (if `terraform/` changed)
- [ ] `kustomize build k8s/overlays/prod | kubeconform -` is clean (if `k8s/` changed)
- [ ] New Prometheus alerts have `summary`, `description`, and `runbook_url` (if `monitoring/` changed)
- [ ] Manual verification steps:

## Risk

<!-- Blast radius if this regresses. One of: low / medium / high. Note: data-loss risk, customer-facing risk, security risk. -->

## Rollback

<!-- How to revert. Specific commands, not "git revert". e.g. "redeploy previous tag v1.4.2 via Jenkins job sim-prov-deploy-prod". -->

## Screenshots / evidence

<!-- Required for UI changes, dashboards, alerts. -->
