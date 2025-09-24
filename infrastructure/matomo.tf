
resource "aws_ecs_cluster" "matomo" {
  name = var.matomo_ecs_cluster_name

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

resource "aws_ecs_cluster_capacity_providers" "matomo" {
  cluster_name       = aws_ecs_cluster.matomo.name
  capacity_providers = ["FARGATE"]
}

resource "aws_iam_role" "matomo_task_execution_role" {
  name               = var.matomo_ecs_role_name
  assume_role_policy = <<EOF
{
  "Version": "2008-10-17",
  "Statement": [
    {
      "Sid": "",
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
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

resource "aws_iam_role_policy" "matomo_task_execution_role_policy" {
  name_prefix = var.matomo_ecs_role_name
  role        = aws_iam_role.matomo_task_execution_role.id

  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "ssm:GetParameters"
      ],
      "Resource": "*"
    }
  ]
}
EOF
}

resource "aws_security_group" "efs_matomo" {
  name        = "matomo-${var.stage}"
  description = "Allow NFS from ECS tasks"
  vpc_id      = aws_vpc.crossfeed_vpc[0].id

  ingress {
    from_port       = 2049
    to_port         = 2049
    protocol        = "tcp"
    security_groups = [aws_security_group.allow_internal[0].id]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Project = var.project
    Stage   = var.stage
  }
}

resource "aws_efs_file_system" "matomo" {
  encrypted = true
  lifecycle_policy { transition_to_ia = "AFTER_30_DAYS" }
  tags = {
    Name    = "matomo-${var.stage}"
    Project = var.project
    Stage   = var.stage
  }
}

# Create mount target(s) in the subnet(s) where ECS tasks run
resource "aws_efs_mount_target" "matomo" {
  file_system_id  = aws_efs_file_system.matomo.id
  subnet_id       = aws_subnet.matomo_1[0].id
  security_groups = [aws_security_group.efs_matomo.id]
}

# Access point sets POSIX ownership to www-data (uid/gid=33) under /html
resource "aws_efs_access_point" "matomo_html" {
  file_system_id = aws_efs_file_system.matomo.id

  posix_user {
    uid = 33
    gid = 33
  }

  root_directory {
    path = "/html"
    creation_info {
      owner_uid   = 33
      owner_gid   = 33
      permissions = "0755"
    }
  }

  tags = {
    Project = var.project
    Stage   = var.stage
  }
}

resource "aws_iam_role_policy" "matomo_task_exec_efs" {
  name = "${var.matomo_ecs_role_name}-efs"
  role = aws_iam_role.matomo_task_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "elasticfilesystem:ClientMount",
          "elasticfilesystem:ClientWrite",
          "elasticfilesystem:ClientRootAccess"
        ],
        Resource = [
          aws_efs_file_system.matomo.arn,
          aws_efs_access_point.matomo_html.arn
        ]
      }
    ]
  })
}


