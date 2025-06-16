resource "aws_iam_role" "playwright_worker_task_execution_role" {
  name = "${var.crossfeed_playwright}-task-execution-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
        Effect = "Allow"
      }
    ]
  })
}

resource "aws_iam_role" "playwright_worker_task_role" {
  name = "${var.crossfeed_playwright}-worker-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
        Effect = "Allow"
      }
    ]
  })
}

resource "aws_iam_role_policy" "playwright_ecs_task_policy" {
  name = "${var.crossfeed_playwright}-ecs-task-policy"
  role = aws_iam_role.playwright_worker_task_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = ["s3:ListBucket", "s3:GetObject", "s3:PutObject"]
        Effect = "Allow"
        Resource = [
          "arn:aws:s3:::${var.automated_test_reports_bucket_name}",  # ListBucket on the bucket itself
          "arn:aws:s3:::${var.automated_test_reports_bucket_name}/*" # GetObject and PutObject on all objects within the bucket
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "playwright_ecs_execution_policy" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
  role       = aws_iam_role.playwright_worker_task_execution_role.id
}

resource "aws_ecs_task_definition" "playwright_worker" {
  family                   = var.playwright_worker_ecs_task_definition_family
  container_definitions    = <<EOF
[
  {
    "name": "main",
    "image": "public.ecr.aws/sphmedia/sphmedia/microsoft-playwright:v1.50.1-jammy",
    "essential": true,
    "mountPoints": [],
    "portMappings": [],
    "volumesFrom": [],
    "logConfiguration": {
      "logDriver": "awslogs",
      "options": {
        "awslogs-group": "${var.worker_ecs_log_group_name}",
        "awslogs-region": "${var.aws_region}",
        "awslogs-stream-prefix": "playwright"
      }
    },
    "environment": [
      {
        "name": "BROWSER_TYPE",
        "value": "chromium"
      },
      {
        "name": "TEST_URL",
        "value": "${var.frontend_domain}"
      }
    ],
    "command": [
      "-c",
      "echo 'Installing Playwright...'; npx playwright install --with-deps; echo 'Cloning Playwright tests from GitHub...'; git clone https://github.com/cisagov/xfd.git /app/xfd; ",
      "sh"
    ]
  }
]
EOF
  requires_compatibilities = ["FARGATE"]
  # "awsvpc" is required for Fargate tasks to enable the use of ENIs for networking.
  network_mode       = "awsvpc"
  execution_role_arn = aws_iam_role.playwright_worker_task_execution_role.arn # Execution role for ECS tasks
  task_role_arn      = aws_iam_role.playwright_worker_task_role.arn           # Task role for the application

  cpu    = 256 # .25 vCPU
  memory = 512 # 512 MB

  tags = {
    Project = var.project
    Stage   = var.stage
    Owner   = "Crossfeed managed resource"
  }
}

resource "aws_ecs_cluster" "playwright_ecs_cluster" {
  name = "${var.crossfeed_playwright}-ecs-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Project = var.project
    Stage   = var.stage
    Owner   = "Crossfeed managed resource"
  }
}

resource "aws_ecs_cluster_capacity_providers" "playwright_ecs_cluster_capacity_providers" {
  cluster_name       = aws_ecs_cluster.playwright_ecs_cluster.name
  capacity_providers = ["FARGATE"]
}

resource "aws_s3_bucket" "automated_test_reports_bucket" {
  bucket = var.automated_test_reports_bucket_name
  tags = {
    Project = var.project
    Stage   = var.stage
    Owner   = "Crossfeed managed resource"
  }
}

resource "aws_s3_bucket_policy" "automated_test_reports_bucket" {
  bucket = var.automated_test_reports_bucket_name
  policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Sid" : "RequireSSLRequests",
        "Action" : "s3:*",
        "Effect" : "Deny",
        "Principal" : "*",
        "Resource" : [
          aws_s3_bucket.automated_test_reports_bucket.arn,
          "${aws_s3_bucket.automated_test_reports_bucket.arn}/*"
        ],
        "Condition" : {
          "Bool" : {
            "aws:SecureTransport" : "false"
          }
        }
      }
    ]
  })
}

resource "aws_s3_bucket_acl" "automated_test_reports_bucket" {
  count  = var.is_dmz ? 1 : 0
  bucket = aws_s3_bucket.automated_test_reports_bucket.id
  acl    = "private"
}

resource "aws_s3_bucket_ownership_controls" "automated_test_reports_bucket" {
  count  = var.is_dmz ? 1 : 0
  bucket = aws_s3_bucket.automated_test_reports_bucket.id
  rule {
    object_ownership = "ObjectWriter"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "automated_test_reports_bucket" {
  bucket = aws_s3_bucket.automated_test_reports_bucket.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "automated_test_reports_bucket" {
  bucket = aws_s3_bucket.automated_test_reports_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_logging" "automated_test_reports_bucket" {
  bucket        = aws_s3_bucket.automated_test_reports_bucket.id
  target_bucket = aws_s3_bucket.logging_bucket.id
  target_prefix = "automated_test_reports_bucket/"
}
