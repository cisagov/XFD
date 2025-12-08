resource "aws_cloudwatch_metric_alarm" "api_error_count" {
  alarm_name          = "${var.log_metric_api_error_rate}-alarm"
  alarm_description   = "Backend API error count for ${var.stage} exceeded threshold"
  namespace           = var.log_metric_namespace
  metric_name         = var.log_metric_api_error_rate
  statistic           = "Sum"
  period              = 60
  evaluation_periods  = 2
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = "${var.project}-${var.stage}-api"
  }

  alarm_actions = [
    aws_sns_topic.alarms.arn
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
    data.aws_lambda_function.ecs_remediator.arn
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
