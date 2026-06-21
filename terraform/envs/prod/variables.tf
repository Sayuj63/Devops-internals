variable "project" {
  description = "Project slug used for naming and tagging"
  type        = string
  default     = "sim-prov"
}

variable "environment" {
  description = "Environment name (prod, staging, dev)"
  type        = string
  default     = "prod"
}

variable "region" {
  description = "AWS region"
  type        = string
  default     = "ap-south-1"
}

variable "vpc_cidr" {
  description = "Primary VPC CIDR"
  type        = string
  default     = "10.40.0.0/16"
}

variable "availability_zones" {
  description = "Availability zones to spread subnets across (must be 3)"
  type        = list(string)
  default     = ["ap-south-1a", "ap-south-1b", "ap-south-1c"]
  validation {
    condition     = length(var.availability_zones) == 3
    error_message = "Exactly three AZs are required for HA."
  }
}

variable "eks_version" {
  description = "EKS Kubernetes version"
  type        = string
  default     = "1.29"
}

variable "eks_node_instance_types" {
  description = "Instance types for the managed node group"
  type        = list(string)
  default     = ["t3.large"]
}

variable "eks_node_min_size" {
  type    = number
  default = 3
}

variable "eks_node_desired_size" {
  type    = number
  default = 3
}

variable "eks_node_max_size" {
  type    = number
  default = 6
}

variable "db_name" {
  type    = string
  default = "simprov"
}

variable "db_username" {
  type    = string
  default = "simprov"
}

variable "db_password" {
  description = "RDS master password — sourced from Vault by the pipeline"
  type        = string
  sensitive   = true
}

variable "db_instance_class" {
  type    = string
  default = "db.t3.medium"
}

variable "db_allocated_storage" {
  type    = number
  default = 50
}

variable "db_backup_retention_days" {
  type    = number
  default = 7
}

variable "tags" {
  description = "Extra tags applied to every resource"
  type        = map(string)
  default = {
    Owner       = "sayuj@itm-skills.edu.in"
    CostCenter  = "telco-platform"
    Compliance  = "trai-gdpr"
    ManagedBy   = "terraform"
  }
}
