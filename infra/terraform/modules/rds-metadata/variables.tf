variable "environment" {
  type        = string
  description = "Environment name."
}

variable "vpc_id" {
  type        = string
  description = "VPC ID."
}

variable "subnet_ids" {
  type        = list(string)
  description = "Private subnet IDs for the DB subnet group."
}

variable "instance_class" {
  type        = string
  description = "RDS instance class."
}

variable "multi_az" {
  type        = bool
  description = "Enable Multi-AZ deployment."
}

variable "read_replica_count" {
  type        = number
  description = "Number of read replicas."
}

variable "engine_version" {
  type        = string
  description = "PostgreSQL engine version."
}

variable "db_name" {
  type        = string
  description = "Initial database name (curation metadata)."
}

variable "master_username" {
  type        = string
  description = "Master username."
}

variable "master_password" {
  type        = string
  description = "Master password (prefer Secrets Manager in real deployments)."
  sensitive   = true
}

variable "allocated_storage" {
  type        = number
  description = "Allocated storage in GiB."
}

variable "backup_retention_period" {
  type        = number
  description = "Automated backup retention days."
}

variable "kms_key_arn" {
  type        = string
  description = "KMS key ARN for storage encryption."
}

variable "tags" {
  type        = map(string)
  description = "Additional tags."
  default     = {}
}
