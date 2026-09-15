aws_region    = "us-east-1"
instance_type = "t3.xlarge"

# SSM parameter paths (values live in SSM, not here)
ssm_ami_id             = "/cisadev/runner/AMI_ID"
ssm_subnet_id          = "/cisadev/runner/SUBNET_ID"
ssm_security_group_id  = "/cisadev/runner/SECURITY_GROUP_ID"
ssm_crowdstrike_cid    = "/cisadev/runner/CROWDSTRIKE_CID"
ssm_crowdstrike_s3_uri = "/cisadev/runner/CROWDSTRIKE_S3_URI"
ssm_crowdstrike_tags   = "/cisadev/runner/CROWDSTRIKE_TAGS"
ssm_runner_url         = "/cisadev/runner/RUNNER_URL"
ssm_runner_group       = "/cisadev/runner/RUNNER_GROUP"

key_name             = "<EC2_KEY_PAIR_NAME>"
iam_instance_profile = "<IAM_INSTANCE_PROFILE>"

tags = {
  Name        = "CyHy Dashboard GitHub Actions Runner"
  Environment = "staging"
  Owner       = "XFD Dashboard"
}

# GitHub Actions runner registration
# (runner_token passed via -var at apply; url/group read from SSM)
runner_name    = "cyhy-dashboard-runner"
runner_version = "2.335.1"
