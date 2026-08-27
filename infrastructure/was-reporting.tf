# WAS reporting EC2 instance. This follows the reusable EC2/IAM/networking
# structure in open_cti.tf without installing the OpenCTI workload.

locals {
  # WAS reporting is a DMZ-only workload. Using this local for every resource
  # guarantees the feature flag is a no-op in Landing Zone environments.
  create_was_reporting_instance = var.is_dmz && var.create_was_reporting_instance

  # staging-cd shares the staging Parameter Store namespace; other stages use
  # their own namespace unless an explicit override is supplied.
  was_reporting_ssm_stage = var.stage == "staging-cd" ? "staging" : var.stage
  was_reporting_ssm_path_prefix = trimsuffix(coalesce(
    var.was_reporting_ssm_path_prefix,
    "/crossfeed/${local.was_reporting_ssm_stage}/was-reporting",
  ), "/")

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
  count = local.create_was_reporting_instance ? 1 : 0
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
  count = local.create_was_reporting_instance ? 1 : 0
  name  = "crossfeed-was-reporting-${var.stage}"
  role  = aws_iam_role.was_reporting[0].id
}

# SSM Session Manager is the administration path; no SSH ingress is needed.
resource "aws_iam_role_policy_attachment" "was_reporting_ssm_core" {
  count      = local.create_was_reporting_instance ? 1 : 0
  role       = aws_iam_role.was_reporting[0].name
  policy_arn = "arn:${var.aws_partition}:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# Restrict Parameter Store reads to WAS reporting's own hierarchy.
resource "aws_iam_role_policy" "was_reporting_ssm_read" {
  count = local.create_was_reporting_instance ? 1 : 0
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
      Resource = "arn:${var.aws_partition}:ssm:${var.aws_region}:*:parameter${local.was_reporting_ssm_path_prefix}/*"
    }]
  })
}

# Parameter Store values encrypted with a customer-managed key need a
# separate, narrowly scoped decrypt grant. No policy is created when unset.
resource "aws_iam_role_policy" "was_reporting_kms_decrypt" {
  count = local.create_was_reporting_instance && var.was_reporting_kms_key_arn != null ? 1 : 0
  name  = "crossfeed-was-reporting-${var.stage}-kms-decrypt"
  role  = aws_iam_role.was_reporting[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["kms:Decrypt"]
      Resource = var.was_reporting_kms_key_arn
      Condition = {
        StringEquals = {
          "kms:ViaService" = "ssm.${var.aws_region}.amazonaws.com"
        }
        StringLike = {
          "kms:EncryptionContext:PARAMETER_ARN" = "arn:${var.aws_partition}:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter${local.was_reporting_ssm_path_prefix}/*"
        }
      }
    }]
  })
}

# DMZ deployments adopt an approved, pre-existing subnet and security group.
data "aws_subnet" "was_reporting" {
  count = local.create_was_reporting_instance ? 1 : 0
  id    = var.was_reporting_subnet_id

  lifecycle {
    precondition {
      condition     = trimspace(var.was_reporting_subnet_id) != ""
      error_message = "was_reporting_subnet_id must be set when WAS reporting is enabled in a DMZ environment."
    }
  }
}

data "aws_security_group" "was_reporting" {
  count = local.create_was_reporting_instance ? 1 : 0
  id    = var.was_reporting_security_group_id

  lifecycle {
    precondition {
      condition     = trimspace(var.was_reporting_security_group_id) != ""
      error_message = "was_reporting_security_group_id must be set when WAS reporting is enabled in a DMZ environment."
    }
  }
}

resource "aws_instance" "was_reporting" {
  count = local.create_was_reporting_instance ? 1 : 0
  # This currently matches OpenCTI's approved DMZ AMI, but remains separate so
  # either workload can change AMIs independently in the future.
  ami                         = var.was_reporting_ami_id
  instance_type               = var.was_reporting_instance_type
  associate_public_ip_address = false

  subnet_id = data.aws_subnet.was_reporting[0].id
  vpc_security_group_ids = concat(
    [data.aws_security_group.was_reporting[0].id],
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
    ignore_changes = [ami]

    precondition {
      condition     = trimspace(var.was_reporting_ami_id) != ""
      error_message = "was_reporting_ami_id must be set before enabling WAS reporting."
    }
  }

  # The instance-profile reference already orders role/profile creation. These
  # policy dependencies ensure boot-time SSM and configuration access exists
  # before EC2 starts user_data.
  depends_on = [
    aws_iam_role_policy_attachment.was_reporting_ssm_core,
    aws_iam_role_policy.was_reporting_ssm_read,
    aws_iam_role_policy.was_reporting_kms_decrypt,
  ]
}
