locals {
  base_tags = merge(var.tags, {
    Environment = var.environment
    ManagedBy   = "terraform"
    Module      = "data-transfer"
  })

  is_dx            = var.connection_type == "direct_connect"
  is_vpn           = var.connection_type == "vpn"
  is_cross_account = var.connection_type == "cross_account"
  is_snowball      = var.connection_type == "snowball"
  use_datasync     = contains(["direct_connect", "vpn", "cross_account"], var.connection_type)
}

data "aws_iam_policy_document" "transfer_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["datasync.amazonaws.com"]
    }
  }

  dynamic "statement" {
    for_each = local.is_cross_account ? [1] : []
    content {
      actions = ["sts:AssumeRole"]
      principals {
        type        = "AWS"
        identifiers = ["arn:aws:iam::${var.source_account_id}:root"]
      }
    }
  }
}

resource "aws_iam_role" "transfer" {
  name               = var.transfer_role_name
  assume_role_policy = data.aws_iam_policy_document.transfer_assume.json
  tags               = local.base_tags
}

data "aws_iam_policy_document" "transfer_readonly" {
  statement {
    sid     = "LandingWriteOnlyToRawPrefix"
    actions = ["s3:PutObject", "s3:AbortMultipartUpload", "s3:ListBucket"]
    resources = [
      "arn:aws:s3:::${var.landing_bucket}",
      "arn:aws:s3:::${var.landing_bucket}/landing/raw/*"
    ]
  }

  statement {
    sid       = "DenyCuratedZones"
    effect    = "Deny"
    actions   = ["s3:PutObject", "s3:DeleteObject"]
    resources = [
      "arn:aws:s3:::${var.landing_bucket}/bronze/*",
      "arn:aws:s3:::${var.landing_bucket}/silver/*",
      "arn:aws:s3:::${var.landing_bucket}/gold/*"
    ]
  }
}

resource "aws_iam_role_policy" "transfer_readonly" {
  name   = "${var.transfer_role_name}-landing"
  role   = aws_iam_role.transfer.id
  policy = data.aws_iam_policy_document.transfer_readonly.json
}

resource "aws_datasync_location_s3" "landing" {
  count = local.use_datasync ? 1 : 0

  s3_bucket_arn = "arn:aws:s3:::${var.landing_bucket}"
  subdirectory  = "/landing/raw"
  s3_config {
    bucket_access_role_arn = aws_iam_role.transfer.arn
  }
  tags = local.base_tags
}

resource "aws_vpn_gateway" "this" {
  count  = local.is_vpn ? 1 : 0
  vpc_id = var.vpc_id
  tags   = local.base_tags
}

resource "aws_customer_gateway" "this" {
  count      = local.is_vpn ? 1 : 0
  bgp_asn    = var.vpn_bgp_asn
  ip_address = var.vpn_customer_gateway_ip
  type       = "ipsec.1"
  tags       = local.base_tags
}

resource "aws_dx_gateway" "this" {
  count           = local.is_dx ? 1 : 0
  name            = "${var.environment}-dx-gateway"
  amazon_side_asn = var.dx_amazon_side_asn
}

# Snowball jobs are operator-initiated; module records intent + landing target only.
resource "aws_ssm_parameter" "snowball_landing" {
  count = local.is_snowball ? 1 : 0
  name  = "/${var.environment}/data-transfer/snowball-landing"
  type  = "String"
  value = "s3://${var.landing_bucket}/landing/raw/"
  tags  = local.base_tags
}