resource "aws_ecs_task_definition" "matomo" {
  family                   = var.matomo_ecs_task_definition_family
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.matomo_task_execution_role.arn

  volume {
    name = "matomo_html"
    efs_volume_configuration {
      file_system_id     = aws_efs_file_system.matomo.id
      transit_encryption = "ENABLED"
      authorization_config {
        access_point_id = aws_efs_access_point.matomo_html.id
        iam             = "ENABLED"
      }
    }
  }

  container_definitions = jsonencode([
    {
      name      = "main",
      image     = "matomo:5.2.1",
      essential = true,

      # Mount EFS at /var/www/html in Matomo Fargate container
      mountPoints = [
        { sourceVolume = "matomo_html", containerPath = "/var/www/html", readOnly = false }
      ],

      environment = [
        { name = "MATOMO_DATABASE_HOST", value = aws_db_instance.matomo_db.address },
        { name = "MATOMO_DATABASE_ADAPTER", value = "mysql" },
        { name = "MATOMO_DATABASE_TABLES_PREFIX", value = "matomo_" },
        { name = "MATOMO_DATABASE_USERNAME", value = aws_db_instance.matomo_db.username },
        { name = "MATOMO_DATABASE_DBNAME", value = aws_db_instance.matomo_db.db_name },
        { name = "MATOMO_GENERAL_PROXY_URI_HEADER", value = "1" },
        { name = "MATOMO_GENERAL_ASSUME_SECURE_PROTOCOL", value = "1" },
        { name = "MATOMO_GENERAL_FORCE_SSL", value = "1" },
        { name = "MATOMO_FORCE_INDEX_URL", value = var.matomo_force_index_url },
        { name = "MATOMO_CONFIG_PATH", value = "/var/www/html/config/config.ini.php" }
      ],

      secrets = [
        { name = "MATOMO_DATABASE_PASSWORD", valueFrom = aws_ssm_parameter.matomo_db_password.arn }
      ],

      # Bootstrap: write/patch config.ini.php on EFS, then start Apache
      command = [
        "/bin/sh", "-lc",
        <<-EOC
          set -eu
          CONFIG="$${MATOMO_CONFIG_PATH:-/var/www/html/config/config.ini.php}"
          URL="$${MATOMO_FORCE_INDEX_URL:-}"
          [ -n "$URL" ] || { echo "MATOMO_FORCE_INDEX_URL not set"; exit 1; }

          mkdir -p "$(dirname "$CONFIG")"
          if [ ! -f "$CONFIG" ]; then
            printf '%s\n' '; <?php exit; ?> DO NOT REMOVE THIS LINE' '[General]' > "$CONFIG"
          fi

          TMP="$(mktemp)"
          awk -v url="$URL" '
          BEGIN {
            scal["assume_secure_protocol"]="1"
            scal["force_ssl"]="1"
            scal["force_index_url"]="\"" url "\""
            scal["proxy_uri_header"]="1"
            arr["proxy_client_headers[]"]="\"HTTP_X_FORWARDED_FOR\""
            arr["proxy_host_headers[]"]="\"HTTP_X_FORWARDED_HOST\""
            arr["trusted_hosts[]"]="\"matomo\""
            for (k in scal) seenS[k]=0
            for (k in arr)  seenA[k]=0
          }
          function flush_missing(){
            for (k in scal) if(!seenS[k]) print k " = " scal[k]
            for (k in arr)  if(!seenA[k]) print k " = " arr[k]
          }
          {
            line=$0
            if ($0 ~ /^\\[/) {
              if (inG && $0 !~ /^\\[General\\]/) { flush_missing(); inG=0 }
              if ($0 ~ /^\\[General\\]/) inG=1
            }
            if (inG) {
              for (k in scal) {
                p="^(" k ")[ \\t]*=.*$"
                if ($0 ~ p) { print k " = " scal[k]; seenS[k]=1; next }
              }
              for (k in arr) {
                p="^(" k ")[ \\t]*=[ \\t]*" arr[k] "[ \\t]*$"
                if ($0 ~ p) { seenA[k]=1 }
              }
            }
            print line
          }
          END { if (inG) flush_missing() }
          ' "$CONFIG" > "$TMP" && mv "$TMP" "$CONFIG"

          chmod 0640 "$CONFIG" || true
          exec docker-php-entrypoint apache2-foreground
        EOC
      ],

      logConfiguration = {
        logDriver = "awslogs",
        options = {
          awslogs-group         = var.matomo_ecs_log_group_name,
          awslogs-region        = var.aws_region,
          awslogs-stream-prefix = "matomo"
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

resource "aws_service_discovery_private_dns_namespace" "default" {
  count       = var.is_dmz ? 1 : 0
  name        = "crossfeed.local"
  description = "Crossfeed ${var.stage}"
  vpc         = aws_vpc.crossfeed_vpc[0].id
}

resource "aws_service_discovery_service" "matomo" {
  # ECS service can be accessed through http://matomo.cfs.lz.us-cert.gov
  count = var.is_dmz ? 1 : 0
  name  = "matomo"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.default[0].id

    dns_records {
      ttl  = 10
      type = "A"
    }

    routing_policy = "MULTIVALUE"
  }
}

resource "aws_ecs_service" "matomo" {
  count           = var.is_dmz ? 1 : 0
  name            = "matomo"
  launch_type     = "FARGATE"
  cluster         = aws_ecs_cluster.matomo.id
  task_definition = aws_ecs_task_definition.matomo.arn
  desired_count   = 1
  network_configuration {
    subnets         = [aws_subnet.matomo_1[0].id]
    security_groups = [aws_security_group.allow_internal[0].id]
  }
  service_registries {
    registry_arn = aws_service_discovery_service.matomo[0].arn
  }
}

resource "aws_cloudwatch_log_group" "matomo" {
  name              = var.matomo_ecs_log_group_name
  retention_in_days = 3653
  kms_key_id        = aws_kms_key.key.arn
  tags = {
    Project = var.project
    Stage   = var.stage
    Owner   = "Crossfeed managed resource"
  }
}

resource "random_password" "matomo_db_password" {
  length  = 16
  special = false
}

resource "aws_db_instance" "matomo_db" {
  identifier                          = var.matomo_db_name
  instance_class                      = var.matomo_db_instance_class
  allocated_storage                   = 20
  max_allocated_storage               = 1000
  storage_type                        = "gp2"
  engine                              = "mariadb"
  engine_version                      = "11.4"
  skip_final_snapshot                 = true
  availability_zone                   = var.matomo_availability_zone
  multi_az                            = true
  backup_retention_period             = 35
  storage_encrypted                   = true
  iam_database_authentication_enabled = false
  allow_major_version_upgrade         = true
  deletion_protection                 = true
  enabled_cloudwatch_logs_exports     = ["audit", "error", "general", "slowquery"]


  // database information
  db_name  = "matomo"
  username = "matomo"
  password = random_password.matomo_db_password.result

  db_subnet_group_name = aws_db_subnet_group.default.name

  vpc_security_group_ids = [var.is_dmz ? aws_security_group.allow_internal[0].id : aws_security_group.allow_internal_lz[0].id]

  tags = {
    Project        = var.project
    Owner          = "Crossfeed managed resource"
    ART            = "CISA-TH"
    POC            = "Lamar Steward   Craig Duhn"
    PocEmail       = "lamar.stewart@cisa.dhs.gov"
    Name           = "crossfeed-matomo-staging"
    BillingProject = "VM-Crossfeed"
    workload-type  = "staging"
  }
}

resource "aws_ssm_parameter" "matomo_db_password" {
  name      = var.ssm_matomo_db_password
  type      = "SecureString"
  value     = random_password.matomo_db_password.result
  overwrite = true

  tags = {
    Project = var.project
    Owner   = "Crossfeed managed resource"
  }
}

# Elastic File System permissions
resource "aws_iam_policy" "efs_deploy_policy" {
  count       = var.is_dmz ? 1 : 0
  name        = "crossfeed-${var.stage}-efs-deploy-policy"
  description = "Allow creating/managing EFS (FS, AP, MT) for Matomo"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Sid    = "EfsCrudAndTagging",
        Effect = "Allow",
        Action = [
          "elasticfilesystem:CreateFileSystem",
          "elasticfilesystem:DeleteFileSystem",
          "elasticfilesystem:UpdateFileSystem",
          "elasticfilesystem:DescribeFileSystems",
          "elasticfilesystem:CreateMountTarget",
          "elasticfilesystem:DeleteMountTarget",
          "elasticfilesystem:DescribeMountTargets",
          "elasticfilesystem:DescribeMountTargetSecurityGroups",
          "elasticfilesystem:CreateAccessPoint",
          "elasticfilesystem:DeleteAccessPoint",
          "elasticfilesystem:DescribeAccessPoints",
          "elasticfilesystem:TagResource",
          "elasticfilesystem:UntagResource",
          "elasticfilesystem:ListTagsForResource"
        ],
        Resource = "*"
      },
      {
        Sid    = "Ec2DescribesForEfs",
        Effect = "Allow",
        Action = [
          "ec2:DescribeVpcs",
          "ec2:DescribeSubnets",
          "ec2:DescribeSecurityGroups"
        ],
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_user_policy_attachment" "efs_deploy_user_attach" {
  count      = var.is_dmz ? 1 : 0
  user       = "crossfeed-deploy-staging"
  policy_arn = aws_iam_policy.efs_deploy_policy[0].arn
}
