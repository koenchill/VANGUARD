locals {
  base_tags = merge(var.tags, {
    Environment = var.environment
    ManagedBy   = "terraform"
    Module      = "eks"
  })
}

data "aws_iam_policy_document" "cluster_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["eks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "cluster" {
  name               = "${var.cluster_name}-cluster"
  assume_role_policy = data.aws_iam_policy_document.cluster_assume.json
  tags               = local.base_tags
}

resource "aws_iam_role_policy_attachment" "cluster_policy" {
  role       = aws_iam_role.cluster.name
  policy_arn = var.cluster_policy_arn
}

resource "aws_security_group" "cluster" {
  name        = "${var.cluster_name}-cluster"
  description = "EKS cluster security group"
  vpc_id      = var.vpc_id
  tags        = local.base_tags
}

resource "aws_eks_cluster" "this" {
  name     = var.cluster_name
  role_arn = aws_iam_role.cluster.arn
  version  = var.cluster_version

  vpc_config {
    subnet_ids              = var.subnet_ids
    security_group_ids      = [aws_security_group.cluster.id]
    endpoint_private_access = var.endpoint_private_access
    # Portfolio freeze / AVD-AWS-0041: private API only (no public CIDR surface).
    endpoint_public_access  = false
  }

  # AVD-AWS-0039 — encrypt Kubernetes secrets at rest with customer-managed KMS.
  encryption_config {
    provider {
      key_arn = var.kms_key_arn
    }
    resources = ["secrets"]
  }

  enabled_cluster_log_types = var.enabled_cluster_log_types
  tags                      = local.base_tags

  lifecycle {
    precondition {
      condition     = var.endpoint_public_access == false
      error_message = "EKS public API endpoint must stay disabled (AVD-AWS-0041 / Zero Trust)."
    }
    precondition {
      condition     = !contains(var.public_access_cidrs, "0.0.0.0/0")
      error_message = "EKS public_access_cidrs must not include 0.0.0.0/0."
    }
  }

  depends_on = [aws_iam_role_policy_attachment.cluster_policy]
}
