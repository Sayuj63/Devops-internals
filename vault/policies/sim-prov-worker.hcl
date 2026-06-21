# Policy: sim-prov-worker
# The worker writes audit events and rotates the HLR API key, so it has
# slightly broader access than the API.

path "secret/data/sim-prov/db" {
  capabilities = ["read"]
}

path "secret/data/sim-prov/hlr" {
  capabilities = ["read", "update"]
}

path "secret/data/sim-prov/audit-signing" {
  capabilities = ["read"]
}

path "auth/token/renew-self"  { capabilities = ["update"] }
path "auth/token/lookup-self" { capabilities = ["read"]   }
