# Policy: sim-prov-api
# Read-only access to the secrets the FastAPI service needs at boot.

path "secret/data/sim-prov/db" {
  capabilities = ["read"]
}

path "secret/data/sim-prov/hlr" {
  capabilities = ["read"]
}

path "secret/data/sim-prov/jwt" {
  capabilities = ["read"]
}

# Allow the app to refresh its own token before expiry.
path "auth/token/renew-self" {
  capabilities = ["update"]
}

path "auth/token/lookup-self" {
  capabilities = ["read"]
}
