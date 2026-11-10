
resource "aws_s3_bucket" "reports_bucket" {
  bucket = var.reports_bucket_name
  tags = {
    Project = var.project
    Stage   = var.stage
    Owner   = "Crossfeed managed resource"
  }
}

resource "aws_s3_bucket_policy" "reports_bucket" {
  bucket = var.reports_bucket_name
  policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Sid" : "RequireSSLRequests",
        "Action" : "s3:*",
        "Effect" : "Deny",
        "Principal" : "*",
        "Resource" : [
          aws_s3_bucket.reports_bucket.arn,
          "${aws_s3_bucket.reports_bucket.arn}/*"
        ],
        "Condition" : {
          "Bool" : {
            "aws:SecureTransport" : "false"
          }
        }
      }
    ]
  })
}

resource "aws_s3_bucket_acl" "reports_bucket" {
  count  = var.is_dmz ? 1 : 0
  bucket = aws_s3_bucket.reports_bucket.id
  acl    = "private"
}

resource "aws_s3_bucket_ownership_controls" "reports_bucket" {
  count  = var.is_dmz ? 1 : 0
  bucket = aws_s3_bucket.reports_bucket.id
  rule {
    object_ownership = "ObjectWriter"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "reports_bucket" {
  bucket = aws_s3_bucket.reports_bucket.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "reports_bucket" {
  bucket = aws_s3_bucket.reports_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_logging" "reports_bucket" {
  bucket        = aws_s3_bucket.reports_bucket.id
  target_bucket = aws_s3_bucket.logging_bucket.id
  target_prefix = "reports_bucket/"
}

resource "aws_s3_bucket" "pe_db_backups_bucket" {
  bucket = var.pe_db_backups_bucket_name
  tags = {
    Project = var.project
    Stage   = var.stage
    Owner   = "Crossfeed managed resource"
  }
}

resource "aws_s3_bucket_policy" "pe_db_backups_bucket" {
  bucket = aws_s3_bucket.pe_db_backups_bucket.id
  policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Sid" : "RequireSSLRequests",
        "Action" : "s3:*",
        "Effect" : "Deny",
        "Principal" : "*",
        "Resource" : [
          aws_s3_bucket.pe_db_backups_bucket.arn,
          "${aws_s3_bucket.pe_db_backups_bucket.arn}/*"
        ],
        "Condition" : {
          "Bool" : {
            "aws:SecureTransport" : "false"
          }
        }
      }
    ]
  })
}

resource "aws_s3_bucket_acl" "pe_db_backups_bucket" {
  count  = var.is_dmz ? 1 : 0
  bucket = aws_s3_bucket.pe_db_backups_bucket.id
  acl    = "private"
}

resource "aws_s3_bucket_ownership_controls" "pe_db_backups_bucket" {
  count  = var.is_dmz ? 1 : 0
  bucket = aws_s3_bucket.pe_db_backups_bucket.id
  rule {
    object_ownership = "ObjectWriter"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "pe_db_backups_bucket" {
  bucket = aws_s3_bucket.pe_db_backups_bucket.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "pe_db_backups_bucket" {
  bucket = aws_s3_bucket.pe_db_backups_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_logging" "pe_db_backups_bucket" {
  bucket        = aws_s3_bucket.pe_db_backups_bucket.id
  target_bucket = aws_s3_bucket.logging_bucket.id
  target_prefix = "pe_db_backups_bucket/"
}

resource "aws_s3_bucket" "crossfeed-lz-sync" {
  count  = var.is_dmz ? 1 : 0
  bucket = var.crossfeed-lz-sync_name
  tags = {
    Project = var.project
    Stage   = var.stage
  }
}

resource "aws_s3_bucket_policy" "crossfeed-lz-sync" {
  count  = var.is_dmz ? 1 : 0
  bucket = var.crossfeed-lz-sync_name
  policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Sid" : "RequireSSLRequests",
        "Action" : "s3:*",
        "Effect" : "Deny",
        "Principal" : "*",
        "Resource" : [
          aws_s3_bucket.crossfeed-lz-sync[0].arn,
          "${aws_s3_bucket.crossfeed-lz-sync[0].arn}/*"
        ],
        "Condition" : {
          "Bool" : {
            "aws:SecureTransport" : "false"
          }
        }
      }
    ]
  })
}

