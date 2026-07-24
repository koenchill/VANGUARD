locals {
  base_tags = merge(var.tags, {
    Environment = var.environment
    ManagedBy   = "terraform"
    Module      = "powerbi-gateway-windows"
  })

  # G-003: fixed count, not Karpenter/ASG — vendor HA is installed gateway members.
  create_count = var.enabled ? var.gateway_node_count : 0
}

resource "aws_security_group" "gateway" {
  count       = var.enabled ? 1 : 0
  name        = "${var.environment}-powerbi-gateway"
  description = "PowerBI standard gateway Windows hosts"
  vpc_id      = var.vpc_id
  tags        = local.base_tags
}

resource "aws_instance" "gateway" {
  count = local.create_count

  ami                    = var.ami_id
  instance_type          = var.windows_instance_type
  subnet_id              = var.subnet_ids[count.index % length(var.subnet_ids)]
  vpc_security_group_ids = [aws_security_group.gateway[0].id]
  key_name               = var.key_name

  # AVD-AWS-0028 — require IMDSv2 tokens.
  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  # AVD-AWS-0131 — encrypt root volume.
  root_block_device {
    encrypted = true
  }

  # Stateful licensed install — not disposable compute (G-003).
  user_data = <<-EOT
    <powershell>
    $domain = "${var.ad_domain_join}"
    $trino  = "${var.trino_endpoint}"
    Write-Output "Joining domain $domain for Kerberos constrained delegation"
    Write-Output "Trino endpoint target: $trino"
    # Gateway install + cluster join performed by infra/ansible/powerbi-gateway (Phase 8)
    </powershell>
  EOT

  tags = merge(local.base_tags, {
    Name = "${var.environment}-powerbi-gateway-${count.index}"
    Role = "powerbi-gateway-member"
  })

  lifecycle {
    ignore_changes = [ami]
  }
}
