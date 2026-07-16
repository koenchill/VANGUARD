output "prometheus_workspace_id" {
  description = "AMP workspace ID."
  value       = aws_prometheus_workspace.this.id
}

output "prometheus_endpoint" {
  description = "AMP query endpoint."
  value       = aws_prometheus_workspace.this.prometheus_endpoint
}

output "grafana_workspace_id" {
  description = "AMG workspace ID when created."
  value       = try(aws_grafana_workspace.this[0].id, null)
}
