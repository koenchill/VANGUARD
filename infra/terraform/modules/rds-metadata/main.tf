locals {
  base_tags = merge(var.tags, {
    Environment = var.environment
    ManagedBy   = "terraform"
    Module      = "rds-metadata"
  })
}

resource "aws_db_subnet_group" "this" {
  name       = "${var.environment}-metadata"
  subnet_ids = var.subnet_ids
  tags       = local.base_tags
}

resource "aws_security_group" "this" {
  name        = "${var.environment}-metadata-db"
  description = "Curation metadata Postgres"
  vpc_id      = var.vpc_id
  tags        = local.base_tags
}

resource "aws_db_instance" "primary" {
  identifier                 = "${var.environment}-curation-metadata"
  engine                     = "postgres"
  engine_version             = var.engine_version
  instance_class             = var.instance_class
  allocated_storage          = var.allocated_storage
  db_name                    = var.db_name
  username                   = var.master_username
  password                   = var.master_password
  db_subnet_group_name       = aws_db_subnet_group.this.name
  vpc_security_group_ids     = [aws_security_group.this.id]
  multi_az                   = var.multi_az
  storage_encrypted          = true
  kms_key_id                 = var.kms_key_arn
  backup_retention_period    = var.backup_retention_period
  skip_final_snapshot        = false
  final_snapshot_identifier  = "${var.environment}-curation-metadata-final"
  deletion_protection        = true
  auto_minor_version_upgrade = true
  tags                       = local.base_tags
}

resource "aws_db_instance" "replica" {
  count = var.read_replica_count

  identifier             = "${var.environment}-curation-metadata-rr-${count.index}"
  replicate_source_db    = aws_db_instance.primary.identifier
  instance_class         = var.instance_class
  publicly_accessible    = false
  skip_final_snapshot    = true
  vpc_security_group_ids = [aws_security_group.this.id]
  storage_encrypted      = true
  kms_key_id             = var.kms_key_arn
  tags                   = local.base_tags
}
