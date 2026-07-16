locals {
  base_tags = merge(var.tags, {
    Environment = var.environment
    ManagedBy   = "terraform"
    Module      = "backup-dr"
  })
}

resource "aws_backup_vault" "primary" {
  name        = var.primary_vault_name
  kms_key_arn = var.kms_key_arn
  tags        = local.base_tags
}

resource "aws_backup_plan" "daily" {
  name = "${var.environment}-daily"
  rule {
    rule_name         = "daily-incremental"
    target_vault_name = aws_backup_vault.primary.name
    schedule          = var.daily_schedule
    lifecycle {
      delete_after = var.backup_retention_daily_days
    }
    copy_action {
      destination_vault_arn = var.dr_vault_arn
    }
  }
  tags = local.base_tags
}

resource "aws_backup_plan" "weekly" {
  name = "${var.environment}-weekly"
  rule {
    rule_name         = "weekly-full"
    target_vault_name = aws_backup_vault.primary.name
    schedule          = var.weekly_schedule
    lifecycle {
      delete_after = var.backup_retention_weekly_weeks * 7
    }
    copy_action {
      destination_vault_arn = var.dr_vault_arn
    }
  }
  tags = local.base_tags
}

data "aws_iam_policy_document" "velero_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "velero" {
  name               = var.velero_role_name
  assume_role_policy = data.aws_iam_policy_document.velero_assume.json
  tags               = local.base_tags
}

data "aws_iam_policy_document" "velero" {
  statement {
    actions   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"]
    resources = [var.velero_bucket_arn, "${var.velero_bucket_arn}/*"]
  }
}

resource "aws_iam_role_policy" "velero" {
  name   = "${var.velero_role_name}-s3"
  role   = aws_iam_role.velero.id
  policy = data.aws_iam_policy_document.velero.json
}
