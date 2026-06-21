variable "name" {
  type        = string
  description = "Base name for RDS resources"
}

variable "vpc_id" {
  type = string
}

variable "subnet_ids" {
  type        = list(string)
  description = "Private subnets for the DB subnet group"
}

variable "allowed_security_group_ids" {
  type        = list(string)
  description = "Security group IDs allowed to reach Postgres on 5432"
}

variable "db_name" {
  type    = string
  default = "simprov"
}

variable "username" {
  type    = string
  default = "simprov"
}

variable "password" {
  type      = string
  sensitive = true
}

variable "instance_class" {
  type    = string
  default = "db.t3.medium"
}

variable "engine_version" {
  type    = string
  default = "15.7"
}

variable "allocated_storage" {
  type    = number
  default = 50
}

variable "max_allocated_storage" {
  type    = number
  default = 200
}

variable "backup_retention_days" {
  type    = number
  default = 7
}

variable "deletion_protection" {
  type    = bool
  default = true
}

variable "tags" {
  type    = map(string)
  default = {}
}
