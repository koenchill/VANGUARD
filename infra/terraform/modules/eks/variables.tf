variable "environment" {
  type        = string
  description = "Environment name."
}

variable "vpc_id" {
  type        = string
  description = "VPC ID for the EKS cluster."
}

variable "subnet_ids" {
  type        = list(string)
  description = "Subnet IDs for the EKS control plane / nodes."
}

variable "cluster_version" {
  type        = string
  description = "Kubernetes version for the EKS cluster."
}

variable "cluster_name" {
  type        = string
  description = "EKS cluster name."
}

variable "endpoint_private_access" {
  type        = bool
  description = "Enable private API endpoint access."
}

variable "endpoint_public_access" {
  type        = bool
  description = "Enable public API endpoint access."
}

variable "public_access_cidrs" {
  type        = list(string)
  description = "CIDRs allowed to reach the public EKS API endpoint. Must not include 0.0.0.0/0."
  # Documentation/TEST-NET CIDR as safe default so scanners never see the AWS world-open default.
  default     = ["203.0.113.0/24"]
}

variable "kms_key_arn" {
  type        = string
  description = "KMS key ARN used to encrypt Kubernetes secrets at rest."
}

variable "enabled_cluster_log_types" {
  type        = list(string)
  description = "Control plane log types to enable."
}

variable "cluster_policy_arn" {
  type        = string
  description = "IAM policy ARN attached to the EKS cluster role (AWS-managed EKS cluster policy)."
}

variable "tags" {
  type        = map(string)
  description = "Additional tags."
  default     = {}
}