resource "aws_s3_bucket_acl" "crossfeed-lz-sync" {
  count  = var.is_dmz ? 1 : 0
  bucket = aws_s3_bucket.crossfeed-lz-sync[0].id
  acl    = "private"
}

resource "aws_s3_bucket_server_side_encryption_configuration" "crossfeed-lz-sync" {
  count  = var.is_dmz ? 1 : 0
  bucket = aws_s3_bucket.crossfeed-lz-sync[0].id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket" "crossfeed-xpanse-org-sync" {
  count  = var.is_dmz ? 1 : 0
  bucket = var.xpanse_org_sync_bucket_name
  tags = {
    Project = var.project
    Stage   = var.stage
  }
}

resource "aws_s3_bucket_policy" "crossfeed-xpanse-org-sync" {
  count  = var.is_dmz ? 1 : 0
  bucket = var.xpanse_org_sync_bucket_name
  policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Sid" : "RequireSSLRequests",
        "Action" : "s3:*",
        "Effect" : "Deny",
        "Principal" : "*",
        "Resource" : [
          aws_s3_bucket.crossfeed-xpanse-org-sync[0].arn,
          "${aws_s3_bucket.crossfeed-xpanse-org-sync[0].arn}/*"
        ],
        "Condition" : {
          "Bool" : {
            "aws:SecureTransport" : "false"
          }
        }
      }
    ]
  })
}

resource "aws_s3_bucket_acl" "crossfeed-xpanse-org-sync" {
  count  = var.is_dmz ? 1 : 0
  bucket = aws_s3_bucket.crossfeed-xpanse-org-sync[0].id
  acl    = "private"
}

resource "aws_s3_bucket_server_side_encryption_configuration" "crossfeed-xpanse-org-sync" {
  count  = var.is_dmz ? 1 : 0
  bucket = aws_s3_bucket.crossfeed-xpanse-org-sync[0].id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_ownership_controls" "crossfeed-xpanse-org-sync" {
  count  = var.is_dmz ? 1 : 0
  bucket = aws_s3_bucket.crossfeed-xpanse-org-sync[0].id
  rule {
    object_ownership = "ObjectWriter"
  }
}

resource "aws_s3_bucket_logging" "crossfeed-xpanse-org-sync" {
  count         = var.is_dmz ? 1 : 0
  bucket        = aws_s3_bucket.crossfeed-xpanse-org-sync[0].id
  target_bucket = aws_s3_bucket.logging_bucket.id
  target_prefix = "crossfeed-xpanse-org-sync/"
}

resource "aws_s3_bucket" "zscaler_cert_bucket" {
  count  = var.is_dmz ? 0 : 1
  bucket = var.zscaler_cert_bucket_name
  tags = {
    Project = var.project
    Stage   = var.stage
    Owner   = "Crossfeed managed resource"
  }
}

resource "aws_s3_bucket_policy" "zscaler_cert_bucket" {
  count  = var.is_dmz ? 0 : 1
  bucket = aws_s3_bucket.zscaler_cert_bucket[0].id
  policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Sid" : "RequireSSLRequests",
        "Action" : "s3:*",
        "Effect" : "Deny",
        "Principal" : "*",
        "Resource" : [
          aws_s3_bucket.zscaler_cert_bucket[0].arn,
          "${aws_s3_bucket.zscaler_cert_bucket[0].arn}/*"
        ],
        "Condition" : {
          "Bool" : {
            "aws:SecureTransport" : "false"
          }
        }
      }
    ]
  })
}

