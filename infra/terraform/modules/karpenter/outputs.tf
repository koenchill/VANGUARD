output "controller_role_arn" {
  description = "IAM role ARN for Karpenter controller."
  value       = aws_iam_role.controller.arn
}

output "node_instance_profile_name" {
  description = "Instance profile for Karpenter nodes."
  value       = aws_iam_instance_profile.node.name
}

output "interruption_queue_name" {
  description = "SQS interruption queue name."
  value       = aws_sqs_queue.interruption.name
}

output "nodepool_names" {
  description = "karpenter.sh/v1 NodePool names (mutually exclusive workload pools)."
  value       = keys(local.nodepools)
}

output "nodepool_specs" {
  description = "Structured NodePool specs for Phase 5 GitOps rendering (karpenter.sh/v1)."
  value = {
    for name, cfg in local.nodepools : name => {
      apiVersion = "karpenter.sh/v1"
      kind       = "NodePool"
      metadata = {
        name = name
      }
      spec = {
        template = {
          metadata = {
            labels = {
              "workload-tier" = cfg.taint_value
            }
          }
          spec = {
            requirements = [
              {
                key      = "karpenter.sh/capacity-type"
                operator = "In"
                values   = cfg.capacity_types
              },
              {
                key      = "karpenter.k8s.aws/instance-family"
                operator = "In"
                values   = cfg.families
              },
              {
                key      = "kubernetes.io/arch"
                operator = "In"
                values   = [var.node_architecture]
              }
            ]
            taints = [
              {
                key    = "workload-tier"
                value  = cfg.taint_value
                effect = "NoSchedule"
              }
            ]
            nodeClassRef = {
              group = "karpenter.k8s.aws"
              kind  = "EC2NodeClass"
              name  = name
            }
          }
        }
        disruption = {
          consolidationPolicy = "WhenEmptyOrUnderutilized"
          consolidateAfter    = var.consolidate_after
        }
      }
    }
  }
}
