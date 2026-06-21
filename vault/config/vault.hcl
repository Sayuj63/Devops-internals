ui            = true
disable_mlock = true
cluster_name  = "sim-prov-vault"

# Local dev / docker-compose uses file storage. For production, switch to
# integrated raft storage with KMS auto-unseal (see vault/README.md).
storage "file" {
  path = "/vault/file"
}

# Production sketch (left commented for the demo cluster):
# storage "raft" {
#   path    = "/vault/data"
#   node_id = "vault-1"
#   retry_join { leader_api_addr = "https://vault-0.vault.svc:8200" }
# }
# seal "awskms" {
#   region     = "ap-south-1"
#   kms_key_id = "alias/sim-prov-vault-unseal"
# }

listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = 1
}

api_addr     = "http://0.0.0.0:8200"
cluster_addr = "http://0.0.0.0:8201"

# Telemetry into Prometheus.
telemetry {
  prometheus_retention_time = "30s"
  disable_hostname          = true
}

# Auditing — file sink rotated by the platform.
# audit { type = "file" path = "/vault/logs/audit.log" }
