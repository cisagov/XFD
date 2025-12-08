

resource "aws_cloudwatch_dashboard" "backendOps" {
  dashboard_name = "cyhy-${var.stage}-backend-ops"

  dashboard_body = jsonencode({
    "widgets" : [
      {
        "type" : "metric",
        "x" : 5,
        "y" : 0,
        "width" : 5,
        "height" : 6,
        "properties" : {
          "metrics" : [
            ["AWS/Lambda", "Duration", "FunctionName", "crossfeed-${var.stage}-api", "Resource", "crossfeed-${var.stage}-api", { "region" : "${var.aws_region}" }],
            [".", ".", ".", "crossfeed-frontend-${var.stage}-api", { "region" : "${var.aws_region}" }],
            ["...", "crossfeed-${var.stage}-scheduler", { "region" : "${var.aws_region}", "visible" : false }]
          ],
          "view" : "timeSeries",
          "stacked" : false,
          "region" : "${var.aws_region}",
          "period" : 300,
          "stat" : "Average",
          "title" : "API Lambdas Duration"
        }
      },
      {
        "type" : "metric",
        "x" : 5,
        "y" : 12,
        "width" : 5,
        "height" : 6,
        "properties" : {
          "view" : "timeSeries",
          "stacked" : false,
          "metrics" : [
            ["AWS/Lambda", "Duration", "FunctionName", "crossfeed-${var.stage}-scheduler"]
          ],
          "region" : "${var.aws_region}",
          "period" : 300,
          "title" : "Scheduler Lambda Duratio"
        }
      },
      {
        "type" : "metric",
        "x" : 5,
        "y" : 6,
        "width" : 5,
        "height" : 6,
        "properties" : {
          "metrics" : [
            ["AWS/Lambda", "Duration", "FunctionName", "crossfeed-${var.stage}-api", "Resource", "crossfeed-${var.stage}-api", { "region" : "${var.aws_region}", "visible" : false }],
            [".", "Errors", ".", "crossfeed-frontend-${var.stage}-api"],
            ["...", "crossfeed-${var.stage}-api"]
          ],
          "view" : "timeSeries",
          "stacked" : false,
          "region" : "${var.aws_region}",
          "period" : 300,
          "stat" : "Sum",
          "title" : "API Lambda Errors"
        }
      },
      {
        "type" : "metric",
        "x" : 5,
        "y" : 18,
        "width" : 5,
        "height" : 6,
        "properties" : {
          "metrics" : [
            ["AWS/Lambda", "Duration", "FunctionName", "crossfeed-${var.stage}-api", "Resource", "crossfeed-${var.stage}-api", { "region" : "${var.aws_region}", "visible" : false }],
            [".", "Errors", ".", "crossfeed-${var.stage}-scheduler"]
          ],
          "view" : "timeSeries",
          "stacked" : false,
          "region" : "${var.aws_region}",
          "period" : 300,
          "stat" : "Sum",
          "title" : "Scheduler Lambda Errors"
        }
      },
      {
        "type" : "metric",
        "x" : 15,
        "y" : 0,
        "width" : 5,
        "height" : 6,
        "properties" : {
          "metrics" : [
            ["ECS/ContainerInsights", "TaskCpuUtilization", "ClusterName", "${var.worker_ecs_cluster_name}", { "stat" : "Minimum", "label" : "TaskCpuUtilization Minimum", "region" : "${var.aws_region}" }],
            ["...", { "stat" : "Maximum", "label" : "TaskCpuUtilization Maximum", "region" : "${var.aws_region}" }],
            ["...", { "stat" : "Average", "label" : "TaskCpuUtilization Average", "region" : "${var.aws_region}" }]
          ],
          "period" : 60,
          "region" : "${var.aws_region}",
          "stacked" : false,
          "title" : "ECS Fargate CPU utilization",
          "view" : "timeSeries"
        }
      },
      {
        "type" : "metric",
        "x" : 15,
        "y" : 6,
        "width" : 5,
        "height" : 6,
        "properties" : {
          "metrics" : [
            ["ECS/ContainerInsights", "TaskMemoryUtilization", "ClusterName", "${var.worker_ecs_cluster_name}", { "stat" : "Minimum", "label" : "TaskMemoryUtilization Minimum", "region" : "${var.aws_region}" }],
            ["...", { "stat" : "Maximum", "label" : "TaskMemoryUtilization Maximum", "region" : "${var.aws_region}" }],
            ["...", { "stat" : "Average", "label" : "TaskMemoryUtilization Average", "region" : "${var.aws_region}" }]
          ],
          "period" : 60,
          "region" : "${var.aws_region}",
          "stacked" : false,
          "title" : "ECS Fargate Memory utilization",
          "view" : "timeSeries"
        }
      },
      {
        "type" : "metric",
        "x" : 10,
        "y" : 0,
        "width" : 5,
        "height" : 6,
        "properties" : {
          "period" : 300,
          "metrics" : [
            ["AWS/RDS", "CPUUtilization", "DBInstanceIdentifier", "${var.db_name}", { "label" : "${var.db_name}", "region" : "${var.aws_region}" }]
          ],
          "region" : "${var.aws_region}",
          "stat" : "Average",
          "title" : "Crossfeed RDS CPUUtilization",
          "yAxis" : {
            "left" : {
              "min" : 0
            }
          },
          "view" : "timeSeries",
          "stacked" : false
        }
      },
      {
        "type" : "metric",
        "x" : 10,
        "y" : 12,
        "width" : 5,
        "height" : 6,
        "properties" : {
          "period" : 300,
          "metrics" : [
            ["AWS/RDS", "DiskQueueDepth", "DBInstanceIdentifier", "${var.db_name}", { "label" : "${var.db_name}", "region" : "${var.aws_region}" }]
          ],
          "region" : "${var.aws_region}",
          "stat" : "Average",
          "title" : "Crossfeed RDS DiskQueueDepth",
          "yAxis" : {
            "left" : {
              "min" : 0
            }
          },
          "view" : "timeSeries",
          "stacked" : false
        }
      },
      {
        "type" : "metric",
        "x" : 10,
        "y" : 6,
        "width" : 5,
        "height" : 6,
        "properties" : {
          "period" : 300,
          "metrics" : [
            ["AWS/RDS", "FreeStorageSpace", "DBInstanceIdentifier", "${var.db_name}", { "label" : "${var.db_name}", "region" : "${var.aws_region}" }]
          ],
          "region" : "${var.aws_region}",
          "stat" : "Average",
          "title" : "Crossfeed RDS FreeStorageSpace",
          "yAxis" : {
            "left" : {
              "min" : 0
            }
          },
          "view" : "timeSeries",
          "stacked" : false
        }
      },
      {
        "type" : "metric",
        "x" : 20,
        "y" : 0,
        "width" : 4,
        "height" : 6,
        "properties" : {
          "metrics" : [
            ["AWS/ES", "CPUUtilization", "DomainName", "crossfeed-${var.stage}", "ClientId", "263492004256"]
          ],
          "view" : "timeSeries",
          "stacked" : false,
          "region" : "${var.aws_region}",
          "title" : "OpenSearch CPU utilization (Percent)",
          "period" : 60,
          "stat" : "Maximum",
          "yAxis" : {
            "left" : {
              "showUnits" : false
            }
          }
        }
      },
      {
        "type" : "metric",
        "x" : 20,
        "y" : 6,
        "width" : 4,
        "height" : 6,
        "properties" : {
          "metrics" : [
            ["AWS/ES", "JVMMemoryPressure", "DomainName", "crossfeed-${var.stage}", "ClientId", "263492004256"]
          ],
          "view" : "timeSeries",
          "stacked" : false,
          "region" : "${var.aws_region}",
          "title" : "OpenSearch JVM memory pressure (Percent)",
          "period" : 60,
          "stat" : "Maximum",
          "yAxis" : {
            "left" : {
              "showUnits" : false
            }
          }
        }
      },
      {
        "type" : "metric",
        "x" : 20,
        "y" : 18,
        "width" : 4,
        "height" : 6,
        "properties" : {
          "metrics" : [
            ["AWS/ES", "SearchableDocuments", "DomainName", "crossfeed-${var.stage}", "ClientId", "263492004256"]
          ],
          "view" : "timeSeries",
          "stacked" : false,
          "region" : "${var.aws_region}",
          "title" : "OpenSearch Searchable documents (Count)",
          "period" : 60,
          "stat" : "Average",
          "yAxis" : {
            "left" : {
              "showUnits" : false
            }
          }
        }
      },
      {
        "type" : "metric",
        "x" : 20,
        "y" : 12,
        "width" : 4,
        "height" : 6,
        "properties" : {
          "metrics" : [
            ["AWS/ES", "SearchLatency", "DomainName", "crossfeed-${var.stage}", "ClientId", "263492004256"]
          ],
          "view" : "timeSeries",
          "stacked" : false,
          "region" : "${var.aws_region}",
          "title" : "OpenSearch Search latency (Milliseconds)",
          "period" : 60,
          "stat" : "Average",
          "yAxis" : {
            "left" : {
              "showUnits" : false
            }
          }
        }
      },
      {
        "type" : "metric",
        "x" : 20,
        "y" : 24,
        "width" : 4,
        "height" : 6,
        "properties" : {
          "metrics" : [
            [{ "expression" : "FLOOR(m1/1024*60/PERIOD(m1))", "label" : "FreeStorageSpace", "id" : "e1" }],
            ["AWS/ES", "FreeStorageSpace", "DomainName", "crossfeed-${var.stage}", "ClientId", "263492004256", { "id" : "m1", "visible" : false }]
          ],
          "view" : "timeSeries",
          "stacked" : false,
          "region" : "${var.aws_region}",
          "title" : "OpenSearch Total free storage space (GiB)",
          "period" : 60,
          "stat" : "Sum",
          "yAxis" : {
            "left" : {
              "showUnits" : false
            }
          }
        }
      },
      {
        "type" : "metric",
        "x" : 0,
        "y" : 0,
        "width" : 5,
        "height" : 6,
        "properties" : {
          "metrics" : [
            ["AWS/ApiGateway", "Count", "ApiName", "${var.stage}-crossfeed", "Stage", "${var.stage}", { "visible" : false }],
            [".", ".", { "visible" : false }],
            [".", ".", "ApiName", "${var.stage}-crossfeed"],
            ["...", "${var.stage}-crossfeed-frontend"]
          ],
          "period" : 300,
          "stat" : "Sum",
          "region" : "${var.aws_region}",
          "view" : "timeSeries",
          "stacked" : false,
          "title" : "Api Gateway Calls"
        }
      },
      {
        "type" : "metric",
        "x" : 0,
        "y" : 6,
        "width" : 5,
        "height" : 6,
        "properties" : {
          "metrics" : [
            ["AWS/ApiGateway", "Count", "ApiName", "${var.stage}-crossfeed", "Stage", "${var.stage}", { "visible" : false, "region" : "${var.aws_region}" }],
            [".", ".", { "visible" : false, "region" : "${var.aws_region}" }],
            [".", "4XXError", "ApiName", "${var.stage}-crossfeed-frontend"],
            [".", "5XXError", ".", "."],
            [".", "4XXError", ".", "${var.stage}-crossfeed"],
            [".", "5XXError", ".", "."]
          ],
          "period" : 300,
          "stat" : "Sum",
          "region" : "${var.aws_region}",
          "view" : "timeSeries",
          "stacked" : false,
          "title" : "Api Gateway Errors"
        }
      },
      {
        "type" : "metric",
        "x" : 0,
        "y" : 12,
        "width" : 5,
        "height" : 6,
        "properties" : {
          "metrics" : [
            ["AWS/ApiGateway", "Count", "ApiName", "${var.stage}-crossfeed", "Stage", "${var.stage}", { "visible" : false, "region" : "${var.aws_region}" }],
            [".", ".", { "visible" : false, "region" : "${var.aws_region}" }],
            [".", "Latency", "ApiName", "${var.stage}-crossfeed-frontend"],
            ["...", "${var.stage}-crossfeed"]
          ],
          "period" : 300,
          "stat" : "Sum",
          "region" : "${var.aws_region}",
          "view" : "timeSeries",
          "stacked" : false,
          "title" : "Api Gateway Latency"
        }
      }
    ]
  })
}

