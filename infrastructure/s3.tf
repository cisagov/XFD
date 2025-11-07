
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

resource "aws_s3_bucket_ownership_controls" "django_env_bucket" {
  bucket = aws_s3_bucket.django_env_bucket.id
  rule {
    object_ownership = "ObjectWriter"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "django_env_bucket" {
  bucket = aws_s3_bucket.django_env_bucket.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
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
