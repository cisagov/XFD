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
#
# user_data / .env automation (see local.open_cti_user_data below): `user_data` is normally a
# ForceNew attribute on aws_instance -- setting it here would otherwise plan a `-/+ replace` of
# this already-running, prevent_destroy'd instance, which prevent_destroy would then hard-block.
# user_data_replace_on_change = false avoids that, but it also means user_data genuinely only
# executes at an instance's TRUE first boot -- it will NOT retroactively run against stage-cd's
# already-running instance just because `terraform apply` sets/changes this field. Backfilling
# stage-cd requires manually replaying the same payload via `aws ssm send-command` -- see
# output.open_cti_backfill_script for the exact steps. A brand-new instance (e.g. a future `stage`
# deployment) needs no special handling: user_data runs normally on its real first boot.

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

# Delivery for open-cti/docker-compose.yml + rabbitmq.conf -- confirmed byte-for-byte identical
# (modulo whitespace/comments) to what's actually running on stage-cd on 2026-08-17, so this repo's
# copies are safe to treat as the source of truth. Can't go through user_data like bootstrap.sh/
# env.static do -- docker-compose.yml alone is ~18KB, over EC2's 16KB user_data limit -- so
# bootstrap.sh instead `aws s3 cp`s both from here every boot, before open-cti-compose.service
# starts. BucketOwnerEnforced (ACLs fully disabled): only ever written by CI and read by this
# instance's role, no cross-account/ACL-based access needed.
#
# Terraform owns the bucket itself (below) -- policy, encryption, versioning, logging, and the IAM
# read grant. It deliberately does NOT own the objects in it: .github/workflows/
# open-cti-config-sync.yml uploads open-cti/docker-compose.yml + rabbitmq.conf on every push to
# develop that touches either file, so a config change reaches the bucket the moment it merges,
# without waiting on (or requiring) a `terraform apply`. That workflow's target bucket name is a
# hardcoded literal, kept in sync with var.open_cti_config_bucket_name by convention -- see that
# workflow file's header comment.
#
# Operational note: a brand-new bucket starts empty. Nothing lands in it until the next push to
# develop that touches either file merges (or someone seeds it by hand with one `aws s3 cp`) -- so
# for a genuinely new environment, land a no-op touch/merge to develop before that instance's first
# real boot, or bootstrap.sh's S3 fetch will fail with a 404.
resource "aws_s3_bucket" "open_cti_config" {
  count  = var.create_open_cti_instance ? 1 : 0
  bucket = var.open_cti_config_bucket_name
  tags = {
    Project = var.project
    Stage   = var.stage
    Owner   = "Crossfeed managed resource"
  }
}

resource "aws_s3_bucket_public_access_block" "open_cti_config" {
  count                   = var.create_open_cti_instance ? 1 : 0
  bucket                  = aws_s3_bucket.open_cti_config[0].id
  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_policy" "open_cti_config" {
  count  = var.create_open_cti_instance ? 1 : 0
  bucket = aws_s3_bucket.open_cti_config[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "RequireSSLRequests"
        Action    = "s3:*"
        Effect    = "Deny"
        Principal = "*"
        Resource = [
          aws_s3_bucket.open_cti_config[0].arn,
          "${aws_s3_bucket.open_cti_config[0].arn}/*"
        ]
        Condition = {
          Bool = { "aws:SecureTransport" = "false" }
        }
      }
    ]
  })
}

resource "aws_s3_bucket_ownership_controls" "open_cti_config" {
  count  = var.create_open_cti_instance ? 1 : 0
  bucket = aws_s3_bucket.open_cti_config[0].id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "open_cti_config" {
  count  = var.create_open_cti_instance ? 1 : 0
  bucket = aws_s3_bucket.open_cti_config[0].id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "open_cti_config" {
  count  = var.create_open_cti_instance ? 1 : 0
  bucket = aws_s3_bucket.open_cti_config[0].id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_logging" "open_cti_config" {
  count         = var.create_open_cti_instance ? 1 : 0
  bucket        = aws_s3_bucket.open_cti_config[0].id
  target_bucket = aws_s3_bucket.logging_bucket.id
  target_prefix = "open_cti_config/"
}

resource "aws_iam_role_policy" "open_cti_s3_config_read" {
  count = var.create_open_cti_instance ? 1 : 0
  name  = "crossfeed-open-cti-${var.stage}-s3-config-read"
  role  = aws_iam_role.open_cti[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:GetObject"]
      Resource = "${aws_s3_bucket.open_cti_config[0].arn}/*"
    }]
  })
}

