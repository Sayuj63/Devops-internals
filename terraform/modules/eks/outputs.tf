output "cluster_name" {
  value = aws_eks_cluster.this.name
}

output "cluster_endpoint" {
  value     = aws_eks_cluster.this.endpoint
  sensitive = true
}

output "cluster_certificate_authority" {
  value     = aws_eks_cluster.this.certificate_authority[0].data
  sensitive = true
}

output "cluster_security_group_id" {
  value = aws_security_group.cluster.id
}

output "node_iam_role_arn" {
  value = aws_iam_role.node.arn
}

output "node_security_group_id" {
  value       = aws_eks_cluster.this.vpc_config[0].cluster_security_group_id
  description = "EKS-managed shared security group attached to nodes — use as ingress source for data plane"
}

output "oidc_issuer_url" {
  value = aws_iam_openid_connect_provider.eks.url
}

output "oidc_provider_arn" {
  value = aws_iam_openid_connect_provider.eks.arn
}
