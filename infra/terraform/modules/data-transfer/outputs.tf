output "transfer_role_arn" {
  description = "Read-constrained transfer role ARN."
  value       = aws_iam_role.transfer.arn
}

output "connection_type" {
  description = "Active connection type."
  value       = var.connection_type
}

output "landing_subdirectory" {
  description = "Landing prefix — always landing/raw."
  value       = "/landing/raw"
}

output "datasync_destination_arn" {
  description = "DataSync S3 location ARN when network transfer is used."
  value       = try(aws_datasync_location_s3.landing[0].arn, null)
}
