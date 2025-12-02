resource "aws_lambda_function" "ecs_remediator" {
  function_name = "cyhy-${var.stage}-ecs-remediator"
  role          = aws_iam_role.remediation_lambda_role.arn
  handler       = "ecs_remediator.lambda_handler"
  runtime       = "python3.12"

  filename         = "${path.module}/lambda/ecs_remediator.zip"
  source_code_hash = filebase64sha256("${path.module}/lambda/ecs_remediator.zip")

  timeout = 60

  environment {
    variables = {
      CUSTOM_METRIC_NAMESPACE = "Crossfeed/Remediation"
      ECS_CLUSTER_NAME = var.worker_ecs_cluster_name
      ECS_SERVICE_NAME = var.worker_ecs_task_definition_family
      STAGE            = var.stage
      PROJECT          = var.project
      SNS_ALARMS_TOPIC_ARN    = aws_sns_topic.alarms.arn
    }
  }

  tags = {
    Project = var.project
    Stage   = var.stage
  }
}

resource "aws_cloudwatch_event_rule" "api_error_rate_alarm_rule" {
  name        = "cyhy-${var.stage}-api-error-rate-alarm-rule"
  description = "Triggers ECS remediation Lambda when API error rate alarm is ALARM."

  event_pattern = jsonencode({
    "source"      : ["aws.cloudwatch"],
    "detail-type" : ["CloudWatch Alarm State Change"],
    "detail"      : {
      "state" : {
        "value" : ["ALARM"]
      },
      "alarmName" : [
        aws_cloudwatch_metric_alarm.api_error_rate.alarm_name
      ]
    }
  })
}

resource "aws_cloudwatch_event_target" "api_error_rate_alarm_target" {
  rule      = aws_cloudwatch_event_rule.api_error_rate_alarm_rule.name
  target_id = "ecs-remediator"
  arn       = aws_lambda_function.ecs_remediator.arn
}

resource "aws_lambda_permission" "allow_eventbridge_invoke_ecs_remediator" {
  statement_id  = "AllowEventBridgeInvokeEcsRemediator"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ecs_remediator.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.api_error_rate_alarm_rule.arn
}

resource "aws_iam_role" "remediation_lambda_role" {
  name = "cyhy-${var.stage}-remediation-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action    = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "remediation_lambda_inline_policy" {
  name = "remediation-lambda-policy"
  role = aws_iam_role.remediation_lambda_role.id

  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = [
          "ecs:DescribeServices",
          "ecs:UpdateService"
        ]
        Resource = [
          "arn:${var.aws_partition}:ecs:${var.aws_region}:${var.aws_account_id}:service/${var.worker_ecs_cluster_name}/${var.worker_ecs_task_definition_family}"
        ]
      },
      {
        Effect   = "Allow"
        Action   = [
          "iam:PassRole"
        ]
        Resource = var.worker_ecs_task_execution_role_arn
      },
      {
        Effect   = "Allow"
        Action   = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:${var.aws_partition}:logs:${var.aws_region}:${var.aws_account_id}:log-group:/aws/lambda/cyhy-${var.stage}-ecs-remediator*"
      },
      {
        "Effect":   "Allow",
        "Action":   ["sns:Publish"],
        "Resource": [ aws_sns_topic.alarms.arn ]
      }
      ,
      {
        "Effect": "Allow",
        "Action": ["cloudwatch:PutMetricData"],
        "Resource": ["*"]  // or more narrowly scoped if you want
      }
    ]
  })
}

resource "aws_cloudwatch_event_rule" "worker_ecs_cpu_high_alarm_rule" {
  name        = "cyhy-${var.stage}-worker-ecs-cpu-high-alarm-rule"
  description = "Triggers ECS remediation Lambda when worker ECS CPU high alarm enters ALARM."

  event_pattern = jsonencode({
    "source"      : ["aws.cloudwatch"],
    "detail-type" : ["CloudWatch Alarm State Change"],
    "detail"      : {
      "state"    : { "value": ["ALARM"] },
      "alarmName": [ aws_cloudwatch_metric_alarm.worker_ecs_cpu_high.alarm_name ]
    }
  })
}

resource "aws_cloudwatch_event_target" "worker_ecs_cpu_high_alarm_target" {
  rule      = aws_cloudwatch_event_rule.worker_ecs_cpu_high_alarm_rule.name
  target_id = "ecs-remediator-worker"
  arn       = aws_lambda_function.ecs_remediator.arn
}

resource "aws_lambda_permission" "allow_eventbridge_invoke_ecs_remediator_worker" {
  statement_id  = "AllowEventBridgeInvokeEcsRemediatorWorker"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ecs_remediator.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.worker_ecs_cpu_high_alarm_rule.arn
}
