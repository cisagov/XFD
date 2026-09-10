data "aws_ssm_parameter" "ami_id" {
  name = var.ssm_ami_id
}

data "aws_ssm_parameter" "subnet_id" {
  name = var.ssm_subnet_id
}

data "aws_ssm_parameter" "security_group_id" {
  name = var.ssm_security_group_id
}

resource "aws_instance" "cisadev_xfd_gh_actions_runner_ec2" {
  ami                         = data.aws_ssm_parameter.ami_id.value
  instance_type               = var.instance_type
  subnet_id                   = data.aws_ssm_parameter.subnet_id.value
  vpc_security_group_ids      = [data.aws_ssm_parameter.security_group_id.value]
  key_name                    = var.key_name
  iam_instance_profile        = var.iam_instance_profile
  associate_public_ip_address = var.associate_public_ip_address
  tags                        = var.tags

  root_block_device {
    volume_size = var.root_volume_size
    volume_type = "gp3"
    encrypted   = true
  }

  user_data = templatefile("${path.module}/user_data.sh.tpl", {
    crowdstrike_s3_uri = var.crowdstrike_s3_uri
    crowdstrike_cid    = var.crowdstrike_cid
    crowdstrike_tags   = var.crowdstrike_tags
    runner_url         = var.runner_url
    runner_token       = var.runner_token
    runner_group       = var.runner_group
    runner_name        = var.runner_name
    runner_version     = var.runner_version
  })

  # Token changes on rebuild shouldn't force instance replacement.
  lifecycle {
    ignore_changes = [user_data]
  }
}
