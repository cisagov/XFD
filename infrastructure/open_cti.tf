# OpenCTI EC2 instance (see ../open-cti/docker-compose.yml for the Docker Compose stack it runs).
#
# This instance already exists -- it was created out-of-band, not by Terraform -- and must be
# adopted via `terraform import aws_instance.open_cti <instance_id>` before this config can be
# applied cleanly. Run `terraform plan` after import and confirm the ONLY diffs are additive
# (new IAM role/profile/attachments, new SSM parameters, `iam_instance_profile` null -> set)
# before ever running `apply`. Any `-/+` (replace) on aws_instance.open_cti means an attribute
# below doesn't match reality and must be corrected first.
#
# prevent_destroy is a second guardrail on top of the create_open_cti_instance flag. To
# intentionally decommission this instance later: remove the `lifecycle` block below in its own
# apply FIRST, then flip create_open_cti_instance to false and apply the destroy. Skipping the
# first step will make Terraform refuse the destroy.

resource "aws_iam_role" "open_cti" {
  count              = var.create_open_cti_instance ? 1 : 0
  name               = "crossfeed-open-cti-${var.stage}"
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

resource "aws_iam_instance_profile" "open_cti" {
  count = var.create_open_cti_instance ? 1 : 0
  name  = "crossfeed-open-cti-${var.stage}"
  role  = aws_iam_role.open_cti[0].id
}

# SSM Session Manager access -- lets this instance be administered without SSH/an open port 22,
# same pattern as email-sender.tf.
resource "aws_iam_role_policy_attachment" "open_cti_ssm_core" {
  count      = var.create_open_cti_instance ? 1 : 0
  role       = aws_iam_role.open_cti[0].name
  policy_arn = "arn:${var.aws_partition}:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy_attachment" "open_cti_ssm_service" {
  count      = var.create_open_cti_instance ? 1 : 0
  role       = aws_iam_role.open_cti[0].name
  policy_arn = "arn:${var.aws_partition}:iam::aws:policy/service-role/AmazonEC2RoleforSSM"
}

# Lets the instance read (but not write) its own secrets back out of SSM Parameter Store --
# needed to re-render open-cti/.env during a rebuild instead of re-entering every value by hand.
resource "aws_iam_role_policy" "open_cti_ssm_read_secrets" {
  count = var.create_open_cti_instance ? 1 : 0
  name  = "crossfeed-open-cti-${var.stage}-ssm-read"
  role  = aws_iam_role.open_cti[0].id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Action = [
        "ssm:GetParameter",
        "ssm:GetParameters",
        "ssm:GetParametersByPath",
      ],
      Resource = "arn:${var.aws_partition}:ssm:${var.aws_region}:*:parameter${var.open_cti_ssm_path_prefix}*"
    }]
  })
}

# Read-only lookups. This security group and subnet already exist and were not created by this
# config -- their ownership/rules predate this Terraform and are unverified, so they're referenced
# here rather than declared/managed as resources.
data "aws_security_group" "open_cti" {
  count = var.create_open_cti_instance ? 1 : 0
  id    = var.open_cti_security_group_id
}

data "aws_subnet" "open_cti" {
  count = var.create_open_cti_instance ? 1 : 0
  id    = var.open_cti_subnet_id
}

resource "aws_instance" "open_cti" {
  count                       = var.create_open_cti_instance ? 1 : 0
  ami                         = var.open_cti_ami_id
  instance_type               = var.open_cti_instance_type
  associate_public_ip_address = false

  subnet_id              = data.aws_subnet.open_cti[0].id
  vpc_security_group_ids = [data.aws_security_group.open_cti[0].id]

  iam_instance_profile = aws_iam_instance_profile.open_cti[0].id

  root_block_device {
    volume_size = var.open_cti_root_volume_size
  }

  tags = {
    Project = var.project
    Stage   = var.stage
    Name    = "pe_ec2" # TO-DO: rename to "open-cti" instance and change this value.
    Owner   = "Crossfeed managed resource"
  }

  lifecycle {
    ignore_changes  = [ami]
    prevent_destroy = true
  }

  depends_on = [
    aws_iam_role.open_cti,
    aws_iam_instance_profile.open_cti,
    aws_iam_role_policy_attachment.open_cti_ssm_core,
    aws_iam_role_policy_attachment.open_cti_ssm_service,
  ]
}

# Placeholder SecureString parameters for every secret currently living only in the live
# instance's open-cti/.env. Terraform creates the parameter shells; it never sets or overwrites
# the real value (overwrite = false, ignore_changes = [value]) since these secrets already exist
# and can't be safely regenerated -- e.g. rotating OPENCTI_ENCRYPTION_KEY would break decryption
# of existing data, and rotating connector API keys would require re-registering with each
# third-party service. Set the real values once, out-of-band, e.g.:
#   aws ssm put-parameter --name "/crossfeed/staging/OPENCTI_ADMIN_PASSWORD" \
#     --type SecureString --value "<real value>" --overwrite
resource "aws_ssm_parameter" "open_cti_secrets" {
  for_each  = var.create_open_cti_instance ? var.open_cti_secret_keys : toset([])
  name      = "${var.open_cti_ssm_path_prefix}/${each.key}"
  type      = "SecureString"
  value     = "REPLACE_ME"
  overwrite = false

  lifecycle {
    ignore_changes = [value]
  }

  tags = {
    Project = var.project
    Stage   = var.stage
    Owner   = "Crossfeed managed resource"
  }
}
