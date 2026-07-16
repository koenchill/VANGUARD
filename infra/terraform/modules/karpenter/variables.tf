variable "environment" {
  type        = string
  description = "Environment name."
}

variable "cluster_name" {
  type        = string
  description = "EKS cluster name Karpenter joins."
}

variable "cluster_endpoint" {
  type        = string
  description = "EKS API endpoint."
}

variable "oidc_provider_arn" {
  type        = string
  description = "IAM OIDC provider ARN for the cluster (IRSA)."
}

variable "namespace" {
  type        = string
  description = "Kubernetes namespace for Karpenter controller."
}

variable "service_account_name" {
  type        = string
  description = "Karpenter controller service account name."
}

variable "inference_gpu_instance_families" {
  type        = list(string)
  description = "Instance families for inference-gpu NodePool (G-016)."
}

variable "pipeline_cpu_instance_families" {
  type        = list(string)
  description = "Instance families for pipeline-cpu NodePool (G-016)."
}

variable "gateway_general_instance_families" {
  type        = list(string)
  description = "Instance families for gateway-general NodePool (G-016)."
}

variable "sandbox_runtime_instance_families" {
  type        = list(string)
  description = "Instance families for sandbox-runtime NodePool (G-016)."
}

variable "inference_gpu_capacity_types" {
  type        = list(string)
  description = "Capacity types for inference-gpu (e.g. on-demand)."
}

variable "pipeline_cpu_capacity_types" {
  type        = list(string)
  description = "Capacity types for pipeline-cpu (spot-heavy)."
}

variable "gateway_general_capacity_types" {
  type        = list(string)
  description = "Capacity types for gateway-general."
}

variable "sandbox_runtime_capacity_types" {
  type        = list(string)
  description = "Capacity types for sandbox-runtime."
}

variable "node_role_name" {
  type        = string
  description = "IAM role name assumed by Karpenter-provisioned nodes."
}

variable "controller_role_name" {
  type        = string
  description = "IAM role name for the Karpenter controller (IRSA)."
}

variable "interruption_queue_name" {
  type        = string
  description = "SQS queue name for Spot interruption events."
}

variable "node_worker_policy_arn" {
  type        = string
  description = "IAM policy ARN for EKS worker nodes."
}

variable "node_cni_policy_arn" {
  type        = string
  description = "IAM policy ARN for the VPC CNI."
}

variable "node_ecr_policy_arn" {
  type        = string
  description = "IAM policy ARN for ECR read-only access."
}

variable "node_architecture" {
  type        = string
  description = "Node architecture requirement (e.g. amd64)."
}

variable "consolidate_after" {
  type        = string
  description = "Karpenter consolidation delay (e.g. 30m)."
}

variable "create_nodepools" {
  type        = bool
  description = "When true, apply karpenter.sh/v1 NodePool manifests via the Kubernetes provider."
}

variable "tags" {
  type        = map(string)
  description = "Additional tags."
  default     = {}
}
