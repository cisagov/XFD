resource "aws_cloudwatch_metric_alarm" "api_error_rate" {
  alarm_name          = "${var.log_metric_api_error_rate}-alarm"
  alarm_description   = "API error rate for Crossfeed / CyHy backend exceeded threshold"
  metric_name         = var.log_metric_api_error_rate
  namespace           = var.log_metric_namespace
  alarm_actions       = [aws_sns_topic.alarms.arn]
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  period              = 60
  threshold           = 1
  statistic           = "Average"
  treat_missing_data  = "notBreaching"

  tags = {
    Project  = var.project
    Stage    = var.stage
    Severity = var.severity_high
  }
}
