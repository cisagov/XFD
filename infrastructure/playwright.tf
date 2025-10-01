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
          "arn:${var.aws_partition}:s3:::${var.automated_test_reports_bucket_name}",  # ListBucket on the bucket itself
          "arn:${var.aws_partition}:s3:::${var.automated_test_reports_bucket_name}/*" # GetObject and PutObject on all objects within the bucket
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "playwright_ecs_execution_policy" {
  policy_arn = "arn:${var.aws_partition}:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
  role       = aws_iam_role.playwright_worker_task_execution_role.id
}

resource "aws_ecr_repository" "playwright_worker" {
  name = var.playwright_worker_repository_name

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
    Owner   = "Crossfeed managed resource"
  }
}


resource "aws_ecs_task_definition" "playwright_worker" {
  family                   = var.playwright_worker_ecs_task_definition_family
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024

  execution_role_arn = aws_iam_role.playwright_worker_task_execution_role.arn
  task_role_arn      = aws_iam_role.playwright_worker_task_role.arn

  container_definitions = jsonencode([
    {
      name      = "main",
      image     = "${aws_ecr_repository.playwright_worker.repository_url}:latest", # Your custom image
      essential = true,

      environment = [
        { name = "AWS_REGION", value = var.aws_region },
        { name = "BROWSER_TYPE", value = "chromium" },
        { name = "TEST_URL", value = var.frontend_domain },
        // additional overrides like S3 paths can still be injected at runtime

        // Required by run_playwright_tests.sh
        { name = "PW_XFD_URL", value = "" },
        { name = "PW_XFD_USERNAME", value = "" },
        { name = "PW_XFD_PASSWORD", value = "" },
        { name = "PW_XFD_2FA_SECRET", value = "" },
        { name = "PW_XFD_LOGIN", value = "" },
        { name = "ENVIRONMENT", value = "" },
        { name = "DATETIME", value = "" },
        { name = "GIT_BRANCH", value = "" },
        { name = "AUTOMATED_TEST_REPORTS_BUCKET_NAME", value = "" },
        { name = "S3_HTML_PATH", value = "" },
        { name = "S3_JSON_PATH", value = "" },
        { name = "PW_HEADLESS", value = "" },
        { name = "PW_CI", value = "" },
      ],

      logConfiguration = {
        logDriver = "awslogs",
        options = {
          awslogs-group         = var.worker_ecs_log_group_name,
          awslogs-region        = var.aws_region,
          awslogs-stream-prefix = "playwright"
        }
      }
    }
  ])

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
