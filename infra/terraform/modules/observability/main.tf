locals {
  base_tags = merge(var.tags, {
    Environment = var.environment
    ManagedBy   = "terraform"
    Module      = "observability"
  })
}

resource "aws_prometheus_workspace" "this" {
  alias = var.prometheus_workspace_alias
  tags  = local.base_tags
}

resource "aws_grafana_workspace" "this" {
  count                    = var.create_managed_grafana ? 1 : 0
  name                     = var.grafana_workspace_name
  account_access_type      = "CURRENT_ACCOUNT"
  authentication_providers = ["AWS_SSO"]
  permission_type          = "SERVICE_MANAGED"
  tags                     = local.base_tags
}
