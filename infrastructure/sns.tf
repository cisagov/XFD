resource "aws_sns_topic" "alarms" {
  name              = var.sns_topic_alarms
  kms_master_key_id = "alias/aws/sns"

  tags = {
    Project = var.project
    Stage   = var.stage
  }
}

resource "aws_ssm_parameter" "alarms_topic_arn" {
  name        = "/crossfeed/${var.stage}/alarms_topic_arn"
  description = "Alarms SNS Topic ARN for Serverless resolution"
  type        = "String"
  value       = aws_sns_topic.alarms.arn
  overwrite   = true

  tags = {
    Project = var.project
    Stage   = var.stage
    Managed = "Terraform"
  }
}
