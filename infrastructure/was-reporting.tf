# WAS reporting EC2 instance. This follows the reusable EC2/IAM/networking
# structure in open_cti.tf without installing the OpenCTI workload.

locals {
  was_reporting_tags = merge({
    Project         = var.project
    Stage           = var.stage
    Name            = "was_reporting"
    Owner           = "Crossfeed managed resource"
    ApplicationRole = "WAS reporting"
    Environment     = var.stage
  }, var.was_reporting_tags)
}

resource "aws_iam_role" "was_reporting" {
  count = var.create_was_reporting_instance ? 1 : 0
  name  = "crossfeed-was-reporting-${var.stage}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
      Effect = "Allow"
    }]
  })
  tags = local.was_reporting_tags
}

resource "aws_iam_instance_profile" "was_reporting" {
  count = var.create_was_reporting_instance ? 1 : 0
  name  = "crossfeed-was-reporting-${var.stage}"
  role  = aws_iam_role.was_reporting[0].id
}

# SSM Session Manager is the administration path; no SSH ingress is needed.
resource "aws_iam_role_policy_attachment" "was_reporting_ssm_core" {
  count      = var.create_was_reporting_instance ? 1 : 0
  role       = aws_iam_role.was_reporting[0].name
  policy_arn = "arn:${var.aws_partition}:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy_attachment" "was_reporting_ssm_service" {
  count      = var.create_was_reporting_instance ? 1 : 0
  role       = aws_iam_role.was_reporting[0].name
  policy_arn = "arn:${var.aws_partition}:iam::aws:policy/service-role/AmazonEC2RoleforSSM"
}

# Restrict Parameter Store reads to WAS reporting's own hierarchy.
resource "aws_iam_role_policy" "was_reporting_ssm_read" {
  count = var.create_was_reporting_instance ? 1 : 0
  name  = "crossfeed-was-reporting-${var.stage}-ssm-read"
  role  = aws_iam_role.was_reporting[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "ssm:GetParameter",
        "ssm:GetParameters",
        "ssm:GetParametersByPath",
      ]
      Resource = "arn:${var.aws_partition}:ssm:${var.aws_region}:*:parameter${var.was_reporting_ssm_path_prefix}*"
    }]
  })
}

# DMZ deployments adopt an approved, pre-existing subnet and security group.
data "aws_subnet" "was_reporting" {
  count = var.create_was_reporting_instance && var.is_dmz ? 1 : 0
  id    = var.was_reporting_subnet_id
}

data "aws_security_group" "was_reporting" {
  count = var.create_was_reporting_instance && var.is_dmz ? 1 : 0
  id    = var.was_reporting_security_group_id
}

# Landing Zone deployments create an egress-only security group. SSM is
# outbound initiated, so no inbound rule is required.
resource "aws_security_group" "was_reporting_lz" {
  count       = var.create_was_reporting_instance && !var.is_dmz ? 1 : 0
  name        = "crossfeed-was-reporting-${var.stage}"
  description = "WAS reporting EC2 (Landing Zone) -- egress only"
  vpc_id      = data.aws_ssm_parameter.vpc_id[0].value

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = local.was_reporting_tags
}

# This group is attached to RDS and scopes access to the WAS host's SG.
resource "aws_security_group" "was_reporting_db_access" {
  count       = var.create_was_reporting_instance && !var.is_dmz ? 1 : 0
  name        = "crossfeed-was-reporting-db-access-${var.stage}"
  description = "Allows the WAS reporting EC2 instance to reach Crossfeed Postgres"
  vpc_id      = data.aws_ssm_parameter.vpc_id[0].value

  ingress {
    description     = "Postgres from WAS reporting EC2"
    from_port       = var.db_port
    to_port         = var.db_port
    protocol        = "tcp"
    security_groups = [aws_security_group.was_reporting_lz[0].id]
  }

  tags = local.was_reporting_tags
}

# The matching Postgres role and GRANT rds_iam are created out of band.
resource "aws_iam_role_policy" "was_reporting_rds_iam_auth" {
  count = var.create_was_reporting_instance && !var.is_dmz ? 1 : 0
  name  = "crossfeed-was-reporting-${var.stage}-rds-iam-auth"
  role  = aws_iam_role.was_reporting[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["rds-db:connect"]
      Resource = "arn:${var.aws_partition}:rds-db:${var.aws_region}:${data.aws_caller_identity.current.account_id}:dbuser:${aws_db_instance.db.resource_id}/${var.was_reporting_db_username}"
    }]
  })
}

resource "aws_instance" "was_reporting" {
  count                       = var.create_was_reporting_instance ? 1 : 0
  ami                         = var.is_dmz ? var.was_reporting_ami_id : var.lz_was_reporting_ami_id
  instance_type               = var.was_reporting_instance_type
  associate_public_ip_address = false

  subnet_id = var.is_dmz ? data.aws_subnet.was_reporting[0].id : data.aws_ssm_parameter.subnet_backend_id[0].value
  vpc_security_group_ids = var.is_dmz ? concat(
    [data.aws_security_group.was_reporting[0].id],
    var.was_reporting_approved_security_group_ids,
    ) : concat(
    [aws_security_group.was_reporting_lz[0].id],
    var.was_reporting_approved_security_group_ids,
  )

  iam_instance_profile = aws_iam_instance_profile.was_reporting[0].id

  # WAS-specific initialization can replace this payload later.
  user_data                   = file("${path.module}/ssm-agent-install.sh")
  user_data_replace_on_change = false

  root_block_device {
    volume_size           = var.was_reporting_root_volume_size
    volume_type           = var.was_reporting_root_volume_type
    encrypted             = true
    delete_on_termination = var.was_reporting_delete_volume_on_termination
  }

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  tags        = local.was_reporting_tags
  volume_tags = local.was_reporting_tags

  lifecycle {
    ignore_changes  = [ami]
    prevent_destroy = true
  }

  depends_on = [
    aws_iam_role.was_reporting,
    aws_iam_instance_profile.was_reporting,
    aws_iam_role_policy_attachment.was_reporting_ssm_core,
    aws_iam_role_policy_attachment.was_reporting_ssm_service,
    aws_iam_role_policy.was_reporting_ssm_read,
    aws_iam_role_policy.was_reporting_rds_iam_auth,
  ]
}
