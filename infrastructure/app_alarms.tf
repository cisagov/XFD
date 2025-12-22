# ------------------------------------------------------------------------------
# API Performance Alarms
# ------------------------------------------------------------------------------

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

# ------------------------------------------------------------------------------
# ECS Performance Alarms
# ------------------------------------------------------------------------------

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


# ------------------------------------------------------------------------------
# Database Performance Alarms
# ------------------------------------------------------------------------------

# 1. High Database Connections (>80% utilization)
# NOTE: Threshold (332) is based on db.t3.medium (~416 max).
# If you use a different size, update this value: (Max_Connections * 0.8)
resource "aws_cloudwatch_metric_alarm" "rds_high_connections" {
  alarm_name          = "${var.project}-${var.stage}-rds-high-connections"
  alarm_description   = "RDS connection count exceeded 80% of capacity. Scan performance may degrade."
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "DatabaseConnections"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Maximum"
  threshold           = 332

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.db.id
  }

  alarm_actions = [aws_sns_topic.alarms.arn]
  ok_actions    = [aws_sns_topic.alarms.arn]
}

# 2. Low CPU Credit Balance (Burstable Instances Only)
# Alerts if credits drop below 20%, indicating the DB is about to throttle.
resource "aws_cloudwatch_metric_alarm" "rds_low_cpu_credit_balance" {
  # Logic: Only create this alarm if the instance class starts with "db.t" (e.g., db.t3.medium)
  count = length(regexall("^db.t", var.db_instance_class)) > 0 ? 1 : 0

  alarm_name          = "${var.project}-${var.stage}-rds-low-cpu-credits"
  alarm_description   = "RDS CPU Credit Balance is low (< 20%). Database performance risk."
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "3"
  metric_name         = "CPUCreditBalance"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Average"
  threshold           = 115 # Based on t3.medium (576 max credits * 0.20)

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.db.id
  }

  alarm_actions = [aws_sns_topic.alarms.arn]
  ok_actions    = [aws_sns_topic.alarms.arn]
}

# 3. Slow Query Spikes
# A. Create a Metric Filter to count logs where duration > 2s
resource "aws_cloudwatch_log_metric_filter" "slow_query_filter" {
  name           = "${var.project}-${var.stage}-slow-query-filter"
  pattern        = "\"duration: \""
  log_group_name = "/aws/rds/instance/${aws_db_instance.db.identifier}/postgresql"

  metric_transformation {
    name      = "SlowQueryCount"
    namespace = "Crossfeed/DB"
    value     = "1"
  }
}

# B. Alarm if we see > 50 slow queries in 5 minutes
resource "aws_cloudwatch_metric_alarm" "rds_slow_query_spike" {
  alarm_name          = "${var.project}-${var.stage}-rds-slow-query-spike"
  alarm_description   = "Spike in slow queries (>2s) detected: >50 occurrences in 5 mins"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "SlowQueryCount"
  namespace           = "Crossfeed/DB"
  period              = "300"
  statistic           = "Sum"
  threshold           = 50
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.alarms.arn]
  ok_actions    = [aws_sns_topic.alarms.arn]
}
