# Runner EC2 variables. runner_token is passed via -var at apply, never committed.

# --- AWS / general ---
variable "aws_region" {
  description = "AWS region for the CISADEV runner"
  type        = string
  default     = "us-east-1"
}

variable "instance_type" {
  description = "EC2 instance type for the runner"
  type        = string
  default     = "t3.xlarge"
}

variable "root_volume_size" {
  description = "Root EBS volume size in GB"
  type        = number
  default     = 50
}

variable "key_name" {
  description = "EC2 key pair name for SSH access to the runner"
  type        = string
  default     = "" # TBD
}

variable "iam_instance_profile" {
  description = "IAM instance profile attached to the runner EC2"
  type        = string
}

variable "associate_public_ip_address" {
  description = "Whether to associate a public IP with the runner"
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags applied to the runner EC2"
  type        = map(string)
  default = {
    Name        = "CyHy Dashboard GitHub Actions Runner"
    Environment = "staging"
    Owner       = "XFD Dashboard"
  }
}

# --- SSM Parameter Store paths ---
variable "ssm_ami_id" {
  description = "SSM parameter path for the Ubuntu AMI ID"
  type        = string
}

variable "ssm_subnet_id" {
  description = "SSM parameter path for the subnet ID (must have outbound internet access)"
  type        = string
}

variable "ssm_security_group_id" {
  description = "SSM parameter path for the security group ID"
  type        = string
}

# --- GitHub Actions runner registration ---
variable "ssm_runner_url" {
  description = "SSM parameter path for the GitHub enterprise URL"
  type        = string
}

variable "ssm_runner_group" {
  description = "SSM parameter path for the runner group name"
  type        = string
}

variable "runner_name" {
  description = "Name to register the self-hosted runner under"
  type        = string
}

variable "runner_version" {
  description = "GitHub Actions runner release version"
  type        = string
  default     = "2.335.1"
}

variable "runner_token" {
  description = "Ephemeral GitHub Actions runner registration token. Passed via -var at apply time; never stored in a file."
  type        = string
  sensitive   = true
}

# --- CrowdStrike Falcon (mandatory for CISADEV compliance) ---
variable "ssm_crowdstrike_s3_uri" {
  description = "SSM parameter path for the CrowdStrike sensor .deb S3 URI"
  type        = string
}

variable "ssm_crowdstrike_cid" {
  description = "SSM parameter path for the CrowdStrike CID"
  type        = string
}

variable "ssm_crowdstrike_tags" {
  description = "SSM parameter path for the CrowdStrike grouping tags"
  type        = string
}
