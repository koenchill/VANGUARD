locals {
  aws_partition = var.aws_partition
  common_tags = merge(var.tags, {
    Environment = var.environment
    Project     = "vanguard"
    Partition   = local.aws_partition
  })
}

resource "aws_iam_openid_connect_provider" "eks" {
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [var.eks_oidc_thumbprint]
  url             = module.eks.oidc_issuer_url
  tags            = local.common_tags
}

resource "aws_backup_vault" "dr" {
  provider    = aws.dr
  name        = var.backup_dr_vault_name
  kms_key_arn = var.kms_key_arn
  tags        = local.common_tags
}

module "vpc" {
  source = "../../modules/vpc"

  environment          = var.environment
  cidr_block           = var.vpc_cidr
  private_subnets      = var.private_subnets
  availability_zones   = var.availability_zones
  enable_dns_hostnames = var.enable_dns_hostnames
  enable_dns_support   = var.enable_dns_support
  tags                 = local.common_tags
}

module "eks" {
  source = "../../modules/eks"

  environment                 = var.environment
  vpc_id                      = module.vpc.vpc_id
  subnet_ids                  = module.vpc.private_subnet_ids
  cluster_version             = var.eks_cluster_version
  cluster_name                = var.eks_cluster_name
  endpoint_private_access     = var.eks_endpoint_private_access
  endpoint_public_access      = var.eks_endpoint_public_access
  public_access_cidrs         = var.eks_public_access_cidrs
  kms_key_arn                 = var.kms_key_arn
  enabled_cluster_log_types   = var.eks_enabled_cluster_log_types
  cluster_policy_arn          = var.eks_cluster_policy_arn
  tags                        = local.common_tags
}

module "karpenter" {
  source = "../../modules/karpenter"

  environment                       = var.environment
  cluster_name                      = module.eks.cluster_name
  cluster_endpoint                  = module.eks.cluster_endpoint
  oidc_provider_arn                 = aws_iam_openid_connect_provider.eks.arn
  namespace                         = var.karpenter_namespace
  service_account_name              = var.karpenter_service_account_name
  inference_gpu_instance_families   = var.inference_gpu_instance_families
  pipeline_cpu_instance_families    = var.pipeline_cpu_instance_families
  gateway_general_instance_families = var.gateway_general_instance_families
  sandbox_runtime_instance_families = var.sandbox_runtime_instance_families
  inference_gpu_capacity_types      = var.inference_gpu_capacity_types
  pipeline_cpu_capacity_types       = var.pipeline_cpu_capacity_types
  gateway_general_capacity_types    = var.gateway_general_capacity_types
  sandbox_runtime_capacity_types    = var.sandbox_runtime_capacity_types
  node_role_name                    = var.karpenter_node_role_name
  controller_role_name              = var.karpenter_controller_role_name
  interruption_queue_name           = var.karpenter_interruption_queue_name
  node_worker_policy_arn            = var.karpenter_node_worker_policy_arn
  node_cni_policy_arn               = var.karpenter_node_cni_policy_arn
  node_ecr_policy_arn               = var.karpenter_node_ecr_policy_arn
  node_architecture                 = var.karpenter_node_architecture
  consolidate_after                 = var.karpenter_consolidate_after
  tags                              = local.common_tags
}

module "storage" {
  source = "../../modules/storage"

  environment     = var.environment
  enable_efs_csi  = var.enable_efs_csi
  s3_bucket_name  = var.data_lake_bucket
  vpc_id          = module.vpc.vpc_id
  subnet_ids      = module.vpc.private_subnet_ids
  kms_key_arn     = var.kms_key_arn
  force_destroy   = var.storage_force_destroy
  tags            = local.common_tags
}

module "metadata_db" {
  source = "../../modules/rds-metadata"