resource "aws_cloudwatch_dashboard" "vulnScanningSync" {
  count          = var.is_dmz ? 0 : 1
  dashboard_name = "cyhy-${var.stage}-vulnScanningSync"
  dashboard_body = jsonencode({
    "widgets" : [
      {
        "type" : "metric",
        "x" : 0,
        "y" : 0,
        "width" : 13,
        "height" : 14,
        "properties" : {
          "sparkline" : false,
          "view" : "table",
          "stacked" : false,
          "region" : "${var.aws_region}",
          "title" : "VulnScanningSync Duration per Function",
          "period" : 60,
          "stat" : "Sum",
          "yAxis" : {
            "left" : {
              "showUnits" : false
            }
          },
          "metrics" : [
            ["CyHy/Worker/Functions", "DurationSeconds", "Stage", "main", "Success", "True"],
            [".", "RecordCount", ".", ".", ".", "."],
            ["...", "False"],
            [".", "DurationSeconds", ".", "fetch_vuln_scan_chunks_frozen", ".", "True"],
            [".", "RecordCount", ".", ".", ".", "."],
            [".", "DurationSeconds", ".", "fetch_port_scans_from_redshift", ".", "."],
            [".", "RecordCount", ".", ".", ".", "."],
            ["...", "False"],
            [".", "DurationSeconds", ".", "create_port_scan_summaries_bulk", ".", "True"],
            [".", "RecordCount", ".", ".", ".", "."],
            [".", "DurationSeconds", ".", "fetch_tickets_from_redshift", ".", "."],
            [".", "RecordCount", ".", ".", ".", "."]
          ]
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 13
        height = 14
        properties = {
          view    = "table"
          stacked = false
          region  = var.aws_region
          title   = "Redshift queries – Duration & RowCount"
          period  = 60
          stat    = "Average"
          yAxis   = { left = { showUnits = false } }
          # One SEARCH for DurationSeconds, one for RowCount
          metrics = [
            [
              {
                expression = "SEARCH(' {CyHy/Workers/Redshift,QueryName,Success} MetricName=\"DurationSeconds\" ', 'Average')"
                id         = "e1"
                label      = "DurationSeconds"
                region     = var.aws_region
              }
            ],
            [
              {
                expression = "SEARCH(' {CyHy/Workers/Redshift,QueryName,Success} MetricName=\"RowCount\" ', 'Sum')"
                id         = "e2"
                label      = "RowCount"
                region     = var.aws_region
              }
            ]
          ]
          table = {
            summaryColumns = ["MIN", "MAX", "AVG", "SUM"]
          }
        }
      }
    ]

  })
}
