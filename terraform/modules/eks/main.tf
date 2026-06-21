###############################################################################
# Module: eks
# Managed EKS cluster (1.29 default), 1 managed node group, IRSA OIDC provider,
# core add-ons (vpc-cni, coredns, kube-proxy, aws-ebs-csi-driver), and an
# aws-auth ConfigMap mapping the node IAM role.
###############################################################################

data "aws_partition"          "current" {}
data "aws_caller_identity"    "current" {}
data "tls_certificate"        "eks_oidc" { url = aws_eks_cluster.this.identity[0].oidc[0].issuer }

###############################################################################
# IAM
###############################################################################

data "aws_iam_policy_document" "eks_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["eks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "cluster" {
  name               = "${var.name}-cluster"
  assume_role_policy = data.aws_iam_policy_document.eks_assume.json
  tags               = var.tags
}

resource "aws_iam_role_policy_attachment" "cluster_managed" {
  for_each = toset([
    "arn:${data.aws_partition.current.partition}:iam::aws:policy/AmazonEKSClusterPolicy",
    "arn:${data.aws_partition.current.partition}:iam::aws:policy/AmazonEKSVPCResourceController",
  ])
  role       = aws_iam_role.cluster.name
  policy_arn = each.value
}

data "aws_iam_policy_document" "node_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "node" {
  name               = "${var.name}-node"
  assume_role_policy = data.aws_iam_policy_document.node_assume.json
  tags               = var.tags
}

resource "aws_iam_role_policy_attachment" "node_managed" {
  for_each = toset([
    "arn:${data.aws_partition.current.partition}:iam::aws:policy/AmazonEKSWorkerNodePolicy",
    "arn:${data.aws_partition.current.partition}:iam::aws:policy/AmazonEKS_CNI_Policy",
    "arn:${data.aws_partition.current.partition}:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly",
    "arn:${data.aws_partition.current.partition}:iam::aws:policy/AmazonSSMManagedInstanceCore",
  ])
  role       = aws_iam_role.node.name
  policy_arn = each.value
}

###############################################################################
# Cluster
###############################################################################

resource "aws_security_group" "cluster" {
  name        = "${var.name}-cluster-sg"
  description = "EKS control plane to node communication"
  vpc_id      = var.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, { Name = "${var.name}-cluster-sg" })
}

resource "aws_cloudwatch_log_group" "cluster" {
  name              = "/aws/eks/${var.name}/cluster"
  retention_in_days = 30
  tags              = var.tags
}

resource "aws_eks_cluster" "this" {
  name     = var.name
  role_arn = aws_iam_role.cluster.arn
  version  = var.kubernetes_version

  vpc_config {
    subnet_ids              = var.subnet_ids
    endpoint_public_access  = var.endpoint_public_access
    endpoint_private_access = true
    public_access_cidrs     = var.endpoint_public_access_cidrs
    security_group_ids      = [aws_security_group.cluster.id]
  }

  enabled_cluster_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  depends_on = [
    aws_iam_role_policy_attachment.cluster_managed,
    aws_cloudwatch_log_group.cluster,
  ]

  tags = var.tags
}

resource "aws_iam_openid_connect_provider" "eks" {
  url             = aws_eks_cluster.this.identity[0].oidc[0].issuer
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.eks_oidc.certificates[0].sha1_fingerprint]
  tags            = var.tags
}

###############################################################################
# Managed node group
###############################################################################

resource "aws_eks_node_group" "default" {
  cluster_name    = aws_eks_cluster.this.name
  node_group_name = "${var.name}-ng-default"
  node_role_arn   = aws_iam_role.node.arn
  subnet_ids      = var.subnet_ids
  instance_types  = var.node_instance_types
  capacity_type   = "ON_DEMAND"
  ami_type        = "AL2_x86_64"

  scaling_config {
    min_size     = var.node_min_size
    desired_size = var.node_desired_size
    max_size     = var.node_max_size
  }

  update_config { max_unavailable = 1 }

  labels = {
    "workload"      = "sim-prov"
    "node.kubernetes.io/lifecycle" = "on-demand"
  }

  lifecycle { ignore_changes = [scaling_config[0].desired_size] }

  depends_on = [aws_iam_role_policy_attachment.node_managed]
  tags       = var.tags
}

###############################################################################
# Cluster add-ons
###############################################################################

resource "aws_eks_addon" "core" {
  for_each = {
    "vpc-cni"            = "OVERWRITE"
    "coredns"            = "OVERWRITE"
    "kube-proxy"         = "OVERWRITE"
    "aws-ebs-csi-driver" = "OVERWRITE"
  }
  cluster_name             = aws_eks_cluster.this.name
  addon_name               = each.key
  resolve_conflicts_on_update = each.value
  resolve_conflicts_on_create = "OVERWRITE"
  depends_on               = [aws_eks_node_group.default]
  tags                     = var.tags
}

###############################################################################
# aws-auth ConfigMap — minimum mapping for the node IAM role
###############################################################################

provider "kubernetes" {
  host                   = aws_eks_cluster.this.endpoint
  cluster_ca_certificate = base64decode(aws_eks_cluster.this.certificate_authority[0].data)
  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    command     = "aws"
    args        = ["eks", "get-token", "--cluster-name", aws_eks_cluster.this.name]
  }
}

resource "kubernetes_config_map_v1_data" "aws_auth" {
  metadata {
    name      = "aws-auth"
    namespace = "kube-system"
  }
  force = true
  data = {
    mapRoles = yamlencode([
      {
        rolearn  = aws_iam_role.node.arn
        username = "system:node:{{EC2PrivateDNSName}}"
        groups   = ["system:bootstrappers", "system:nodes"]
      }
    ])
  }
  depends_on = [aws_eks_node_group.default]
}
