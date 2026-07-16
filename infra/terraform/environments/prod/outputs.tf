output "vpc_id" {
  value = module.vpc.vpc_id
}

output "private_subnet_ids" {
  value = module.vpc.private_subnet_ids
}

output "eks_cluster_name" {
  value = module.eks.cluster_name
}

output "eks_cluster_endpoint" {
  value = module.eks.cluster_endpoint
}

output "data_lake_bucket" {
  value = module.storage.s3_bucket_name
}

output "metadata_db_primary_endpoint" {
  value = module.metadata_db.primary_endpoint
}

output "metadata_db_read_replica_endpoints" {
  value = module.metadata_db.read_replica_endpoints
}

output "trino_endpoint" {
  value = module.trino_query_engine.endpoint
}

output "powerbi_gateway_instance_ids" {
  value = module.powerbi_gateway_cluster.instance_ids
}

output "data_transfer_role_arn" {
  value = module.data_transfer.transfer_role_arn
}

output "backup_primary_vault_arn" {
  value = module.backup_dr.primary_vault_arn
}

output "backup_dr_vault_arn" {
  value = aws_backup_vault.dr.arn
}

output "karpenter_nodepool_names" {
  value = module.karpenter.nodepool_names
}

output "prometheus_workspace_id" {
  value = module.observability.prometheus_workspace_id
}
