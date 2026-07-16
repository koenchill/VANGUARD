locals {
  base_tags = merge(var.tags, {
    Environment = var.environment
    ManagedBy   = "terraform"
    Module      = "trino-query-engine"
    # G-005: Trino is the sole query engine — no engine_type switch.
    QueryEngine = "trino"
  })
}

resource "aws_security_group" "trino" {
  name        = "${var.environment}-trino"
  description = "Trino query engine"
  vpc_id      = var.vpc_id
  tags        = local.base_tags
}

resource "aws_lb" "trino" {
  name               = "${var.environment}-trino"
  internal           = true
  load_balancer_type = "network"
  subnets            = var.subnet_ids
  tags               = local.base_tags
}

resource "aws_lb_target_group" "trino" {
  name        = "${var.environment}-trino"
  port        = var.trino_port
  protocol    = "TCP"
  vpc_id      = var.vpc_id
  target_type = "instance"
  tags        = local.base_tags
}

resource "aws_lb_listener" "trino" {
  load_balancer_arn = aws_lb.trino.arn
  port              = var.trino_port
  protocol          = "TCP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.trino.arn
  }
}

resource "aws_launch_template" "worker" {
  name_prefix   = "${var.environment}-trino-worker-"
  image_id      = var.ami_id
  instance_type = var.worker_instance_type

  vpc_security_group_ids = concat([aws_security_group.trino.id], var.trino_security_group_ids)

  user_data = base64encode(<<-EOT
    #!/bin/bash
    echo "TRINO_ROLE=worker" >> /etc/trino/role.env
    echo "OPA_SIDECAR_ENABLED=${var.opa_sidecar_enabled}" >> /etc/trino/role.env
    echo "DATA_LAKE_BUCKET=${var.data_lake_bucket}" >> /etc/trino/role.env
  EOT
  )

  tag_specifications {
    resource_type = "instance"
    tags = merge(local.base_tags, {
      Name         = "${var.environment}-trino-worker"
      "karpenter.sh/nodepool" = "pipeline-cpu"
    })
  }
}

resource "aws_autoscaling_group" "workers" {
  name                = "${var.environment}-trino-workers"
  desired_capacity    = var.worker_count
  max_size            = var.worker_count
  min_size            = var.worker_count
  vpc_zone_identifier = var.subnet_ids
  target_group_arns   = [aws_lb_target_group.trino.arn]

  launch_template {
    id      = aws_launch_template.worker.id
    version = "$Latest"
  }

  tag {
    key                 = "Name"
    value               = "${var.environment}-trino-worker"
    propagate_at_launch = true
  }
}

resource "aws_instance" "coordinator" {
  ami                    = var.ami_id
  instance_type          = var.coordinator_instance_type
  subnet_id              = var.subnet_ids[0]
  vpc_security_group_ids = concat([aws_security_group.trino.id], var.trino_security_group_ids)

  user_data = <<-EOT
    #!/bin/bash
    echo "TRINO_ROLE=coordinator" >> /etc/trino/role.env
    echo "OPA_SIDECAR_ENABLED=${var.opa_sidecar_enabled}" >> /etc/trino/role.env
    echo "DATA_LAKE_BUCKET=${var.data_lake_bucket}" >> /etc/trino/role.env
  EOT

  tags = merge(local.base_tags, {
    Name = "${var.environment}-trino-coordinator"
  })
}
