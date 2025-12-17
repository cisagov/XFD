
data "aws_ssm_parameter" "db_password" { name = var.ssm_db_password }
data "aws_ssm_parameter" "db_username" { name = var.ssm_db_username }

resource "aws_db_subnet_group" "default" {
  name       = var.db_group_name
  subnet_ids = var.is_dmz ? [aws_subnet.db_1[0].id, aws_subnet.db_2[0].id] : [data.aws_ssm_parameter.subnet_db_1_id[0].value, data.aws_ssm_parameter.subnet_db_2_id[0].value]

  tags = {
    Project = var.project
    Owner   = "Crossfeed managed resource"
  }
}

resource "aws_db_parameter_group" "default" {
  name   = "crossfeed-${var.stage}-postgres17"
  family = "postgres17"

  parameter {
    name  = "rds.force_ssl"
    value = "0"
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_db_instance" "db" {
  identifier                  = var.db_name
  instance_class              = var.db_instance_class
  allocated_storage           = 1000
  max_allocated_storage       = 10000
  storage_type                = "gp3"
  iops                        = 16000
  storage_throughput          = 1000
  engine                      = "postgres"
  engine_version              = "17.6"
  allow_major_version_upgrade = true
  skip_final_snapshot         = true
  availability_zone = (
    var.stage == "staging"
    ? data.aws_availability_zones.available.names[0]
    : data.aws_availability_zones.available.names[0]
  )
  multi_az                            = true
  backup_retention_period             = 35
  storage_encrypted                   = true
  iam_database_authentication_enabled = true
  enabled_cloudwatch_logs_exports     = ["postgresql", "upgrade"]
  deletion_protection                 = true

  // database information
  db_name  = var.db_table_name
  username = data.aws_ssm_parameter.db_username.value
  password = data.aws_ssm_parameter.db_password.value
  port     = var.db_port

  db_subnet_group_name = aws_db_subnet_group.default.name
  parameter_group_name = aws_db_parameter_group.default.name

  vpc_security_group_ids = [var.is_dmz ? aws_security_group.allow_internal[0].id : aws_security_group.allow_internal_lz[0].id]

  tags = {
    Project        = "Crossfeed"
    Owner          = "Crossfeed managed resource"
    ART            = "CISA-VM"
    POC            = "Lamar Steward   Craig Duhn"
    PocEmail       = "lamar.stewart@cisa.dhs.gov"
    Name           = "crossfeed-${var.stage}-db"
    BillingProject = "VM-Crossfeed"
    workload-type  = var.stage
  }
}

data "aws_ami" "ubuntu" {
  count       = var.is_dmz ? 1 : 0
  most_recent = true

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  # Canonical
  owners = ["099720109477"]
}

resource "aws_iam_role" "db_accessor" {
  count              = var.create_db_accessor_instance ? 1 : 0
  name               = "crossfeed-db-accessor-${var.stage}"
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
resource "aws_iam_instance_profile" "db_accessor" {
  count = var.create_db_accessor_instance ? 1 : 0
  name  = "crossfeed-db-accessor-${var.stage}"
  role  = aws_iam_role.db_accessor[0].id
}

#Attach Policies to Instance Role
resource "aws_iam_role_policy_attachment" "db_accessor_ssm_core" {
  count      = var.create_db_accessor_instance ? 1 : 0
  role       = aws_iam_role.db_accessor[0].name
  policy_arn = "arn:${var.aws_partition}:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy_attachment" "db_accessor_ssm_service" {
  count      = var.create_db_accessor_instance ? 1 : 0
  role       = aws_iam_role.db_accessor[0].name
  policy_arn = "arn:${var.aws_partition}:iam::aws:policy/service-role/AmazonEC2RoleforSSM"
}

resource "aws_iam_role_policy" "db_accessor_s3_policy" {
  count       = var.create_db_accessor_instance ? 1 : 0
  name_prefix = "crossfeed-db-accessor-s3-${var.stage}"
  role        = aws_iam_role.db_accessor[0].id
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

resource "aws_iam_role_policy" "sqs_send_message_policy" {
  count       = var.create_db_accessor_instance ? 1 : 0
  name_prefix = "ec2-send-sqs-message-${var.stage}"
  role        = aws_iam_role.db_accessor[0].id
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

resource "aws_instance" "db_accessor" {
  count                       = var.create_db_accessor_instance ? 1 : 0
  ami                         = var.is_dmz ? data.aws_ami.ubuntu[0].id : var.ami_id
  instance_type               = var.db_accessor_instance_class
  associate_public_ip_address = false

  depends_on = [
    aws_iam_instance_profile.db_accessor,
    aws_security_group.allow_internal,
    aws_subnet.backend
  ]
  tags = {
    Project           = var.project
    Stage             = var.stage
    Name              = "db_accessor"
    Owner             = "Crossfeed managed resource"
    ApplicationRole   = ""
    BillingProject    = ""
    Confidentiality   = ""
    Criticality       = ""
    Environment       = ""
    FismaID           = "PRE-08561-GSS-08561"
    OperationalStatus = "Stage"
    ResourceSavings   = ""
    Security          = ""
    StrStp            = ""
    POC               = ""

  }
  root_block_device {
    volume_size = 1000
  }

  vpc_security_group_ids = [var.is_dmz ? aws_security_group.allow_internal[0].id : aws_security_group.allow_internal_lz[0].id]
  subnet_id              = var.is_dmz ? aws_subnet.backend[0].id : data.aws_ssm_parameter.subnet_db_1_id[0].value

  iam_instance_profile = aws_iam_instance_profile.db_accessor[0].id
  user_data            = file("./ssm-agent-install.sh")
  lifecycle {
    # prevent_destroy = true
    ignore_changes = [ami]
  }
}

resource "aws_ssm_parameter" "lambda_sg_id" {
  name      = var.ssm_lambda_sg
  type      = "String"
  value     = var.is_dmz ? aws_security_group.allow_internal[0].id : aws_security_group.allow_internal_lz[0].id
  overwrite = true

  tags = {
    Project = var.project
    Owner   = "Crossfeed managed resource"
  }
}

resource "aws_ssm_parameter" "lambda_subnet_id" {
  name      = var.ssm_lambda_subnet
  type      = "String"
  value     = var.is_dmz ? aws_subnet.backend[0].id : data.aws_ssm_parameter.subnet_db_2_id[0].value
  overwrite = true

  tags = {
    Project = var.project
    Owner   = "Crossfeed managed resource"
  }
}

resource "aws_ssm_parameter" "worker_sg_id" {
  name      = var.ssm_worker_sg
  type      = "String"
  value     = var.is_dmz ? aws_security_group.worker[0].id : aws_security_group.worker_lz[0].id
  overwrite = true

  tags = {
    Project = var.project
    Owner   = "Crossfeed managed resource"
  }
}

resource "aws_ssm_parameter" "worker_subnet_id" {
  name      = var.ssm_worker_subnet
  type      = "String"
  value     = var.is_dmz ? aws_subnet.worker[0].id : data.aws_ssm_parameter.subnet_db_2_id[0].value
  overwrite = true

  tags = {
    Project = var.project
    Owner   = "Crossfeed managed resource"
  }
}

resource "aws_ssm_parameter" "crossfeed_send_db_host" {
  name      = var.ssm_db_host
  type      = "SecureString"
  value     = aws_db_instance.db.address
  overwrite = true

  tags = {
    Project = var.project
    Owner   = "Crossfeed managed resource"
  }
}

resource "aws_ssm_parameter" "crossfeed_send_db_name" {
  name      = var.ssm_db_name
  type      = "SecureString"
  value     = aws_db_instance.db.db_name
  overwrite = true

  tags = {
    Project = var.project
    Owner   = "Crossfeed managed resource"
  }
}
