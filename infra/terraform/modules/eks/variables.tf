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
