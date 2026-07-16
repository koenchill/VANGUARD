output "primary_endpoint" {
  description = "Primary writer endpoint."
  value       = aws_db_instance.primary.address
}

output "read_replica_endpoints" {
  description = "Read replica endpoints."
  value       = aws_db_instance.replica[*].address
}

output "security_group_id" {
  description = "DB security group ID."
  value       = aws_security_group.this.id
}

output "db_name" {
  description = "Database name."
  value       = aws_db_instance.primary.db_name
}
