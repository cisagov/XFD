data "aws_ssm_parameter" "ami_id" {
  name = var.ssm_ami_id
}

data "aws_ssm_parameter" "subnet_id" {
  name = var.ssm_subnet_id
}

data "aws_ssm_parameter" "security_group_id" {
  name = var.ssm_security_group_id
}

data "aws_ssm_parameter" "crowdstrike_cid" {
  name = var.ssm_crowdstrike_cid
}

data "aws_ssm_parameter" "crowdstrike_s3_uri" {
  name = var.ssm_crowdstrike_s3_uri
}

data "aws_ssm_parameter" "crowdstrike_tags" {
  name = var.ssm_crowdstrike_tags
}

data "aws_ssm_parameter" "runner_url" {
  name = var.ssm_runner_url
}

data "aws_ssm_parameter" "runner_group" {
  name = var.ssm_runner_group
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
    crowdstrike_s3_uri = data.aws_ssm_parameter.crowdstrike_s3_uri.value
    crowdstrike_cid    = data.aws_ssm_parameter.crowdstrike_cid.value
    crowdstrike_tags   = data.aws_ssm_parameter.crowdstrike_tags.value
    runner_url         = data.aws_ssm_parameter.runner_url.value
    runner_token       = var.runner_token
    runner_group       = data.aws_ssm_parameter.runner_group.value
    runner_name        = var.runner_name
    runner_version     = var.runner_version
  })

  # Token changes on rebuild shouldn't force instance replacement.
  lifecycle {
    ignore_changes = [user_data]
  }
}
