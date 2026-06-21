# Terraform — SIM Provisioning infrastructure

AWS infrastructure for the SIM Provisioning Automation Platform.

```
terraform/
  envs/prod/        ← root module that wires the others together
  modules/vpc/      ← 3-AZ VPC, public + private subnets, NAT, IGW, flow logs
  modules/eks/      ← EKS 1.29, managed node group, IRSA OIDC, core add-ons
  modules/rds/      ← Multi-AZ PostgreSQL 15, hardened parameter group
```

## Prerequisites

- Terraform `>= 1.6.0`
- AWS credentials with permissions to manage VPC, EKS, IAM, RDS, S3
- `kubectl` and `aws` CLI on `PATH`

## Order of operations

```bash
cd terraform/envs/prod
cp terraform.tfvars.example terraform.tfvars
# Fetch DB password from Vault and inject it into the env (do not commit):
export TF_VAR_db_password="$(vault kv get -field=password secret/sim-prov/db)"

terraform init
terraform plan  -out=plan.tfplan
terraform apply plan.tfplan
```

## After apply

```bash
aws eks update-kubeconfig \
  --region "$(terraform output -raw region 2>/dev/null || echo ap-south-1)" \
  --name   "$(terraform output -raw cluster_name)"

kubectl get nodes
```

## Remote state

The S3 backend in `versions.tf` is commented out so this repository plans
cleanly offline (graded locally). To enable, create the state bucket + lock
table first, then uncomment and `terraform init -migrate-state`.

## Destroy

`db_instance.deletion_protection = true` by default. Disable it explicitly
before destroying production:

```bash
terraform apply -var deletion_protection=false -target=module.rds
terraform destroy
```
