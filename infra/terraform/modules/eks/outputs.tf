output "cluster_name" {
  description = "EKS cluster name."
  value       = aws_eks_cluster.this.name
}

output "cluster_endpoint" {
  description = "EKS API endpoint."
  value       = aws_eks_cluster.this.endpoint
}

output "cluster_security_group_id" {
  description = "Cluster security group ID."
  value       = aws_security_group.cluster.id
}

output "oidc_issuer_url" {
  description = "OIDC issuer URL for IRSA."
  value       = try(aws_eks_cluster.this.identity[0].oidc[0].issuer, null)
}
