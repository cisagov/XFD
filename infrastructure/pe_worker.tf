
# P&E ECR Repository
resource "aws_ecr_repository" "pe_worker" {
  count = var.is_dmz ? 1 : 0
  name  = var.pe_worker_ecs_repository_name
  image_scanning_configuration {
    scan_on_push = true
  }
  image_tag_mutability = "MUTABLE"

  encryption_configuration {
    encryption_type = "KMS"
    kms_key         = aws_kms_key.key.arn
  }

  tags = {
    Project = var.project
    Stage   = var.stage
  }
}

# P&E ECS Cluster
resource "aws_ecs_cluster" "pe_worker" {
  count = var.is_dmz ? 1 : 0
  name  = var.pe_worker_ecs_cluster_name

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Project = var.project
    Stage   = var.stage
  }
}

resource "aws_ecs_cluster_capacity_providers" "pe_worker" {
  count              = var.is_dmz ? 1 : 0
  cluster_name       = aws_ecs_cluster.pe_worker[0].name
  capacity_providers = ["FARGATE"]
}

# P&E generic task definition
resource "aws_ecs_task_definition" "pe_worker" {
  count                    = var.is_dmz ? 1 : 0
  family                   = var.pe_worker_ecs_task_definition_family
  container_definitions    = <<EOF
[
  {
    "name": "main",
    "image": "${aws_ecr_repository.pe_worker[0].repository_url}:latest",
    "essential": true,
    "mountPoints": [],
    "portMappings": [],
%{if !var.is_dmz~}
    "volumesFrom": [
      {
        "sourceContainer": "wiz-sensor",
        "readOnly": false
      }
    ],
    "dependsOn": [
      {
        "containerName": "wiz-sensor",
        "condition": "COMPLETE"
      }
    ],
    "linuxParameters": {
      "capabilities": {
        "add": [
          "SYS_PTRACE"
        ]
      }
    },
    "entryPoint": [
      "/opt/wiz/sensor/wiz-sensor",
      "daemon",
      "--"
    ],
    "command": [
      "./worker/pe-worker-start.sh"
    ],
%{endif~}
    "logConfiguration": {
      "logDriver": "awslogs",
      "options": {
        "awslogs-group": "${var.pe_worker_ecs_log_group_name}",
        "awslogs-region": "${var.aws_region}",
        "awslogs-stream-prefix": "worker"
      }
    },
    "environment": [
      {
        "name": "DB_DIALECT",
        "value": "postgres"
      },
      {
        "name": "REPORTS_BUCKET_NAME",
        "value": "${var.reports_bucket_name}"
      },
      {
        "name": "DB_PORT",
        "value": "${var.db_port}"
      }
    ],
    "secrets": [
      {
        "name": "CENSYS_API_ID",
        "valueFrom": "${data.aws_ssm_parameter.censys_api_id.arn}"
      },
      {
        "name": "CENSYS_API_SECRET",
        "valueFrom": "${data.aws_ssm_parameter.censys_api_secret.arn}"
      },
      {
        "name": "CF_API_KEY",
        "valueFrom": "${data.aws_ssm_parameter.cf_api_key.arn}"
      },
      {
        "name": "DB_HOST",
        "valueFrom": "${aws_ssm_parameter.crossfeed_send_db_host.arn}"
      },
      {
        "name": "DB_NAME",
        "valueFrom": "${aws_ssm_parameter.crossfeed_send_db_name.arn}"
      },
      {
        "name": "DB_PASSWORD",
        "valueFrom": "${data.aws_ssm_parameter.db_password.arn}"
      },
      {
        "name": "DB_USERNAME",
        "valueFrom": "${data.aws_ssm_parameter.db_username.arn}"
      },
      {
        "name": "DNSMONITOR_CLIENT_ID",
        "valueFrom": "${data.aws_ssm_parameter.ssm_dnsmonitor_client_id.arn}"
      },
      {
        "name": "DNSMONITOR_CLIENT_SECRET",
        "valueFrom": "${data.aws_ssm_parameter.ssm_dnsmonitor_client_secret.arn}"
      },
      {
        "name": "FLARE_TENANT_ID",
        "valueFrom": "${data.aws_ssm_parameter.ssm_flare_tenant_id.arn}"
      },
      {
        "name": "ELASTICSEARCH_ENDPOINT",
        "valueFrom": "${aws_ssm_parameter.es_endpoint.arn}"
      },
      {
        "name": "INTELX_API_KEY",
        "valueFrom": "${data.aws_ssm_parameter.intelx_api_key.arn}"
      },
      {
        "name": "LG_API_KEY",
        "valueFrom": "${data.aws_ssm_parameter.lg_api_key.arn}"
      },
      {
        "name": "LG_WORKSPACE_NAME",
        "valueFrom": "${data.aws_ssm_parameter.lg_workspace_name.arn}"
      },
      {
        "name": "PE_API_KEY",
        "valueFrom": "${data.aws_ssm_parameter.pe_api_key.arn}"
      },
      {
        "name": "PE_API_URL",
        "valueFrom": "${data.aws_ssm_parameter.pe_api_url.arn}"
      },
      {
        "name": "PE_DB_NAME",
        "valueFrom": "${data.aws_ssm_parameter.pe_db_name.arn}"
      },
      {
        "name": "PE_DB_PASSWORD",
        "valueFrom": "${data.aws_ssm_parameter.pe_db_password.arn}"
      },
      {
        "name": "PE_DB_USERNAME",
        "valueFrom": "${data.aws_ssm_parameter.pe_db_username.arn}"
      },
      {
        "name": "PE_SHODAN_API_KEYS",
        "valueFrom": "${data.aws_ssm_parameter.pe_shodan_api_keys.arn}"
      },
      {
        "name": "QUALYS_PASSWORD",
        "valueFrom": "${data.aws_ssm_parameter.qualys_password.arn}"
      },
      {
        "name": "QUALYS_USERNAME",
        "valueFrom": "${data.aws_ssm_parameter.qualys_username.arn}"
      },
      {
        "name": "SHODAN_API_KEY",
        "valueFrom": "${data.aws_ssm_parameter.shodan_api_key.arn}"
      },
      {
        "name": "SHODAN_ORG_EXCEPTION",
        "valueFrom": "${data.aws_ssm_parameter.ssm_shodan_org_exception.arn}"
      },
      {
        "name": "WHOIS_XML_KEY",
        "valueFrom": "${data.aws_ssm_parameter.whoisxml_api_key.arn}"
      },
%{if !var.is_dmz~}
      {
        "name": "WIZ_API_CLIENT_ID",
        "valueFrom": "${data.aws_ssm_parameter.wiz_service_account_secret_arn[0].value}:WIZ_API_CLIENT_ID::"
      },
      {
        "name": "WIZ_API_CLIENT_SECRET",
        "valueFrom": "${data.aws_ssm_parameter.wiz_service_account_secret_arn[0].value}:WIZ_API_CLIENT_SECRET::"
      },
%{endif~}
      {
        "name": "WORKER_SIGNATURE_PRIVATE_KEY",
        "valueFrom": "${data.aws_ssm_parameter.worker_signature_private_key.arn}"
      },
      {
        "name": "WORKER_SIGNATURE_PUBLIC_KEY",
        "valueFrom": "${data.aws_ssm_parameter.worker_signature_public_key.arn}"
      },
      {
        "name": "XPANSE_API_KEY",
        "valueFrom": "${data.aws_ssm_parameter.xpanse_api_key.arn}"
      },
      {
        "name": "XPANSE_AUTH_ID",
        "valueFrom": "${data.aws_ssm_parameter.xpanse_auth_id.arn}"
      }
    ]
  }%{if !var.is_dmz},
  {
    "name": "wiz-sensor",
    "image": "wizfedramp.azurecr.us/sensor-serverless:v1",
    "repositoryCredentials": {
      "credentialsParameter": "${data.aws_ssm_parameter.wiz_registry_secret_arn[0].value}"
    },
    "cpu": 0,
    "portMappings": [],
    "essential": false,
    "environment": [],
    "environmentFiles": [],
    "mountPoints": [],
    "volumesFrom": [],
    "systemControls": []
  }
%{endif}
]
EOF
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  execution_role_arn       = aws_iam_role.worker_task_execution_role.arn
  task_role_arn            = aws_iam_role.worker_task_role.arn

  # CPU and memory values: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-cpu-memory-error.html

  cpu    = 2048
  memory = 16384
  tags = {
    Project = var.project
    Stage   = var.stage
  }
}

