resource "aws_lambda_function" "ecs_remediator" {
  function_name = "cyhy-${var.stage}-ecs-remediator"
  role          = var.remediation_lambda_role_arn
  handler       = "ecs_remediator.lambda_handler"
  runtime       = "python3.12"

  filename         = "${path.module}/lambda/ecs_remediator.zip"
  source_code_hash = filebase64sha256("${path.module}/lambda/ecs_remediator.zip")

  timeout = 60

  environment {
    variables = {
      ECS_CLUSTER_NAME = var.worker_ecs_cluster_name
      ECS_SERVICE_NAME = var.worker_ecs_task_definition_family
      STAGE            = var.stage
      PROJECT          = var.project
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
