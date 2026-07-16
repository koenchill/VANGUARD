output "endpoint" {
  description = "Internal NLB DNS name for Trino (BI DirectQuery / Grafana)."
  value       = aws_lb.trino.dns_name
}

output "security_group_id" {
  description = "Trino security group ID."
  value       = aws_security_group.trino.id
}

output "opa_sidecar_enabled" {
  description = "Whether OPA sidecar is enabled (G-004)."
  value       = var.opa_sidecar_enabled
}
