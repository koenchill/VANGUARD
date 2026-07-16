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
  description = "Subnet IDs for Trino workers / NLB."
}

variable "worker_instance_type" {
  type        = string
  description = "EC2 instance type for Trino workers (r6i-class for pipeline-cpu pool alignment)."
}

variable "worker_count" {
  type        = number
  description = "Desired Trino worker count."
}

variable "coordinator_instance_type" {
  type        = string
  description = "EC2 instance type for the Trino coordinator."
}

variable "opa_sidecar_enabled" {
  type        = bool
  description = "Enable OPA sidecar for authorization (G-004)."
}

variable "data_lake_bucket" {
  type        = string
  description = "S3 data lake bucket name Trino catalogs against."
}

variable "ami_id" {
  type        = string
  description = "AMI ID for Trino hosts (or ASG launch template)."
}

variable "trino_port" {
  type        = number
  description = "Trino coordinator/worker listen port."
}

variable "trino_security_group_ids" {
  type        = list(string)
  description = "Additional security groups attached to Trino instances."
  default     = []
}

variable "tags" {
  type        = map(string)
  description = "Additional tags."
  default     = {}
}
