locals {
  base_tags = merge(var.tags, {
    Environment = var.environment
    ManagedBy   = "terraform"
    Module      = "storage"
  })
}

resource "aws_s3_bucket" "lake" {
  bucket        = var.s3_bucket_name
  force_destroy = var.force_destroy
  tags          = local.base_tags
}

resource "aws_s3_bucket_versioning" "lake" {
  bucket = aws_s3_bucket.lake.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "lake" {
  bucket = aws_s3_bucket.lake.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = var.kms_key_arn
    }
  }
}

resource "aws_s3_bucket_public_access_block" "lake" {
  bucket                  = aws_s3_bucket.lake.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_efs_file_system" "this" {
  count            = var.enable_efs_csi ? 1 : 0
  encrypted        = true
  kms_key_id       = var.kms_key_arn
  performance_mode = "generalPurpose"
  tags             = local.base_tags
}

resource "aws_security_group" "efs" {
  count       = var.enable_efs_csi ? 1 : 0
  name        = "${var.environment}-efs"
  description = "EFS mount target SG"
  vpc_id      = var.vpc_id
  tags        = local.base_tags
}
