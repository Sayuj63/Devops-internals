# Vault — secrets for SIM Provisioning

## What lives where

```
vault/
  config/vault.hcl                ← server config (dev file storage; prod = raft + KMS)
  policies/sim-prov-api.hcl       ← API read-only access to db/hlr/jwt
  policies/sim-prov-worker.hcl    ← Worker access incl. audit-signing key
  scripts/bootstrap.sh            ← One-shot seed/policy/role wiring
```

## Local (docker-compose)

The docker-compose Vault runs in dev mode with `VAULT_DEV_ROOT_TOKEN_ID=root-dev-token`.
Bootstrap once after the stack is up:

```bash
export VAULT_ADDR=http://127.0.0.1:8200
export VAULT_TOKEN=root-dev-token
./vault/scripts/bootstrap.sh
```

## Production unseal — Shamir 5-of-3 with KMS auto-unseal as future state

1. Initialise the cluster on first start:

   ```bash
   vault operator init -key-shares=5 -key-threshold=3 -format=json > /secure/init.json
   ```

   The output contains 5 unseal key shards and the initial root token.
   Distribute one shard each to: SRE on-call, platform lead, security lead,
   CTO escrow, and offline cold storage (printed, vault).

2. Unseal three of five operators must run on each pod after a restart:

   ```bash
   vault operator unseal <shard-1>
   vault operator unseal <shard-2>
   vault operator unseal <shard-3>
   ```

3. **Target state — KMS auto-unseal** (already sketched in `config/vault.hcl`):
   enable the `awskms` seal stanza, migrate with
   `vault operator unseal -migrate`, and the cluster will recover automatically
   on pod restarts. Shamir shards remain as a break-glass recovery key.

## Day-2 operations

- Rotate the HLR API key:
  `vault kv put secret/sim-prov/hlr api_key="$(openssl rand -hex 24)" endpoint=...`
  Workers pick up the new value within `ttl` (1h).
- Audit log: enable `vault audit enable file file_path=/vault/logs/audit.log`.
- Backups: `vault operator raft snapshot save /backup/vault-$(date +%F).snap` daily,
  shipped to S3 cross-region.