# Create the  log group
resource "aws_cloudwatch_log_group" "pe_worker" {
  count             = var.is_dmz ? 1 : 0
  name              = var.pe_worker_ecs_log_group_name
  retention_in_days = 3653
  kms_key_id        = aws_kms_key.key.arn
  tags = {
    Project = var.project
    Stage   = var.stage
    Owner   = "Crossfeed managed resource"
  }
}

# Attach to IAM users/groups in the AWS console (run_scans.sh, watch_queues.sh).
resource "aws_iam_policy" "pe_scan_operator" {
  count       = var.is_dmz ? 1 : 0
  name        = "crossfeed-${var.stage}-pe-scan-operator"
  description = "Invoke PE scans, monitor queues/workers, and purge PE scan queues for ${var.stage}"

  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "InvokePeScanController",
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction",
        "lambda:GetFunction"
      ],
      "Resource": "arn:${var.aws_partition}:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:crossfeed-${var.stage}-peScanController"
    },
    {
      "Sid": "InvokePeReportController",
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction",
        "lambda:GetFunction"
      ],
      "Resource": "arn:${var.aws_partition}:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:crossfeed-${var.stage}-peReportController"
    },
    {
      "Sid": "ReadPeWorkerLogs",
      "Effect": "Allow",
      "Action": [
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams",
        "logs:FilterLogEvents",
        "logs:GetLogEvents"
      ],
      "Resource": "arn:${var.aws_partition}:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:${var.pe_worker_ecs_log_group_name}:*"
    },
    {
      "Sid": "DecryptPeWorkerLogs",
      "Effect": "Allow",
      "Action": [
        "kms:Decrypt",
        "kms:DescribeKey"
      ],
      "Resource": "${aws_kms_key.key.arn}"
    },
    {
      "Sid": "DescribePeWorkerCluster",
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeClusters"
      ],
      "Resource": "arn:${var.aws_partition}:ecs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:cluster/${var.pe_worker_ecs_cluster_name}"
    },
    {
      "Sid": "MonitorPeWorkerTasks",
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeTasks",
        "ecs:ListTasks"
      ],
      "Resource": "*",
      "Condition": {
        "ArnEquals": {
          "ecs:cluster": "arn:${var.aws_partition}:ecs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:cluster/${var.pe_worker_ecs_cluster_name}"
        }
      }
    },
    {
      "Sid": "ManagePeScanQueues",
      "Effect": "Allow",
      "Action": [
        "sqs:GetQueueAttributes",
        "sqs:GetQueueUrl",
        "sqs:ListQueues",
        "sqs:PurgeQueue"
      ],
      "Resource": "arn:${var.aws_partition}:sqs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:${var.stage == "integration" ? "pe-integration" : "pe-staging"}-*"
    }
  ]
}
EOF

  tags = {
    Project = var.project
    Stage   = var.stage
    Owner   = "Crossfeed managed resource"
  }
}
