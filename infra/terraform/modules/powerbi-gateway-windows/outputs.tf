output "instance_ids" {
  description = "Windows gateway member instance IDs (empty when disabled)."
  value       = aws_instance.gateway[*].id
}

output "security_group_id" {
  description = "Gateway security group ID (null when disabled)."
  value       = try(aws_security_group.gateway[0].id, null)
}

output "ad_domain_join" {
  description = "Configured AD domain for Kerberos delegation."
  value       = var.ad_domain_join
}
