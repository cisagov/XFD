output "bucket_name" {
  description = "Name of the CISADEV Terraform state bucket. Use this as `bucket` in devhost.config and cisadev.config."
  value       = aws_s3_bucket.tfstate.id
}

output "bucket_arn" {
  description = "ARN of the CISADEV Terraform state bucket"
  value       = aws_s3_bucket.tfstate.arn
}

output "bucket_region" {
  description = "Region of the CISADEV Terraform state bucket"
  value       = var.aws_region
}
