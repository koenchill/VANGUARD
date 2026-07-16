locals {
  base_tags = merge(var.tags, {
    Environment = var.environment
    ManagedBy   = "terraform"
    Module      = "karpenter"
  })

  # Mutually exclusive families — enforced by construction (G-016).
  nodepools = {
    inference-gpu = {
      families       = var.inference_gpu_instance_families
      capacity_types = var.inference_gpu_capacity_types
      taint_value    = "inference-gpu"
    }
    pipeline-cpu = {
      families       = var.pipeline_cpu_instance_families
      capacity_types = var.pipeline_cpu_capacity_types
      taint_value    = "pipeline-cpu"
    }
    gateway-general = {
      families       = var.gateway_general_instance_families
      capacity_types = var.gateway_general_capacity_types
      taint_value    = "gateway-general"
    }
    sandbox-runtime = {
      families       = var.sandbox_runtime_instance_families
      capacity_types = var.sandbox_runtime_capacity_types
      taint_value    = "sandbox-runtime"
    }
  }
}

data "aws_iam_policy_document" "controller_assume" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [var.oidc_provider_arn]
    }
    condition {
      test     = "StringEquals"
      variable = "${replace(var.oidc_provider_arn, "/^arn:aws[a-zA-Z-]*:iam::[0-9]+:oidc-provider\\//", "")}:sub"
      values   = ["system:serviceaccount:${var.namespace}:${var.service_account_name}"]
    }
  }
}

resource "aws_iam_role" "controller" {
  name               = var.controller_role_name
  assume_role_policy = data.aws_iam_policy_document.controller_assume.json
  tags               = local.base_tags
}

data "aws_iam_policy_document" "node_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "node" {
  name               = var.node_role_name
  assume_role_policy = data.aws_iam_policy_document.node_assume.json
  tags               = local.base_tags
}

resource "aws_iam_role_policy_attachment" "node_worker" {
  role       = aws_iam_role.node.name
  policy_arn = var.node_worker_policy_arn
}

resource "aws_iam_role_policy_attachment" "node_cni" {
  role       = aws_iam_role.node.name
  policy_arn = var.node_cni_policy_arn
}

resource "aws_iam_role_policy_attachment" "node_ecr" {
  role       = aws_iam_role.node.name
  policy_arn = var.node_ecr_policy_arn
}

resource "aws_iam_instance_profile" "node" {
  name = var.node_role_name
  role = aws_iam_role.node.name
  tags = local.base_tags
}

resource "aws_sqs_queue" "interruption" {
  name                      = var.interruption_queue_name
  message_retention_seconds = 300
  tags                      = local.base_tags
}

# karpenter.sh/v1 NodePool objects are emitted as structured output for Phase 5
# GitOps manifests (infra/k8s/karpenter). Terraform owns IAM/SQS only here so the
# root module does not require a live Kubernetes API during plan/apply.
