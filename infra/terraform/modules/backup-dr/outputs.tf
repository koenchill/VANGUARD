output "primary_vault_arn" {
  description = "Primary backup vault ARN."
  value       = aws_backup_vault.primary.arn
}

output "daily_plan_id" {
  description = "Daily backup plan ID."
  value       = aws_backup_plan.daily.id
}

output "weekly_plan_id" {
  description = "Weekly backup plan ID."
  value       = aws_backup_plan.weekly.id
}

output "velero_role_arn" {
  description = "Velero IAM role ARN."
  value       = aws_iam_role.velero.arn
}

output "dr_secondary_region" {
  description = "Configured DR secondary region."
  value       = var.dr_secondary_region
}