  environment             = var.environment
  vpc_id                  = module.vpc.vpc_id
  subnet_ids              = module.vpc.private_subnet_ids
  instance_class          = var.metadata_db_instance_class
  multi_az                = var.metadata_db_multi_az
  read_replica_count      = var.metadata_db_read_replicas
  engine_version          = var.metadata_db_engine_version
  db_name                 = var.metadata_db_name
  master_username         = var.metadata_db_master_username
  master_password         = var.metadata_db_master_password
  allocated_storage       = var.metadata_db_allocated_storage
  backup_retention_period = var.metadata_db_backup_retention_period
  kms_key_arn             = var.kms_key_arn
  tags                    = local.common_tags
}

# G-005: Trino-only — no engine_type switch.
module "trino_query_engine" {
  source = "../../modules/trino-query-engine"

  environment               = var.environment
  vpc_id                    = module.vpc.vpc_id
  subnet_ids                = module.vpc.private_subnet_ids
  worker_instance_type      = var.trino_worker_instance_type
  worker_count              = var.trino_worker_count
  coordinator_instance_type = var.trino_coordinator_instance_type
  opa_sidecar_enabled       = var.trino_opa_sidecar_enabled
  data_lake_bucket          = module.storage.s3_bucket_name
  ami_id                    = var.trino_ami_id
  trino_port                = var.trino_port
  tags                      = local.common_tags
}

# G-003/G-004: Windows Server gateway cluster; no-op when air_gapped.
module "powerbi_gateway_cluster" {
  source = "../../modules/powerbi-gateway-windows"

  environment           = var.environment
  enabled               = var.bi_deployment_mode == "hybrid"
  vpc_id                = module.vpc.vpc_id
  subnet_ids            = module.vpc.private_subnet_ids
  gateway_node_count    = var.powerbi_gateway_node_count
  windows_instance_type = var.powerbi_gateway_instance_type
  ad_domain_join        = var.powerbi_gateway_ad_domain
  trino_endpoint        = module.trino_query_engine.endpoint
  ami_id                = var.powerbi_gateway_ami_id
  key_name              = var.powerbi_gateway_key_name
  tags                  = local.common_tags
}

# G-009: data_transfer must be instantiated (closes orphan).
module "data_transfer" {
  source = "../../modules/data-transfer"

  environment             = var.environment
  vpc_id                  = module.vpc.vpc_id
  subnet_ids              = module.vpc.private_subnet_ids
  connection_type         = var.enterprise_source_connectivity.connection_type
  source_endpoint         = var.enterprise_source_connectivity.source_endpoint
  source_account_id       = var.enterprise_source_connectivity.source_account_id
  landing_bucket          = module.storage.s3_bucket_name
  transfer_role_name      = var.transfer_role_name
  datasync_task_name      = var.datasync_task_name
  vpn_customer_gateway_ip = var.vpn_customer_gateway_ip
  vpn_bgp_asn             = var.vpn_bgp_asn
  dx_bandwidth            = var.dx_bandwidth
  dx_amazon_side_asn      = var.dx_amazon_side_asn
  tags                    = local.common_tags
}

module "backup_dr" {
  source = "../../modules/backup-dr"

  environment                   = var.environment
  backup_retention_daily_days   = var.backup_retention_daily_days
  backup_retention_weekly_weeks = var.backup_retention_weekly_weeks
  dr_secondary_region           = var.dr_secondary_region
  primary_vault_name            = var.backup_primary_vault_name
  dr_vault_arn                  = aws_backup_vault.dr.arn
  velero_role_name              = var.velero_role_name
  velero_bucket_arn             = var.velero_bucket_arn
  kms_key_arn                   = var.kms_key_arn
  daily_schedule                = var.backup_daily_schedule
  weekly_schedule               = var.backup_weekly_schedule
  tags                          = local.common_tags
}

module "observability" {
  source = "../../modules/observability"

  environment                = var.environment
  prometheus_workspace_alias = var.prometheus_workspace_alias
  grafana_workspace_name     = var.grafana_workspace_name
  create_managed_grafana     = var.create_managed_grafana
  tags                       = local.common_tags
}
