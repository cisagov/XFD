data "aws_lambda_function" "ecs_remediator" {
  function_name = "crossfeed-${var.stage}-ecsRemediator"
}

data "aws_ssm_parameter" "ecs_remediator_arn" {
  name = "/crossfeed/${var.stage}/ECS_REMEDATIOR_ARN"
}

# --- EventBridge rules + targets for API-gateway 5xx alarms ---
# ------------------------------------------------------------------------------
# 1. Backend API Remediation (Crossfeed)
#    Consolidates: integration-crossfeed, staging-cd-crossfeed, prod-crossfeed
# ------------------------------------------------------------------------------

resource "aws_cloudwatch_event_rule" "backend_api_crossfeed_5xx_alarm_rule" {
  name        = "cyhy-${var.stage}-api-crossfeed-5xx-alarm-rule"
  description = "Triggers ECS remediation when ${var.stage}-crossfeed API 5XX alarm enters ALARM"

  event_pattern = jsonencode({
    "source" : ["aws.cloudwatch"],
    "detail-type" : ["CloudWatch Alarm State Change"],
    # References the new dynamic backend alarm
    "resources" : [aws_cloudwatch_metric_alarm.backend_api_crossfeed_5xx_error.arn],
    "detail" : { "state" : { "value" : ["ALARM"] } }
  })

}

resource "aws_cloudwatch_event_target" "backend_api_crossfeed_5xx_alarm_target" {
  rule = aws_cloudwatch_event_rule.backend_api_crossfeed_5xx_alarm_rule.name
  # Dynamically names the target ID based on stage
  target_id = "ecs-remediator-${var.stage}-crossfeed"
  arn       = data.aws_ssm_parameter.ecs_remediator_arn.name
}

resource "aws_lambda_permission" "allow_eventbridge_invoke_backend_api_crossfeed" {
  statement_id  = "AllowInvokeEcsRemediatorBackendApiCrossfeed"
  action        = "lambda:InvokeFunction"
  function_name = data.aws_lambda_function.ecs_remediator.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.backend_api_crossfeed_5xx_alarm_rule.arn
}

# ------------------------------------------------------------------------------
# 2. Frontend API Remediation (Crossfeed Frontend)
#    Consolidates: integration-crossfeed-frontend, staging-cd-crossfeed-frontend, prod-crossfeed-frontend
# ------------------------------------------------------------------------------

resource "aws_cloudwatch_event_rule" "frontend_api_crossfeed_5xx_alarm_rule" {
  name        = "cyhy-${var.stage}-api-crossfeed-frontend-5xx-alarm-rule"
  description = "Triggers ECS remediation when ${var.stage}-crossfeed-frontend API 5XX alarm enters ALARM"

  event_pattern = jsonencode({
    "source" : ["aws.cloudwatch"],
    "detail-type" : ["CloudWatch Alarm State Change"],
    # References the new dynamic frontend alarm
    "resources" : [aws_cloudwatch_metric_alarm.frontend_api_crossfeed_5xx_error.arn],
    "detail" : { "state" : { "value" : ["ALARM"] } }
  })
}

resource "aws_cloudwatch_event_target" "frontend_api_crossfeed_5xx_alarm_target" {
  rule = aws_cloudwatch_event_rule.frontend_api_crossfeed_5xx_alarm_rule.name
  # Dynamically names the target ID based on stage
  target_id = "ecs-remediator-${var.stage}-crossfeed-frontend"
  arn       = data.aws_ssm_parameter.ecs_remediator_arn.name
}

resource "aws_lambda_permission" "allow_eventbridge_invoke_frontend_api_crossfeed" {
  statement_id  = "AllowInvokeEcsRemediatorFrontendApiCrossfeed"
  action        = "lambda:InvokeFunction"
  function_name = data.aws_lambda_function.ecs_remediator.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.frontend_api_crossfeed_5xx_alarm_rule.arn
}

# --- Existing ECS CPU alarm handling rule ---
# (NOTE: If 'worker_ecs_cpu_high' in app_alarms.tf ALSO has a count, you must fix this block too.
# Based on your files, it does NOT have a count, so this block is likely fine as is.)
resource "aws_cloudwatch_event_rule" "worker_ecs_cpu_high_alarm_rule" {
  name        = "cyhy-${var.stage}-worker-ecs-cpu-high-alarm-rule"
  description = "Triggers ECS remediation Lambda when worker ECS CPU high alarm enters ALARM."
  event_pattern = jsonencode({
    "source" : ["aws.cloudwatch"],
    "detail-type" : ["CloudWatch Alarm State Change"],
    "detail" : {
      "state" : { "value" : ["ALARM"] },
      "alarmName" : [aws_cloudwatch_metric_alarm.worker_ecs_cpu_high.alarm_name]
    }
  })
}

resource "aws_cloudwatch_event_target" "worker_ecs_cpu_high_alarm_target" {
  rule      = aws_cloudwatch_event_rule.worker_ecs_cpu_high_alarm_rule.name
  target_id = "ecs-remediator-worker"
  arn       = data.aws_ssm_parameter.ecs_remediator_arn.name
}

resource "aws_lambda_permission" "allow_eventbridge_invoke_ecs_remediator_worker" {
  statement_id  = "AllowEventBridgeInvokeEcsRemediatorWorker"
  action        = "lambda:InvokeFunction"
  function_name = data.aws_lambda_function.ecs_remediator.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.worker_ecs_cpu_high_alarm_rule.arn
}
