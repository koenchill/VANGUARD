output "s3_bucket_name" {
  description = "Data lake bucket name."
  value       = aws_s3_bucket.lake.bucket
}

output "s3_bucket_arn" {
  description = "Data lake bucket ARN."
  value       = aws_s3_bucket.lake.arn
}

output "efs_id" {
  description = "EFS filesystem ID when enable_efs_csi is true."
  value       = try(aws_efs_file_system.this[0].id, null)
}
