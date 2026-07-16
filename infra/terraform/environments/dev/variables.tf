variable "environment" {
  type        = string
  description = "Environment name."
}

variable "aws_region" {
  type        = string
  description = "Primary AWS region."
}

variable "aws_partition" {
  type        = string
  description = "AWS partition (aws or aws-us-gov)."
}

variable "vpc_cidr" {
  type        = string
  description = "VPC CIDR block."
}

variable "private_subnets" {
  type        = list(string)
  description = "Private subnet CIDRs."
}

variable "availability_zones" {
  type        = list(string)
  description = "AZs aligned to private_subnets."
}

variable "enable_dns_hostnames" {
  type = bool
}

variable "enable_dns_support" {
  type = bool
}

variable "eks_cluster_name" {
  type = string
}

variable "eks_cluster_version" {
  type = string
}

variable "eks_endpoint_private_access" {
  type = bool
}

variable "eks_endpoint_public_access" {
  type = bool
}

variable "eks_enabled_cluster_log_types" {
  type = list(string)
}

variable "eks_cluster_policy_arn" {
  type = string
}

variable "eks_oidc_thumbprint" {
  type        = string
  description = "SHA-1 thumbprint for the EKS OIDC issuer certificate."
}

variable "karpenter_namespace" {
  type = string
}

variable "karpenter_service_account_name" {
  type = string
}

variable "inference_gpu_instance_families" {
  type = list(string)
}

variable "pipeline_cpu_instance_families" {
  type = list(string)
}

variable "gateway_general_instance_families" {
  type = list(string)
}

variable "sandbox_runtime_instance_families" {
  type = list(string)
}

variable "inference_gpu_capacity_types" {
  type = list(string)
}

variable "pipeline_cpu_capacity_types" {
  type = list(string)
}

variable "gateway_general_capacity_types" {
  type = list(string)
}

variable "sandbox_runtime_capacity_types" {
  type = list(string)
}

variable "karpenter_node_role_name" {
  type = string
}

variable "karpenter_controller_role_name" {
  type = string
}

variable "karpenter_interruption_queue_name" {
  type = string
}

variable "karpenter_node_worker_policy_arn" {
  type = string
}

variable "karpenter_node_cni_policy_arn" {
  type = string
}

variable "karpenter_node_ecr_policy_arn" {
  type = string
}

variable "karpenter_node_architecture" {
  type = string
}

variable "karpenter_consolidate_after" {
  type = string
}

variable "data_lake_bucket" {
  type = string
}

variable "enable_efs_csi" {
  type = bool
}

variable "kms_key_arn" {
  type = string
}

variable "storage_force_destroy" {
  type = bool
}

variable "metadata_db_instance_class" {
  type = string
}

variable "metadata_db_multi_az" {
  type = bool
}

variable "metadata_db_read_replicas" {
  type = number
}

variable "metadata_db_engine_version" {
  type = string
}

variable "metadata_db_name" {
  type = string
}

variable "metadata_db_master_username" {
  type = string
}

variable "metadata_db_master_password" {
  type      = string
  sensitive = true
}

variable "metadata_db_allocated_storage" {
  type = number
}

variable "metadata_db_backup_retention_period" {
  type = number
}

variable "trino_worker_instance_type" {
  type = string
}

variable "trino_worker_count" {
  type = number
}

variable "trino_coordinator_instance_type" {
  type = string
}

variable "trino_opa_sidecar_enabled" {
  type = bool
}

variable "trino_ami_id" {
  type = string
}

variable "trino_port" {
  type = number
}

variable "bi_deployment_mode" {
  type = string
  validation {
    condition     = contains(["hybrid", "air_gapped"], var.bi_deployment_mode)
    error_message = "bi_deployment_mode must be hybrid or air_gapped."
  }
}

variable "powerbi_gateway_instance_type" {
  type = string
}

variable "powerbi_gateway_ad_domain" {
  type = string
}

variable "powerbi_gateway_node_count" {
  type = number
}

variable "powerbi_gateway_ami_id" {
  type = string
}

variable "powerbi_gateway_key_name" {
  type = string
}

variable "enterprise_source_connectivity" {
  type = object({
    connection_type   = string
    source_endpoint   = string
    source_account_id = string
  })
}

variable "transfer_role_name" {
  type = string
}

variable "datasync_task_name" {
  type = string
}

variable "vpn_customer_gateway_ip" {
  type    = string
  default = null
}

variable "vpn_bgp_asn" {
  type    = number
  default = null
}

variable "dx_bandwidth" {
  type    = string
  default = null
}

variable "dx_amazon_side_asn" {
  type    = number
  default = null
}

variable "backup_retention_daily_days" {
  type = number
}

variable "backup_retention_weekly_weeks" {
  type = number
}

variable "dr_secondary_region" {
  type = string
}

variable "backup_primary_vault_name" {
  type = string
}

variable "backup_dr_vault_name" {
  type = string
}

variable "velero_role_name" {
  type = string
}

variable "velero_bucket_arn" {
  type = string
}

variable "backup_daily_schedule" {
  type = string
}

variable "backup_weekly_schedule" {
  type = string
}

variable "prometheus_workspace_alias" {
  type = string
}

variable "grafana_workspace_name" {
  type = string
}

variable "create_managed_grafana" {
  type = bool
}

variable "tags" {
  type    = map(string)
  default = {}
}
