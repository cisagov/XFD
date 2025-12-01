resource "aws_cloudwatch_metric_alarm" "api_error_rate" {
  alarm_name          = "${var.log_metric_api_error_rate}-alarm"
  alarm_description   = "API error rate for Crossfeed / CyHy backend exceeded threshold"
  namespace           = var.log_metric_namespace
  metric_name         = var.log_metric_api_error_rate
  statistic           = "Average"
  period              = 60
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = "${var.project}-${var.stage}-api"
  }

  alarm_actions = [
    aws_sns_topic.alarms.arn
    # , aws_lambda_function.ecs_remediator.arn   # Uncomment if you desire automated remediation for API errors
  ]
  ok_actions = [
    aws_sns_topic.alarms.arn
  ]

  tags = {
    Project  = var.project
    Stage    = var.stage
    Severity = var.severity_high
  }
}

resource "aws_cloudwatch_metric_alarm" "worker_ecs_cpu_high" {
  alarm_name          = "${var.project}-${var.stage}-worker-ecs-cpu-high"
  alarm_description   = "Worker ECS service CPU utilization exceeded threshold for ${var.stage}"
  namespace           = "AWS/ECS"
  metric_name         = "CPUUtilization"
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 1
  threshold           = 80
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    ClusterName = var.worker_ecs_cluster_name
    ServiceName = var.worker_ecs_task_definition_family
  }

  alarm_actions = [
    aws_sns_topic.alarms.arn,
    aws_lambda_function.ecs_remediator.arn
  ]
  ok_actions = [
    aws_sns_topic.alarms.arn
  ]

  tags = {
    Project = var.project
    Stage   = var.stage
    Severity= var.severity_high
  }
}

