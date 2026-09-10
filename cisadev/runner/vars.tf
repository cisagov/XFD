# vars.tf
# Variable declarations for the CISADEV GitHub Actions runner EC2.
# Values are supplied via cisadev.tfvars, except runner_token which is passed via -var at plan/apply time and is never written to a file.

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

# --- SSM Parameter Store paths (values resolved at plan/apply time) ---
# The actual AMI/subnet/SG IDs live in SSM Parameter Store in CISADEV, not in version control. 
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
variable "runner_url" {
  description = "GitHub enterprise URL the runner registers against"
  type        = string
}

variable "runner_group" {
  description = "GitHub Actions runner group name"
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
variable "crowdstrike_s3_uri" {
  description = "S3 URI of the CrowdStrike Falcon sensor .deb package"
  type        = string
}

variable "crowdstrike_cid" {
  description = "CrowdStrike customer ID (CID) used to register the sensor"
  type        = string
  sensitive   = true
}

variable "crowdstrike_tags" {
  description = "CrowdStrike grouping tags applied to the sensor"
  type        = string
  default     = ""
}