# Read-only lookups, stage-cd (is_dmz) ONLY. This security group and subnet already exist and were
# not created by this config -- their ownership/rules predate this Terraform and are unverified, so
# they're referenced here rather than declared/managed as resources. There is nothing to adopt for a
# genuinely new LZ deployment (e.g. stage) -- see the aws_security_group.open_cti_lz /
# data.aws_ssm_parameter.subnet_backend_id branch below for that case instead.
data "aws_security_group" "open_cti" {
  count = var.create_open_cti_instance && var.is_dmz ? 1 : 0
  id    = var.open_cti_security_group_id
}

data "aws_subnet" "open_cti" {
  count = var.create_open_cti_instance && var.is_dmz ? 1 : 0
  id    = var.open_cti_subnet_id
}

# LZ (!is_dmz) ONLY -- Terraform-managed, unlike the data-source adoption above, since a fresh LZ
# deployment has nothing pre-existing to adopt. Egress-only: SSM Session Manager (this instance's
# only administration path, same as db_accessor/email-sender) is outbound-initiated, needs no
# inbound rule.
resource "aws_security_group" "open_cti_lz" {
  count       = var.create_open_cti_instance && !var.is_dmz ? 1 : 0
  name        = "crossfeed-open-cti-${var.stage}"
  description = "OpenCTI EC2 (Landing Zone) -- egress only"
  vpc_id      = data.aws_ssm_parameter.vpc_id[0].value

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Project = var.project
    Stage   = var.stage
    Owner   = "Crossfeed managed resource"
  }
}

# LZ (!is_dmz) ONLY -- grants OpenCTI's EC2 (and only OpenCTI's EC2, by security-group reference
# rather than a CIDR block) inbound access to the DB on var.db_port. Attached to
# aws_db_instance.db's vpc_security_group_ids in database.tf ALONGSIDE allow_internal_lz, not
# instead of it -- allow_internal_lz already permits the whole VPC CIDR on every port, so this SG's
# only purpose is documenting/scoping *this specific* grant explicitly rather than relying on that
# broader rule. No egress block: this SG is only ever attached to the DB instance, which doesn't
# need outbound rules of its own here -- allow_internal_lz's existing open egress already covers it
# (AWS unions egress rules across all SGs attached to the same ENI).
resource "aws_security_group" "open_cti_db_access" {
  count       = var.create_open_cti_instance && !var.is_dmz ? 1 : 0
  name        = "crossfeed-open-cti-db-access-${var.stage}"
  description = "Allows the OpenCTI EC2 (Landing Zone) to reach the Crossfeed Postgres DB"
  vpc_id      = data.aws_ssm_parameter.vpc_id[0].value

  ingress {
    description     = "Postgres from OpenCTI EC2"
    from_port       = var.db_port
    to_port         = var.db_port
    protocol        = "tcp"
    security_groups = [aws_security_group.open_cti_lz[0].id]
  }

  tags = {
    Project = var.project
    Stage   = var.stage
    Owner   = "Crossfeed managed resource"
  }
}

# LZ (!is_dmz) ONLY -- IAM database authentication instead of a static password: OpenCTI generates a
# short-lived auth token (`aws rds generate-db-auth-token`) per connection rather than ever storing a
# DB password on the box. Scoped to one specific DB role (var.open_cti_db_username), not var.db_port
# generally. Requires a matching, out-of-band `GRANT rds_iam TO <role>` in Postgres itself before
# this grant is actually useful -- see var.open_cti_db_username's description. IAM auth also requires
# the connection itself to use SSL/TLS, independent of aws_db_parameter_group.default's
# rds.force_ssl setting.
resource "aws_iam_role_policy" "open_cti_rds_iam_auth" {
  count = var.create_open_cti_instance && !var.is_dmz ? 1 : 0
  name  = "crossfeed-open-cti-${var.stage}-rds-iam-auth"
  role  = aws_iam_role.open_cti[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["rds-db:connect"]
      Resource = "arn:${var.aws_partition}:rds-db:${var.aws_region}:${data.aws_caller_identity.current.account_id}:dbuser:${aws_db_instance.db.resource_id}/${var.open_cti_db_username}"
    }]
  })
}

