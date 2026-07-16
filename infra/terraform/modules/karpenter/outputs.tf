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
  description = "karpenter.sh/v1 NodePool names managed when create_nodepools is true."
  value       = keys(local.nodepools)
}
