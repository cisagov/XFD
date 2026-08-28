# WAS reporting EC2. This mirrors the P&E/OpenCTI EC2 pattern while retaining
# independent WAS variables and an intentionally smaller 50 GiB gp3 volume.

locals {
  create_was_reporting_instance = var.is_dmz && var.create_was_reporting_instance
}

resource "aws_iam_role" "was_reporting" {
  count              = local.create_was_reporting_instance ? 1 : 0
  name               = "crossfeed-was-reporting-${var.stage}"
  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF

  tags = {
    Project = var.project
    Stage   = var.stage
    Owner   = "Crossfeed managed resource"
  }
}

resource "aws_iam_instance_profile" "was_reporting" {
  count = local.create_was_reporting_instance ? 1 : 0
  name  = "crossfeed-was-reporting-${var.stage}"
  role  = aws_iam_role.was_reporting[0].id
}

resource "aws_iam_role_policy_attachment" "was_reporting_ssm_core" {
  count      = local.create_was_reporting_instance ? 1 : 0
  role       = aws_iam_role.was_reporting[0].name
  policy_arn = "arn:${var.aws_partition}:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# DMZ deployments adopt the same current subnet and security group values as
# P&E, through independent WAS variables so they can diverge later.
data "aws_security_group" "was_reporting" {
  count = local.create_was_reporting_instance ? 1 : 0
  id    = var.was_reporting_security_group_id
}

data "aws_subnet" "was_reporting" {
  count = local.create_was_reporting_instance ? 1 : 0
  id    = var.was_reporting_subnet_id
}

locals {
  # Match the P&E package bootstrap without installing, configuring, or
  # starting the OpenCTI application stack on the WAS reporting host.
  was_reporting_user_data = local.create_was_reporting_instance ? join("\n", [
    "#!/bin/bash",
    "set -euo pipefail",
    "",
    "install -d -m 0755 /opt/was-reporting",
    "cat > /opt/was-reporting/install-deps.sh <<'INSTALL_DEPS_EOF'",
    file("${path.module}/../open-cti/install-deps.sh"),
    "INSTALL_DEPS_EOF",
    "chmod 755 /opt/was-reporting/install-deps.sh",
    "/opt/was-reporting/install-deps.sh",
  ]) : null
}

resource "aws_instance" "was_reporting" {
  count                       = local.create_was_reporting_instance ? 1 : 0
  ami                         = var.was_reporting_ami_id
  instance_type               = var.was_reporting_instance_type
  associate_public_ip_address = false

  subnet_id              = data.aws_subnet.was_reporting[0].id
  vpc_security_group_ids = [data.aws_security_group.was_reporting[0].id]

  iam_instance_profile = aws_iam_instance_profile.was_reporting[0].id

  user_data                   = local.was_reporting_user_data
  user_data_replace_on_change = false

  root_block_device {
    volume_size = var.was_reporting_root_volume_size
    volume_type = var.was_reporting_root_volume_type
  }

  tags = {
    Project = var.project
    Stage   = var.stage
    Name    = "was_reporting"
    Owner   = "Crossfeed managed resource"
  }

  lifecycle {
    ignore_changes  = [ami]
    prevent_destroy = true
  }

  depends_on = [
    aws_iam_role.was_reporting,
    aws_iam_instance_profile.was_reporting,
    aws_iam_role_policy_attachment.was_reporting_ssm_core,
  ]
}
