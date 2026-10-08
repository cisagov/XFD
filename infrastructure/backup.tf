# AWS Backup for the OpenCTI EC2 instance's single root EBS volume, which hosts all Docker data
# (Elasticsearch/esdata -- the OpenCTI knowledge graph, MinIO/s3data -- uploaded files, and
# XTM One's Postgres/pgsqlxtmonedata, plus Redis/RabbitMQ working state).
#
# EBS snapshots taken this way are point-in-time and crash-consistent for the whole volume --
# equivalent to what the disk would look like after a hard power loss, not a clean shutdown.
# Elasticsearch, MinIO, and Postgres all recover from that via their own translog/journal/WAL
# mechanisms, so this is a reasonable default without any pre-snapshot quiescing step. If
# zero-inconsistency-risk backups are wanted later, bracket the backup window with an SSM
# Automation document running `docker compose stop` / `docker compose start` on the instance --
# not implemented here.

resource "aws_backup_vault" "open_cti" {
  count = var.create_open_cti_instance ? 1 : 0
  name  = "crossfeed-open-cti-${var.stage}"

  tags = {
    Project = var.project
    Stage   = var.stage
    Owner   = "Crossfeed managed resource"
  }
}

resource "aws_iam_role" "open_cti_backup" {
  count = var.create_open_cti_instance ? 1 : 0
  name  = "crossfeed-open-cti-backup-${var.stage}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect    = "Allow",
      Principal = { Service = "backup.amazonaws.com" },
      Action    = "sts:AssumeRole"
    }]
  })

  tags = {
    Project = var.project
    Stage   = var.stage
    Owner   = "Crossfeed managed resource"
  }
}

resource "aws_iam_role_policy_attachment" "open_cti_backup" {
  count      = var.create_open_cti_instance ? 1 : 0
  role       = aws_iam_role.open_cti_backup[0].name
  policy_arn = "arn:${var.aws_partition}:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForBackup"
}

resource "aws_backup_plan" "open_cti" {
  count = var.create_open_cti_instance ? 1 : 0
  name  = "crossfeed-open-cti-${var.stage}"

  rule {
    rule_name         = "daily"
    target_vault_name = aws_backup_vault.open_cti[0].name
    # Recommendation, not a hard requirement -- adjust to your actual RPO/RTO needs.
    schedule = "cron(0 7 * * ? *)"

    lifecycle {
      delete_after = 35
    }
  }

  tags = {
    Project = var.project
    Stage   = var.stage
    Owner   = "Crossfeed managed resource"
  }
}

resource "aws_backup_selection" "open_cti" {
  count        = var.create_open_cti_instance ? 1 : 0
  name         = "open-cti-instance"
  plan_id      = aws_backup_plan.open_cti[0].id
  iam_role_arn = aws_iam_role.open_cti_backup[0].arn
  resources    = [aws_instance.open_cti[0].arn]
}
