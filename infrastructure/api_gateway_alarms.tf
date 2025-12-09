resource "aws_cloudwatch_metric_alarm" "frontend_api_crossfeed_5xx_error" {
  alarm_name          = "${var.project}-${var.stage}-frontend-api-crossfeed-5xx-error"                   //CHANGED
  alarm_description   = "5XX error count for API Gateway ${var.stage}-crossfeed-frontend (${var.stage})" //CHANGED
  namespace           = "AWS/ApiGateway"
  metric_name         = "5XXError"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 3
  threshold           = 2
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    ApiName = "${var.stage}-crossfeed-frontend" // CHANGED
    Stage   = var.stage
  }

  alarm_actions = [aws_sns_topic.alarms.arn]
  ok_actions    = [aws_sns_topic.alarms.arn]

  tags = {
    Project  = var.project
    Stage    = var.stage
    Severity = var.severity_medium
  }
}

resource "aws_cloudwatch_metric_alarm" "backend_api_crossfeed_5xx_error" {
  alarm_name          = "${var.project}-${var.stage}-api-crossfeed-5xx-error"                   //CHANGED
  alarm_description   = "5XX error count for API Gateway ${var.stage}-crossfeed (${var.stage})" //CHANGED
  namespace           = "AWS/ApiGateway"
  metric_name         = "5XXError"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 3
  threshold           = 2
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    ApiName = "${var.stage}-crossfeed" // CHANGED
    Stage   = var.stage
  }

  alarm_actions = [aws_sns_topic.alarms.arn]
  ok_actions    = [aws_sns_topic.alarms.arn]

  tags = {
    Project  = var.project
    Stage    = var.stage
    Severity = var.severity_medium
  }
}
