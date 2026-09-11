aws_region    = "us-east-1"
instance_type = "t3.xlarge"

# SSM parameter paths (values live in SSM, not here)
ssm_ami_id            = "/cisadev/runner/AMI_ID"
ssm_subnet_id         = "/cisadev/runner/SUBNET_ID"
ssm_security_group_id = "/cisadev/runner/SECURITY_GROUP_ID"

key_name             = "<EC2_KEY_PAIR_NAME>"
iam_instance_profile = "<IAM_INSTANCE_PROFILE>"

tags = {
  Name        = "CyHy Dashboard GitHub Actions Runner"
  Environment = "staging"
  Owner       = "XFD Dashboard"
}

# GitHub Actions runner registration (runner_token passed via -var at apply)
runner_url     = "<ENTERPRISE_GITHUB_URL>"
runner_group   = "<RUNNER_GROUP>"
runner_name    = "<RUNNER_NAME>"
runner_version = "2.335.1"

# CrowdStrike (crowdstrike_cid passed via -var at apply)
crowdstrike_s3_uri = "<CROWDSTRIKE_S3_URI>"
crowdstrike_tags   = "<CROWDSTRIKE_TAGS>"