resource "aws_s3_bucket_ownership_controls" "zscaler_cert_bucket" {
  count  = var.is_dmz ? 0 : 1
  bucket = aws_s3_bucket.zscaler_cert_bucket[0].id
  rule {
    object_ownership = "ObjectWriter"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "zscaler_cert_bucket" {
  count  = var.is_dmz ? 0 : 1
  bucket = aws_s3_bucket.zscaler_cert_bucket[0].id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "zscaler_cert_bucket" {
  count  = var.is_dmz ? 0 : 1
  bucket = aws_s3_bucket.zscaler_cert_bucket[0].id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_logging" "zscaler_cert_bucket" {
  count         = var.is_dmz ? 0 : 1
  bucket        = aws_s3_bucket.zscaler_cert_bucket[0].id
  target_bucket = aws_s3_bucket.logging_bucket.id
  target_prefix = "zscaler_cert_bucket/"
}


resource "aws_s3_bucket" "django_env_bucket" {
  bucket = var.django_env_bucket_name
  tags = {
    Project = var.project
    Stage   = var.stage
    Owner   = "Crossfeed managed resource"
  }
}

resource "aws_s3_bucket_policy" "django_env_bucket" {
  bucket = aws_s3_bucket.django_env_bucket.id
  policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Sid" : "RequireSSLRequests",
        "Action" : "s3:*",
        "Effect" : "Deny",
        "Principal" : "*",
        "Resource" : [
          aws_s3_bucket.django_env_bucket.arn,
          "${aws_s3_bucket.django_env_bucket.arn}/*"
        ],
        "Condition" : {
          "Bool" : {
            "aws:SecureTransport" : "false"
          }
        }
      }
    ]
  })
}

# Block all public access (belt & suspenders)
resource "aws_s3_bucket_public_access_block" "django_env_bucket" {
  bucket                  = aws_s3_bucket.django_env_bucket.id
  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "django_env_bucket" {
  bucket = aws_s3_bucket.django_env_bucket.id
  rule {
    object_ownership = "ObjectWriter"
  }
}

# Default encryption with KMS
resource "aws_s3_bucket_server_side_encryption_configuration" "django_env_bucket" {
  bucket = aws_s3_bucket.django_env_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.django_env.arn
    }
  }
}

resource "aws_s3_bucket_versioning" "django_env_bucket" {
  bucket = aws_s3_bucket.django_env_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_logging" "django_env_bucket" {
  bucket        = aws_s3_bucket.django_env_bucket.id
  target_bucket = aws_s3_bucket.logging_bucket.id
  target_prefix = "django_env_bucket/"
}

