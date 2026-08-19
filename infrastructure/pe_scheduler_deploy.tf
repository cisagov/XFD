# Purpose: Add permissions to the IAM Role that controlls the scheduler in AWS
resource "aws_iam_policy" "scheduler_deploy_policy" {
  count       = var.is_dmz ? 1 : 0
  name        = "crossfeed-${var.stage}-scheduler-deploy-policy"
  description = "Allow deployment of EventBridge Scheduler schedules"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "scheduler:CreateSchedule",
          "scheduler:DeleteSchedule",
          "scheduler:GetSchedule",
          "scheduler:UpdateSchedule",
        ]
        Resource = "arn:${var.aws_partition}:scheduler:${var.aws_region}:${data.aws_caller_identity.current.account_id}:schedule/default/pe-*"
      }
    ]
  })
}

resource "aws_iam_user_policy_attachment" "scheduler_deploy_user_attach" {
  count      = var.is_dmz ? 1 : 0
  user       = "crossfeed-deploy-staging"
  policy_arn = aws_iam_policy.scheduler_deploy_policy[0].arn
}
