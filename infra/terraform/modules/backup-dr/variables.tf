variable "environment" {
  type        = string
  description = "Environment name."
}

variable "backup_retention_daily_days" {
  type        = number
  description = "Daily backup retention in days."
}

variable "backup_retention_weekly_weeks" {
  type        = number
  description = "Weekly backup retention in weeks."
}

variable "dr_secondary_region" {
  type        = string
  description = "Secondary region for cross-region vault copy."
}

variable "primary_vault_name" {
  type        = string
  description = "Primary AWS Backup vault name."
}

variable "dr_vault_arn" {
  type        = string
  description = "Destination vault ARN in the DR region (wired by root module)."
}

variable "velero_role_name" {
  type        = string
  description = "IAM role name for Velero."
}

variable "velero_bucket_arn" {
  type        = string
  description = "S3 bucket ARN for Velero backups."
}

variable "kms_key_arn" {
  type        = string
  description = "KMS key ARN for backup vault encryption."
}

variable "daily_schedule" {
  type        = string
  description = "Cron expression for daily backups."
}

variable "weekly_schedule" {
  type        = string
  description = "Cron expression for weekly backups."
}

variable "tags" {
  type        = map(string)
  description = "Additional tags."
  default     = {}
}
