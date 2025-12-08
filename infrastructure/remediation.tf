data "aws_lambda_function" "ecs_remediator" {
  function_name = "cyhy-${var.stage}-ecs-remediator"
}

# --- EventBridge rules + targets for API-gateway 5xx alarms ---

# 1. integration-crossfeed
resource "aws_cloudwatch_event_rule" "integration_crossfeed_5xx_alarm_rule" {
  count       = var.is_dmz ? 0 : 1 # Added to match Alarm existence
  name        = "cyhy-${var.stage}-api-integration-crossfeed-5xx-alarm-rule"
  description = "Triggers ECS remediation when integration-crossfeed API 5XX alarm enters ALARM"
  event_pattern = jsonencode({
    "source" : ["aws.cloudwatch"],
    "detail-type" : ["CloudWatch Alarm State Change"],
    "resources" : [aws_cloudwatch_metric_alarm.integration_crossfeed_5xx[0].arn], # Added [0]
    "detail" : { "state" : { "value" : ["ALARM"] } }
  })
}

resource "aws_cloudwatch_event_target" "integration_crossfeed_5xx_alarm_target" {
  count     = var.is_dmz ? 0 : 1
  rule      = aws_cloudwatch_event_rule.integration_crossfeed_5xx_alarm_rule[0].name # Added [0]
  target_id = "ecs-remediator-integration-crossfeed"
  arn       = data.aws_lambda_function.ecs_remediator.arn # Changed to reference the 'data' source correctly
}

resource "aws_lambda_permission" "allow_eventbridge_invoke_integration_crossfeed" {
  count         = var.is_dmz ? 0 : 1
  statement_id  = "AllowInvokeEcsRemediatorIntegrationCrossfeed"
  action        = "lambda:InvokeFunction"
  function_name = data.aws_lambda_function.ecs_remediator.function_name # Changed to 'data' reference
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.integration_crossfeed_5xx_alarm_rule[0].arn # Added [0]
}

# 2. integration-crossfeed-frontend
resource "aws_cloudwatch_event_rule" "integration_crossfeed_frontend_5xx_alarm_rule" {
  count       = var.is_dmz ? 0 : 1
  name        = "cyhy-${var.stage}-api-integration-crossfeed-frontend-5xx-alarm-rule"
  description = "Triggers ECS remediation when integration-crossfeed-frontend API 5XX alarm enters ALARM"
  event_pattern = jsonencode({
    "source" : ["aws.cloudwatch"],
    "detail-type" : ["CloudWatch Alarm State Change"],
    "resources" : [aws_cloudwatch_metric_alarm.integration_crossfeed_frontend_5xx[0].arn], # Added [0]
    "detail" : { "state" : { "value" : ["ALARM"] } }
  })
}

resource "aws_cloudwatch_event_target" "integration_crossfeed_frontend_5xx_alarm_target" {
  count     = var.is_dmz ? 0 : 1
  rule      = aws_cloudwatch_event_rule.integration_crossfeed_frontend_5xx_alarm_rule[0].name
  target_id = "ecs-remediator-integration-crossfeed-frontend"
  arn       = data.aws_lambda_function.ecs_remediator.arn
}

resource "aws_lambda_permission" "allow_eventbridge_invoke_integration_frontend" {
  count         = var.is_dmz ? 0 : 1
  statement_id  = "AllowInvokeEcsRemediatorIntegrationFrontend"
  action        = "lambda:InvokeFunction"
  function_name = data.aws_lambda_function.ecs_remediator.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.integration_crossfeed_frontend_5xx_alarm_rule[0].arn
}

# 3. staging-cd-crossfeed
resource "aws_cloudwatch_event_rule" "staging_cd_crossfeed_5xx_alarm_rule" {
  count       = var.is_dmz ? 0 : 1
  name        = "cyhy-${var.stage}-api-staging-cd-crossfeed-5xx-alarm-rule"
  description = "Triggers ECS remediation when staging-cd-crossfeed API 5XX alarm enters ALARM"
  event_pattern = jsonencode({
    "source" : ["aws.cloudwatch"],
    "detail-type" : ["CloudWatch Alarm State Change"],
    "resources" : [aws_cloudwatch_metric_alarm.staging_cd_crossfeed_5xx[0].arn], # Added [0]
    "detail" : { "state" : { "value" : ["ALARM"] } }
  })
}

resource "aws_cloudwatch_event_target" "staging_cd_crossfeed_5xx_alarm_target" {
  count     = var.is_dmz ? 0 : 1
  rule      = aws_cloudwatch_event_rule.staging_cd_crossfeed_5xx_alarm_rule[0].name
  target_id = "ecs-remediator-staging-cd-crossfeed"
  arn       = data.aws_lambda_function.ecs_remediator.arn
}

resource "aws_lambda_permission" "allow_eventbridge_invoke_staging_cd_crossfeed" {
  count         = var.is_dmz ? 0 : 1
  statement_id  = "AllowInvokeEcsRemediatorStagingCdCrossfeed"
  action        = "lambda:InvokeFunction"
  function_name = data.aws_lambda_function.ecs_remediator.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.staging_cd_crossfeed_5xx_alarm_rule[0].arn
}

# 4. staging-cd-crossfeed-frontend
resource "aws_cloudwatch_event_rule" "staging_cd_crossfeed_frontend_5xx_alarm_rule" {
  count       = var.is_dmz ? 0 : 1
  name        = "cyhy-${var.stage}-api-staging-cd-crossfeed-frontend-5xx-alarm-rule"
  description = "Triggers ECS remediation when staging-cd-crossfeed-frontend API 5XX alarm enters ALARM"
  event_pattern = jsonencode({
    "source" : ["aws.cloudwatch"],
    "detail-type" : ["CloudWatch Alarm State Change"],
    "resources" : [aws_cloudwatch_metric_alarm.staging_cd_crossfeed_frontend_5xx[0].arn], # Added [0]
    "detail" : { "state" : { "value" : ["ALARM"] } }
  })
}

resource "aws_cloudwatch_event_target" "staging_cd_crossfeed_frontend_5xx_alarm_target" {
  count     = var.is_dmz ? 0 : 1
  rule      = aws_cloudwatch_event_rule.staging_cd_crossfeed_frontend_5xx_alarm_rule[0].name
  target_id = "ecs-remediator-staging-cd-crossfeed-frontend"
  arn       = data.aws_lambda_function.ecs_remediator.arn
}

resource "aws_lambda_permission" "allow_eventbridge_invoke_staging_cd_frontend" {
  count         = var.is_dmz ? 0 : 1
  statement_id  = "AllowInvokeEcsRemediatorStagingCdFrontend"
  action        = "lambda:InvokeFunction"
  function_name = data.aws_lambda_function.ecs_remediator.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.staging_cd_crossfeed_frontend_5xx_alarm_rule[0].arn
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
  arn       = data.aws_lambda_function.ecs_remediator.arn
}

resource "aws_lambda_permission" "allow_eventbridge_invoke_ecs_remediator_worker" {
  statement_id  = "AllowEventBridgeInvokeEcsRemediatorWorker"
  action        = "lambda:InvokeFunction"
  function_name = data.aws_lambda_function.ecs_remediator.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.worker_ecs_cpu_high_alarm_rule.arn
}
