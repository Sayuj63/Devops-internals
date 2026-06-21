###############################################################################
# Module: rds
# Multi-AZ PostgreSQL 15, encrypted, with a hardened parameter group and a
# security group restricted to the supplied EKS node SG.
###############################################################################

resource "aws_db_subnet_group" "this" {
  name       = "${var.name}-db"
  subnet_ids = var.subnet_ids
  tags       = merge(var.tags, { Name = "${var.name}-db" })
}

resource "aws_security_group" "db" {
  name        = "${var.name}-db-sg"
  description = "Postgres access for ${var.name}"
  vpc_id      = var.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, { Name = "${var.name}-db-sg" })
}

resource "aws_security_group_rule" "db_ingress" {
  for_each                 = toset(var.allowed_security_group_ids)
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.db.id
  source_security_group_id = each.value
  description              = "Postgres from ${each.value}"
}

resource "aws_db_parameter_group" "this" {
  name        = "${var.name}-pg15"
  family      = "postgres15"
  description = "Hardened defaults for ${var.name}"

  parameter {
    name  = "log_min_duration_statement"
    value = "500"
  }
  parameter {
    name  = "log_connections"
    value = "1"
  }
  parameter {
    name  = "log_disconnections"
    value = "1"
  }
  parameter {
    name  = "log_lock_waits"
    value = "1"
  }
  parameter {
    name  = "log_statement"
    value = "ddl"
  }
  parameter {
    name         = "shared_preload_libraries"
    value        = "pg_stat_statements"
    apply_method = "pending-reboot"
  }
  parameter {
    name  = "rds.force_ssl"
    value = "1"
  }

  tags = var.tags
}

resource "aws_db_instance" "this" {
  identifier              = "${var.name}-pg"
  engine                  = "postgres"
  engine_version          = var.engine_version
  instance_class          = var.instance_class
  allocated_storage       = var.allocated_storage
  max_allocated_storage   = var.max_allocated_storage
  storage_type            = "gp3"
  storage_encrypted       = true

  db_name                 = var.db_name
  username                = var.username
  password                = var.password
  port                    = 5432
  parameter_group_name    = aws_db_parameter_group.this.name

  multi_az                = true
  publicly_accessible     = false
  db_subnet_group_name    = aws_db_subnet_group.this.name
  vpc_security_group_ids  = [aws_security_group.db.id]

  backup_retention_period = var.backup_retention_days
  backup_window           = "20:00-21:00"
  maintenance_window      = "Mon:21:30-Mon:22:30"
  copy_tags_to_snapshot   = true

  deletion_protection     = var.deletion_protection
  skip_final_snapshot     = false
  final_snapshot_identifier = "${var.name}-pg-final-${formatdate("YYYYMMDDhhmmss", timestamp())}"

  performance_insights_enabled         = true
  performance_insights_retention_period = 7
  monitoring_interval                  = 60
  enabled_cloudwatch_logs_exports      = ["postgresql", "upgrade"]
  auto_minor_version_upgrade           = true

  apply_immediately = false

  lifecycle {
    ignore_changes = [final_snapshot_identifier, password]
  }

  tags = merge(var.tags, { Name = "${var.name}-pg" })
}
