aws_region    = "us-east-1"
instance_type = "t3.xlarge"

# SSM parameter paths (values live in SSM, not here)
ssm_ami_id            = "/cisadev/devhost/AMI_ID"
ssm_subnet_id         = "/cisadev/devhost/SUBNET_ID"
ssm_security_group_id = "/cisadev/devhost/SECURITY_GROUP_ID"

key_name             = "<EC2_KEY_PAIR_NAME>"
iam_instance_profile = "<IAM_INSTANCE_PROFILE>"

tags = {
  Name        = "XFD CISADEV Dev Host"
  Environment = "dev"
  Owner       = "XFD Dashboard"
}

# Login / desktop (devhost_password passed via -var at apply)
devhost_username = "cisadev"
desktop          = "cinnamon"