locals {
  # Full boot-time payload for aws_instance.open_cti: writes env.static,
  # bootstrap.sh, and both systemd units to /opt/open-cti //
  # /etc/systemd/system, then enables + starts them -- see open-cti/bootstrap.sh
  # and open-cti/systemd/*.service for what actually runs on every boot after
  # that.
  #
  # Deliberately built with join()/file(), NOT one big templatefile() or HCL
  # heredoc over the whole thing: bootstrap.sh and the unit files are real
  # scripts full of their own ${...} syntax (bash parameter expansion, systemd
  # specifiers) that Terraform's template interpolation would otherwise try --
  # and fail -- to parse as Terraform variables. file() returns raw bytes with
  # no reinterpretation, so nesting its result inside join() carries each
  # embedded file through untouched. Only the tiny env header actually needs
  # Terraform-side interpolation, so that's the one piece using templatefile().
  #
  # Also exposed via output.open_cti_backfill_script (output.tf) so the exact
  # same payload can be replayed against the already-running stage-cd instance
  # -- see that output's description for the runbook, and this resource's
  # header comment for why `terraform apply` alone won't do it automatically.
  open_cti_user_data = var.create_open_cti_instance ? join("\n", [
    "#!/bin/bash",
    "set -euo pipefail",
    "",
    templatefile("${path.module}/open_cti_user_data_env.sh.tpl", {
      ssm_path_prefix     = var.open_cti_ssm_path_prefix
      config_bucket       = var.open_cti_config_bucket_name
      opencti_host        = var.open_cti_host
      opencti_admin_email = var.open_cti_admin_email
      smtp_hostname       = var.open_cti_smtp_hostname
      censys_org_id       = var.open_cti_censys_org_id
      qualys_api_username = var.open_cti_qualys_api_username
      xtm_one_host        = var.open_cti_xtm_one_host
      xtm_one_admin_email = var.open_cti_xtm_one_admin_email
    }),
    "",
    "cat > /opt/open-cti/env.static <<'ENV_STATIC_EOF'",
    file("${path.module}/../open-cti/env.static"),
    "ENV_STATIC_EOF",
    "",
    "cat > /opt/open-cti/bootstrap.sh <<'BOOTSTRAP_SH_EOF'",
    file("${path.module}/../open-cti/bootstrap.sh"),
    "BOOTSTRAP_SH_EOF",
    "chmod 755 /opt/open-cti/bootstrap.sh",
    "",
    "cat > /etc/systemd/system/open-cti-render-env.service <<'RENDER_UNIT_EOF'",
    file("${path.module}/../open-cti/systemd/open-cti-render-env.service"),
    "RENDER_UNIT_EOF",
    "",
    "cat > /etc/systemd/system/open-cti-compose.service <<'COMPOSE_UNIT_EOF'",
    file("${path.module}/../open-cti/systemd/open-cti-compose.service"),
    "COMPOSE_UNIT_EOF",
    "",
    "systemctl daemon-reload",
    "systemctl enable --now open-cti-render-env.service open-cti-compose.service",
  ]) : null
}

resource "aws_instance" "open_cti" {
  count                       = var.create_open_cti_instance ? 1 : 0
  ami                         = var.open_cti_ami_id
  instance_type               = var.open_cti_instance_type
  associate_public_ip_address = false

  # stage-cd (is_dmz): adopt the pre-existing subnet/SG via the data sources above.
  # stage/prod (!is_dmz, LZ): the LZ subnet + the Terraform-managed SG above -- see both
  # resources' comments for why this branch can't reuse the data-source adoption pattern.
  subnet_id              = var.is_dmz ? data.aws_subnet.open_cti[0].id : data.aws_ssm_parameter.subnet_backend_id[0].value
  vpc_security_group_ids = var.is_dmz ? [data.aws_security_group.open_cti[0].id] : [aws_security_group.open_cti_lz[0].id]

  iam_instance_profile = aws_iam_instance_profile.open_cti[0].id

  # See this file's header comment for why user_data_replace_on_change = false
  # is required here, and what it does/doesn't mean for stage-cd vs. a
  # genuinely new instance.
  user_data                   = local.open_cti_user_data
  user_data_replace_on_change = false

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
    # user_data's first boot fetches secrets/config via these -- make sure IAM
    # has actually propagated before the instance exists to use it. (The S3
    # objects themselves are NOT a Terraform dependency -- see the bucket's
    # comment above -- open-cti-config-sync.yml owns keeping those current.)
    aws_iam_role_policy.open_cti_ssm_read_secrets,
    aws_iam_role_policy.open_cti_s3_config_read,
    # LZ-only (!is_dmz) -- harmless no-op count=0 references on stage-cd.
    aws_iam_role_policy.open_cti_rds_iam_auth,
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
