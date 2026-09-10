# vars.tf
# Variables for the CISADEV developer dev host EC2.
# devhost_password is passed via -var at apply time and never written to a file.

variable "aws_region" {
  description = "AWS region for the dev host"
  type        = string
  default     = "us-east-1"
}

variable "instance_type" {
  description = "EC2 instance type for the dev host"
  type        = string
  default     = "t3.xlarge"
}

variable "root_volume_size" {
  description = "Root EBS volume size in GB"
  type        = number
  default     = 50
}

variable "key_name" {
  description = "EC2 key pair name for SSH access"
  type        = string
  default     = ""
}

variable "iam_instance_profile" {
  description = "IAM instance profile attached to the dev host"
  type        = string
}

variable "associate_public_ip_address" {
  description = "Whether to associate a public IP"
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags applied to the dev host"
  type        = map(string)
  default = {
    Name        = "XFD CISADEV Dev Host"
    Environment = "dev"
    Owner       = "XFD Dashboard"
  }
}

# SSM parameter paths (values live in SSM, resolved at plan/apply time)
variable "ssm_ami_id" {
  description = "SSM parameter path for the Ubuntu AMI ID"
  type        = string
}

variable "ssm_subnet_id" {
  description = "SSM parameter path for the subnet ID"
  type        = string
}

variable "ssm_security_group_id" {
  description = "SSM parameter path for the security group ID"
  type        = string
}

# Dev host login / desktop
variable "devhost_username" {
  description = "Login username created on the dev host"
  type        = string
  default     = "cisadev"
}

variable "devhost_password" {
  description = "Initial login password. Passed via -var at apply; must be changed on first login."
  type        = string
  sensitive   = true

  validation {
    condition     = length(var.devhost_password) > 0
    error_message = "devhost_password must not be empty."
  }
}

variable "desktop" {
  description = "Desktop environment: ubuntu | cinnamon | xfce"
  type        = string
  default     = "cinnamon"

  validation {
    condition     = contains(["ubuntu", "cinnamon", "xfce"], var.desktop)
    error_message = "desktop must be one of: ubuntu, cinnamon, xfce."
  }
}
