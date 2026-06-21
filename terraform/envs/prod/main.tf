locals {
  name = "${var.project}-${var.environment}"

  tags = merge(var.tags, {
    Project     = var.project
    Environment = var.environment
  })
}

provider "aws" {
  region = var.region
  default_tags { tags = local.tags }
}

module "vpc" {
  source = "../../modules/vpc"

  name                = local.name
  cidr                = var.vpc_cidr
  availability_zones  = var.availability_zones
  cluster_name        = local.name
  flow_logs_retention = 30
  tags                = local.tags
}

module "eks" {
  source = "../../modules/eks"

  name               = local.name
  kubernetes_version = var.eks_version
  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.private_subnet_ids

  node_instance_types = var.eks_node_instance_types
  node_min_size       = var.eks_node_min_size
  node_desired_size   = var.eks_node_desired_size
  node_max_size       = var.eks_node_max_size

  tags = local.tags
}

module "rds" {
  source = "../../modules/rds"

  name                 = local.name
  vpc_id               = module.vpc.vpc_id
  subnet_ids           = module.vpc.private_subnet_ids
  allowed_security_group_ids = [module.eks.node_security_group_id]

  db_name              = var.db_name
  username             = var.db_username
  password             = var.db_password
  instance_class       = var.db_instance_class
  allocated_storage    = var.db_allocated_storage
  backup_retention_days = var.db_backup_retention_days

  tags = local.tags
}
