#!/usr/bin/env bash
# Bootstrap Vault for the SIM Provisioning platform.
#   * enables kv-v2 at secret/
#   * seeds db, hlr, jwt, audit-signing secrets
#   * writes sim-prov-api and sim-prov-worker policies
#   * enables Kubernetes auth and binds the workload service accounts
#
# Idempotent — safe to re-run.

set -Eeuo pipefail

: "${VAULT_ADDR:?must be set (e.g. http://127.0.0.1:8200)}"
: "${VAULT_TOKEN:?must be set (root or an admin token)}"
POLICY_DIR="${POLICY_DIR:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../policies" && pwd)}"

K8S_HOST="${K8S_HOST:-https://kubernetes.default.svc:443}"
K8S_CA_CERT="${K8S_CA_CERT:-/var/run/secrets/kubernetes.io/serviceaccount/ca.crt}"
K8S_TOKEN_REVIEWER_JWT="${K8S_TOKEN_REVIEWER_JWT:-}"
NS="${NS:-sim-prov}"

require() { command -v "$1" >/dev/null || { echo "missing dependency: $1" >&2; exit 1; }; }
require vault
require curl

log() { printf '\033[1;36m▶\033[0m %s\n' "$*"; }

###############################################################################
# 1. KV-v2 secrets engine
###############################################################################
if ! vault secrets list -format=json | grep -q '"secret/"'; then
  log "Enabling kv-v2 at secret/"
  vault secrets enable -path=secret -version=2 kv
else
  log "kv-v2 already enabled at secret/"
fi

###############################################################################
# 2. Seed secrets (only if missing — never overwrite live creds)
###############################################################################
seed_if_missing() {
  local path="$1"; shift
  if vault kv get "$path" >/dev/null 2>&1; then
    log "secret $path already exists — skipping"
  else
    log "Seeding $path"
    vault kv put "$path" "$@"
  fi
}

seed_if_missing secret/sim-prov/db \
  host="sim-prov-pg.cluster-ro.ap-south-1.rds.amazonaws.com" \
  port="5432" \
  dbname="simprov" \
  username="simprov" \
  password="$(LC_ALL=C tr -dc 'A-Za-z0-9!@#%^_+=' </dev/urandom | head -c 32)"

seed_if_missing secret/sim-prov/hlr \
  endpoint="http://mock-hlr:9000" \
  api_key="$(LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c 48)"

seed_if_missing secret/sim-prov/jwt \
  signing_key="$(LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c 64)" \
  algorithm="HS256"

seed_if_missing secret/sim-prov/audit-signing \
  key="$(LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c 64)"

###############################################################################
# 3. Policies
###############################################################################
for p in sim-prov-api sim-prov-worker; do
  log "Writing policy $p"
  vault policy write "$p" "${POLICY_DIR}/${p}.hcl"
done

###############################################################################
# 4. Kubernetes auth
###############################################################################
if ! vault auth list -format=json | grep -q '"kubernetes/"'; then
  log "Enabling Kubernetes auth"
  vault auth enable kubernetes
fi

log "Configuring Kubernetes auth backend"
vault write auth/kubernetes/config \
  kubernetes_host="${K8S_HOST}" \
  kubernetes_ca_cert=@"${K8S_CA_CERT}" \
  ${K8S_TOKEN_REVIEWER_JWT:+token_reviewer_jwt="${K8S_TOKEN_REVIEWER_JWT}"} \
  disable_local_ca_jwt=false

log "Binding role sim-prov-api → SA ${NS}/sim-prov-api"
vault write auth/kubernetes/role/sim-prov-api \
  bound_service_account_names=sim-prov-api \
  bound_service_account_namespaces="${NS}" \
  policies=sim-prov-api \
  ttl=1h max_ttl=24h

log "Binding role sim-prov-worker → SA ${NS}/sim-prov-worker"
vault write auth/kubernetes/role/sim-prov-worker \
  bound_service_account_names=sim-prov-worker \
  bound_service_account_namespaces="${NS}" \
  policies=sim-prov-worker \
  ttl=1h max_ttl=24h

log "Done. Vault is configured for sim-prov."
