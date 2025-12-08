# Alarm for API: integration-crossfeed
resource "aws_cloudwatch_metric_alarm" "integration_crossfeed_5xx" {
  count               = var.is_dmz ? 0 : 1
  alarm_name          = "${var.project}-${var.stage}-api-integration-crossfeed-5xx-error"
  alarm_description   = "5XX error count for API Gateway “integration-crossfeed” (${var.stage})"
  namespace           = "AWS/ApiGateway"
  metric_name         = "5XXError"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 3
  threshold           = 2
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    ApiName = "integration-crossfeed"
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

# Alarm for API: integration-crossfeed-frontend
resource "aws_cloudwatch_metric_alarm" "integration_crossfeed_frontend_5xx" {
  count               = var.is_dmz ? 0 : 1
  alarm_name          = "${var.project}-${var.stage}-api-integration-crossfeed-frontend-5xx-error"
  alarm_description   = "5XX error count for API Gateway “integration-crossfeed-frontend” (${var.stage})"
  namespace           = "AWS/ApiGateway"
  metric_name         = "5XXError"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 3
  threshold           = 2
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    ApiName = "integration-crossfeed-frontend"
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

# Alarm for API: staging-cd-crossfeed
resource "aws_cloudwatch_metric_alarm" "staging_cd_crossfeed_5xx" {
  count               = var.is_dmz ? 0 : 1
  alarm_name          = "${var.project}-${var.stage}-api-staging-cd-crossfeed-5xx-error"
  alarm_description   = "5XX error count for API Gateway “staging-cd-crossfeed” (${var.stage})"
  namespace           = "AWS/ApiGateway"
  metric_name         = "5XXError"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 3
  threshold           = 2
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    ApiName = "staging-cd-crossfeed"
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

# Alarm for API: staging-cd-crossfeed-frontend
resource "aws_cloudwatch_metric_alarm" "staging_cd_crossfeed_frontend_5xx" {
  count               = var.is_dmz ? 0 : 1
  alarm_name          = "${var.project}-${var.stage}-api-staging-cd-crossfeed-frontend-5xx-error"
  alarm_description   = "5XX error count for API Gateway “staging-cd-crossfeed-frontend” (${var.stage})"
  namespace           = "AWS/ApiGateway"
  metric_name         = "5XXError"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 3
  threshold           = 2
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    ApiName = "staging-cd-crossfeed-frontend"
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

#The following are for AWS Gov cloud

# Alarm for API: prod-crossfeed
resource "aws_cloudwatch_metric_alarm" "prod_crossfeed_5xx_error" {
  count               = var.is_dmz ? 0 : 1
  alarm_name          = "${var.project}-${var.stage}-api-prod-crossfeed-5xx-error"
  alarm_description   = "5XX error count for API Gateway prod-crossfeed (${var.stage})"
  namespace           = "AWS/ApiGateway"
  metric_name         = "5XXError"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 3
  threshold           = 2
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    ApiName = "prod-crossfeed"
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

# Alarm for API: prod-crossfeed-frontend
resource "aws_cloudwatch_metric_alarm" "prod_crossfeed_frontend_5xx_error" {
  count               = var.is_dmz ? 0 : 1
  alarm_name          = "${var.project}-${var.stage}-api-prod-crossfeed-frontend-5xx-error"
  alarm_description   = "5XX error count for API Gateway prod-crossfeed-frontend (${var.stage})"
  namespace           = "AWS/ApiGateway"
  metric_name         = "5XXError"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 3
  threshold           = 2
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    ApiName = "prod-crossfeed-frontend"
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

# Alarm for API: staging-crossfeed
resource "aws_cloudwatch_metric_alarm" "staging_crossfeed_5xx_error" {
  count               = var.is_dmz ? 0 : 1
  alarm_name          = "${var.project}-${var.stage}-api-staging-crossfeed-5xx-error"
  alarm_description   = "5XX error count for API Gateway staging-crossfeed (${var.stage})"
  namespace           = "AWS/ApiGateway"
  metric_name         = "5XXError"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 3
  threshold           = 2
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    ApiName = "staging-crossfeed"
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

# Alarm for API: staging-crossfeed-frontend
resource "aws_cloudwatch_metric_alarm" "staging_crossfeed_frontend_5xx_error" {
  count               = var.is_dmz ? 0 : 1
  alarm_name          = "${var.project}-${var.stage}-api-staging-crossfeed-frontend-5xx-error"
  alarm_description   = "5XX error count for API Gateway staging-crossfeed-frontend (${var.stage})"
  namespace           = "AWS/ApiGateway"
  metric_name         = "5XXError"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 3
  threshold           = 2
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    ApiName = "staging-crossfeed-frontend"
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
