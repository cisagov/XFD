locals {
  create_was_reporting_instance = var.is_dmz && var.create_was_reporting_instance

  was_reporting_tags = merge({
    Project         = var.project
    Stage           = var.stage
    Name            = "crossfeed-was-reporting-${var.stage}"
    Owner           = "Crossfeed managed resource"
    ApplicationRole = "WAS reporting"
    Environment     = var.stage
  }, var.was_reporting_tags)
}

# The instance profile is managed outside this baseline and must be approved for
# use by the WAS reporting workload before the instance is enabled.
data "aws_iam_instance_profile" "was_reporting" {
  count = local.create_was_reporting_instance ? 1 : 0
  name  = var.was_reporting_iam_instance_profile_name
}

resource "aws_security_group" "was_reporting" {
  count       = local.create_was_reporting_instance ? 1 : 0
  name        = "crossfeed-was-reporting-${var.stage}"
  description = "Approved access for the WAS reporting instance"
  vpc_id      = aws_vpc.crossfeed_vpc[0].id

  dynamic "ingress" {
    for_each = var.was_reporting_ingress_rules

    content {
      description = ingress.value.description
      from_port   = ingress.value.from_port
      to_port     = ingress.value.to_port
      protocol    = ingress.value.protocol
      cidr_blocks = ingress.value.cidr_blocks
    }
  }

  dynamic "egress" {
    for_each = var.was_reporting_egress_rules

    content {
      description = egress.value.description
      from_port   = egress.value.from_port
      to_port     = egress.value.to_port
      protocol    = egress.value.protocol
      cidr_blocks = egress.value.cidr_blocks
    }
  }

  tags = local.was_reporting_tags
}

resource "aws_instance" "was_reporting" {
  count                       = local.create_was_reporting_instance ? 1 : 0
  ami                         = var.was_reporting_ami_id
  instance_type               = var.was_reporting_instance_type
  associate_public_ip_address = false
  subnet_id                   = var.was_reporting_subnet_id != "" ? var.was_reporting_subnet_id : aws_subnet.backend[0].id
  iam_instance_profile        = data.aws_iam_instance_profile.was_reporting[0].name
  vpc_security_group_ids = concat(
    [aws_security_group.was_reporting[0].id],
    var.was_reporting_approved_security_group_ids
  )

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
}
