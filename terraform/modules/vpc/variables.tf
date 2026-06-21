variable "name" {
  type        = string
  description = "Base name for VPC resources"
}

variable "cidr" {
  type        = string
  description = "VPC CIDR block (/16 recommended)"
}

variable "availability_zones" {
  type        = list(string)
  description = "AZs (3) for public/private subnet pairs"
}

variable "cluster_name" {
  type        = string
  description = "EKS cluster name used for subnet tagging"
}

variable "flow_logs_retention" {
  type        = number
  default     = 30
  description = "Days to retain VPC flow logs"
}

variable "tags" {
  type        = map(string)
  default     = {}
  description = "Tags applied to all resources"
}
