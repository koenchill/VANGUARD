variable "environment" {
  type        = string
  description = "Environment name."
}

variable "prometheus_workspace_alias" {
  type        = string
  description = "Amazon Managed Prometheus workspace alias."
}

variable "grafana_workspace_name" {
  type        = string
  description = "Amazon Managed Grafana workspace name (hybrid path optional)."
}

variable "create_managed_grafana" {
  type        = bool
  description = "Create AMG workspace; air-gapped path uses in-cluster Grafana instead."
}

variable "tags" {
  type        = map(string)
  description = "Additional tags."
  default     = {}
}