# CyHy sharing adopts controls on the existing WAS bucket. It does not create
# the bucket or change the encryption defaults used by existing WAS clients.
locals {
  techops_reports_bucket_arn = "arn:${var.aws_partition}:s3:::${var.was_reporting_reports_bucket_name}"
  techops_reports_prefixes = [
    "cybex_scorecard/",
    "cyhy_ad-hoc_notifications/",
    "cyhy_vs_reports/",
    "https_reports/",
    "trustymail_reports/",
  ]
  # Retention is intentionally independent of access permissions. Giving a
  # future role access to another prefix must not schedule that data for deletion.
  techops_reports_retention_days_by_prefix = {
    "cybex_scorecard/"           = 14
    "cyhy_ad-hoc_notifications/" = 14
    "cyhy_vs_reports/"           = 14
    "https_reports/"             = 14
    "trustymail_reports/"        = 14
  }
  techops_reports_object_arns = [for prefix in local.techops_reports_prefixes : "${local.techops_reports_bucket_arn}/${prefix}*"]
  techops_reports_producer_actions = [
    "s3:AbortMultipartUpload",
    "s3:ListMultipartUploadParts",
    "s3:PutObject",
  ]
  techops_reports_existing_policy = jsondecode(
    var.techops_reports.enabled ? var.techops_reports.existing_bucket_policy_json : "{\"Version\":\"2012-10-17\",\"Statement\":[]}"
  )
  techops_reports_policy = merge(local.techops_reports_existing_policy, {
    Statement = concat(
      flatten([local.techops_reports_existing_policy.Statement]),
      [
        {
          Sid       = "TechOpsReportsRequireTLS"
          Effect    = "Deny"
          Principal = "*"
          Action    = "s3:*"
          Resource  = local.techops_reports_object_arns
          Condition = {
            Bool = {
              "aws:SecureTransport"       = "false"
              "aws:PrincipalIsAWSService" = "false"
            }
          }
        },
        {
          Sid       = "TechOpsReportsRequireKmsEncryption"
          Effect    = "Deny"
          Principal = "*"
          Action    = "s3:PutObject"
          Resource  = local.techops_reports_object_arns
          Condition = {
            StringNotEquals = { "s3:x-amz-server-side-encryption" = "aws:kms" }
          }
        },
        {
          Sid       = "TechOpsReportsRequireApprovedKey"
          Effect    = "Deny"
          Principal = "*"
          Action    = "s3:PutObject"
          Resource  = local.techops_reports_object_arns
          Condition = {
            StringNotEquals = { "s3:x-amz-server-side-encryption-aws-kms-key-id" = var.techops_reports.kms_key_arn }
          }
        },
        {
          Sid       = "TechOpsReportsAllowProducers"
          Effect    = "Allow"
          Principal = { AWS = sort(tolist(var.techops_reports.producer_role_arns)) }
          Action    = local.techops_reports_producer_actions
          Resource  = local.techops_reports_object_arns
        },
      ],
      # Analyst download grants are independent of producer uploads. Omit the
      # statements entirely when no reader roles have been configured.
      [for statement in [
        {
          Sid       = "TechOpsReportsAllowReaders"
          Effect    = "Allow"
          Principal = { AWS = sort(tolist(var.techops_reports.reader_role_arns)) }
          Action    = "s3:GetObject"
          Resource  = local.techops_reports_object_arns
        },
        {
          Sid       = "TechOpsReportsAllowReaderListing"
          Effect    = "Allow"
          Principal = { AWS = sort(tolist(var.techops_reports.reader_role_arns)) }
          Action    = "s3:ListBucket"
          Resource  = local.techops_reports_bucket_arn
          Condition = {
            StringLike = { "s3:prefix" = [for prefix in local.techops_reports_prefixes : "${prefix}*"] }
            Bool       = { "aws:SecureTransport" = "true" }
          }
        },
      ] : statement if length(var.techops_reports.reader_role_arns) > 0],
      [
        {
          Sid       = "TechOpsReportsAllowBucketLocation"
          Effect    = "Allow"
          Principal = { AWS = sort(tolist(setunion(var.techops_reports.producer_role_arns, var.techops_reports.reader_role_arns))) }
          Action    = "s3:GetBucketLocation"
          Resource  = local.techops_reports_bucket_arn
          Condition = { Bool = { "aws:SecureTransport" = "true" } }
        },
      ]
    )
  })
  techops_reports_kms_conditions = {
    StringEquals = { "kms:ViaService" = "s3.us-east-1.amazonaws.com" }
    ArnLike = {
      "kms:EncryptionContext:aws:s3:arn" = [local.techops_reports_bucket_arn, "${local.techops_reports_bucket_arn}/*"]
    }
  }
}

resource "aws_s3_bucket_policy" "techops_reports" {
  provider = aws.main
  count    = var.techops_reports.enabled ? 1 : 0
  bucket   = var.was_reporting_reports_bucket_name
  policy   = jsonencode(local.techops_reports_policy)

  lifecycle {
    prevent_destroy = true
  }
}

# S3 stores one complete lifecycle configuration per bucket. The input guard
# prevents this ME-only resource from replacing unreviewed existing WAS rules.
resource "aws_s3_bucket_lifecycle_configuration" "techops_reports" {
  provider              = aws.main
  count                 = var.techops_reports.enabled && var.techops_reports.manage_retention ? 1 : 0
  bucket                = var.was_reporting_reports_bucket_name
  expected_bucket_owner = "957221700844"

  dynamic "rule" {
    for_each = local.techops_reports_retention_days_by_prefix

    content {
      id     = "techops-expire-${trimsuffix(rule.key, "/")}"
      status = "Enabled"

      filter {
        prefix = rule.key
      }

      expiration {
        days = rule.value
      }

      # In versioned buckets, current-version expiration leaves a noncurrent
      # copy. It becomes eligible for permanent cleanup one day later.
      noncurrent_version_expiration {
        noncurrent_days = 1
      }

      abort_incomplete_multipart_upload {
        days_after_initiation = 1
      }
    }
  }

  dynamic "rule" {
    for_each = local.techops_reports_retention_days_by_prefix

    content {
      id     = "techops-markers-${trimsuffix(rule.key, "/")}"
      status = "Enabled"

      filter {
        prefix = rule.key
      }

      expiration {
        expired_object_delete_marker = true
      }
    }
  }

  lifecycle {
    prevent_destroy = true
  }
}
