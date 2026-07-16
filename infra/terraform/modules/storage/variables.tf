variable "environment" {
  type        = string
  description = "Environment name."
}

variable "s3_bucket_name" {
  type        = string
  description = "Data lake bucket name."
}

variable "enable_efs_csi" {
  type        = bool
  description = "Whether to create an EFS filesystem for CSI usage."
}

variable "vpc_id" {
  type        = string
  description = "VPC ID for EFS mount targets (required when enable_efs_csi)."
}

variable "subnet_ids" {
  type        = list(string)
  description = "Subnet IDs for EFS mount targets."
}

variable "kms_key_arn" {
  type        = string
  description = "KMS key ARN for bucket encryption."
}

variable "force_destroy" {
  type        = bool
  description = "Allow Terraform to destroy the bucket with objects."
}

variable "tags" {
  type        = map(string)
  description = "Additional tags."
  default     = {}
}
