# P&E EC2


resource "aws_iam_role" "pe" {
  count              = var.create_pe_instance ? 1 : 0
  name               = "crossfeed-pe-${var.stage}"
  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
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

#Instance Profile
resource "aws_iam_instance_profile" "pe" {
  count = var.create_pe_instance ? 1 : 0
  name  = "crossfeed-pe-${var.stage}"
  role  = aws_iam_role.pe[0].id
}

#Attach Policies to Instance Role
resource "aws_iam_role_policy_attachment" "pe_ssm_core" {
  count      = var.create_pe_instance ? 1 : 0
  role       = aws_iam_role.pe[0].name
  policy_arn = "arn:${var.aws_partition}:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy_attachment" "pe_ssm_service" {
  count      = var.create_pe_instance ? 1 : 0
  role       = aws_iam_role.pe[0].name
  policy_arn = "arn:${var.aws_partition}:iam::aws:policy/service-role/AmazonEC2RoleforSSM"
}

resource "aws_iam_role_policy" "pe_s3_policy" {
  count       = var.create_pe_instance ? 1 : 0
  name_prefix = "crossfeed-pe-s3-${var.stage}"
  role        = aws_iam_role.pe[0].id
  policy      = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:*"
      ],
      "Resource": [
        "${aws_s3_bucket.pe_db_backups_bucket.arn}",
        "${aws_s3_bucket.pe_db_backups_bucket.arn}/*",
        "${aws_s3_bucket.reports_bucket.arn}",
        "${aws_s3_bucket.reports_bucket.arn}/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction"
      ],
      "Resource": [
        "*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeClusters",
        "ecs:DescribeTasks",
        "ecs:ListClusters",
        "ecs:ListTasks",
        "sts:AssumeRole"
      ],
      "Resource": "*"
    }
  ]
}
EOF
}

resource "aws_iam_role_policy" "pe_sqs_send_message_policy" {
  count       = var.create_pe_instance ? 1 : 0
  name_prefix = "pe-ec2-send-sqs-message-${var.stage}"
  role        = aws_iam_role.pe[0].id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = [
          "sqs:SendMessage",
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:ListQueues",
          "sqs:GetQueueUrl"
        ],
        Effect   = "Allow",
        Resource = "*"
      }
    ]
  })
}

resource "aws_instance" "pe" {
  count                       = var.create_pe_instance ? 1 : 0
  ami                         = var.is_dmz ? data.aws_ami.ubuntu[0].id : var.ami_id
  instance_type               = var.db_accessor_instance_class
  associate_public_ip_address = false

  depends_on = [
    aws_iam_instance_profile.pe,
    aws_security_group.allow_internal,
    aws_subnet.pe
  ]
  tags = {
    Project = var.project
    Stage   = var.stage
    Name    = "pe_ec2"
  }
  root_block_device {
    volume_size = 1000
  }

  vpc_security_group_ids = [var.is_dmz ? aws_security_group.allow_internal[0].id : aws_security_group.allow_internal_lz[0].id]
  subnet_id              = var.is_dmz ? aws_subnet.pe[0].id : data.aws_ssm_parameter.subnet_db_1_id[0].value

  iam_instance_profile = aws_iam_instance_profile.pe[0].id
  user_data            = file("./ssm-agent-install.sh")
  lifecycle {
    # prevent_destroy = true
    ignore_changes = [ami]
  }
}


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
    "volumesFrom": [],
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
        "name": "SIXGILL_CLIENT_ID",
        "valueFrom": "${data.aws_ssm_parameter.sixgill_client_id.arn}"
      },
      {
        "name": "SIXGILL_CLIENT_SECRET",
        "valueFrom": "${data.aws_ssm_parameter.sixgill_client_secret.arn}"
      },
      {
        "name": "WHOIS_XML_KEY",
        "valueFrom": "${data.aws_ssm_parameter.whoisxml_api_key.arn}"
      },
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
  }
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
