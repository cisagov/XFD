variable "aws_region" {
  description = "AWS region for the state bucket"
  type        = string
  default     = "us-east-1"
}

variable "state_bucket_name" {
  description = <<-EOT
    Globally-unique S3 bucket name to hold CISADEV Terraform state.
    Must match the `bucket` value in ../devhost/devhost.config and
    ../runner/cisadev.config. If this name is already taken (S3 bucket names
    are global, across all AWS accounts), change it here AND in both of
    those files.
  EOT
  type        = string
  default     = "cisadev-xfd-terraform-state"
}

variable "tags" {
  description = "Tags applied to the state bucket"
  type        = map(string)
  default = {
    Name        = "CISADEV Terraform State"
    Environment = "cisadev"
    Owner       = "XFD Dashboard"
  }
}
