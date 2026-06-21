output "vpc_id" {
  value       = module.vpc.vpc_id
  description = "Primary VPC ID"
}

output "private_subnet_ids" {
  value = module.vpc.private_subnet_ids
}

output "public_subnet_ids" {
  value = module.vpc.public_subnet_ids
}

output "cluster_name" {
  value = module.eks.cluster_name
}

output "cluster_endpoint" {
  value     = module.eks.cluster_endpoint
  sensitive = true
}

output "cluster_oidc_issuer_url" {
  value = module.eks.oidc_issuer_url
}

output "kubeconfig_command" {
  value = "aws eks update-kubeconfig --region ${var.region} --name ${module.eks.cluster_name}"
}

output "rds_endpoint" {
  value     = module.rds.endpoint
  sensitive = true
}

output "rds_port" {
  value = module.rds.port
}

output "alb_ingress_class" {
  value       = "alb"
  description = "Ingress class to use in Kubernetes ALB ingress resources"
}
