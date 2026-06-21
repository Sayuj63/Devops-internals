output "endpoint" {
  value     = aws_db_instance.this.address
  sensitive = true
}

output "port" {
  value = aws_db_instance.this.port
}

output "db_name" {
  value = aws_db_instance.this.db_name
}

output "security_group_id" {
  value = aws_security_group.db.id
}

output "arn" {
  value = aws_db_instance.this.arn
}
