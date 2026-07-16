variable "environment" {
  type        = string
  description = "Environment name."
}

variable "enabled" {
  type        = bool
  description = "When false (air-gapped/IL), create no gateway resources."
}

variable "vpc_id" {
  type        = string
  description = "VPC ID."
}

variable "subnet_ids" {
  type        = list(string)
  description = "Private subnet IDs for gateway members."
}

variable "gateway_node_count" {
  type        = number
  description = "Fixed gateway member count (vendor HA minimum is 2)."
}

variable "windows_instance_type" {
  type        = string
  description = "EC2 instance type for Windows Server gateway members."
}

variable "ad_domain_join" {
  type        = string
  description = "AD domain for Kerberos constrained delegation (G-004)."
}

variable "trino_endpoint" {
  type        = string
  description = "Private Trino endpoint the gateway will DirectQuery."
}

variable "ami_id" {
  type        = string
  description = "Windows Server 2022 AMI ID."
}

variable "key_name" {
  type        = string
  description = "EC2 key pair name for Windows instances."
}

variable "tags" {
  type        = map(string)
  description = "Additional tags."
  default     = {}
}
