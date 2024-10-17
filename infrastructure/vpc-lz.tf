data "aws_ssm_parameter" "vpc_name" {
  count = var.is_dmz ? 0 : 1
  name  = var.ssm_crossfeed_vpc_name
}

data "aws_ssm_parameter" "vpc_id" {
  count = var.is_dmz ? 0 : 1
  name  = var.ssm_vpc_id
}
data "aws_ssm_parameter" "vpc_cidr_block" {
  count = var.is_dmz ? 0 : 1
  name  = var.ssm_vpc_cidr_block
}
data "aws_ssm_parameter" "route_table_endpoints_id" {
  count = var.is_dmz ? 0 : 1
  name  = var.ssm_route_table_endpoints_id
}
data "aws_ssm_parameter" "route_table_private_A_id" {
  count = var.is_dmz ? 0 : 1
  name  = var.ssm_route_table_private_A_id
}
data "aws_ssm_parameter" "route_table_private_B_id" {
  count = var.is_dmz ? 0 : 1
  name  = var.ssm_route_table_private_B_id
}
data "aws_ssm_parameter" "route_table_private_C_id" {
  count = var.is_dmz ? 0 : 1
  name  = var.ssm_route_table_private_C_id
}
data "aws_ssm_parameter" "subnet_backend_id" {
  count = var.is_dmz ? 0 : 1
  name  = var.ssm_subnet_backend_id
}
data "aws_ssm_parameter" "subnet_worker_id" {
  count = var.is_dmz ? 0 : 1
  name  = var.ssm_subnet_worker_id
}
data "aws_ssm_parameter" "subnet_matomo_id" {
  count = var.is_dmz ? 0 : 1
  name  = var.ssm_subnet_matomo_id
}
data "aws_ssm_parameter" "subnet_db_1_id" {
  count = var.is_dmz ? 0 : 1
  name  = var.ssm_subnet_db_1_id
}
data "aws_ssm_parameter" "subnet_db_2_id" {
  count = var.is_dmz ? 0 : 1
  name  = var.ssm_subnet_db_2_id
}
data "aws_ssm_parameter" "subnet_es_id" {
  count = var.is_dmz ? 0 : 1
  name  = var.ssm_subnet_es_id
}


resource "aws_route_table_association" "r_assoc_backend_lz" {
  count          = var.is_dmz ? 0 : 1
  route_table_id = data.aws_ssm_parameter.route_table_endpoints_id[0].value
  subnet_id      = data.aws_ssm_parameter.subnet_backend_id[0].value
}

resource "aws_route_table_association" "r_assoc_worker_lz" {
  count          = var.is_dmz ? 0 : 1
  route_table_id = data.aws_ssm_parameter.route_table_endpoints_id[0].value
  subnet_id      = data.aws_ssm_parameter.subnet_worker_id[0].value
}

resource "aws_route_table_association" "r_assoc_matomo_lz" {
  count          = var.is_dmz ? 0 : 1
  route_table_id = data.aws_ssm_parameter.route_table_endpoints_id[0].value
  subnet_id      = data.aws_ssm_parameter.subnet_matomo_id[0].value
}

resource "aws_route_table_association" "r_assoc_db1" {
  count          = var.is_dmz ? 0 : 1
  route_table_id = data.aws_ssm_parameter.route_table_private_A_id[0].value
  subnet_id      = data.aws_ssm_parameter.subnet_db_1_id[0].value
}

resource "aws_route_table_association" "r_assoc_db2" {
  count          = var.is_dmz ? 0 : 1
  route_table_id = data.aws_ssm_parameter.route_table_private_B_id[0].value
  subnet_id      = data.aws_ssm_parameter.subnet_db_2_id[0].value
}

resource "aws_route_table_association" "r_assoc_es_1" {
  count          = var.is_dmz ? 0 : 1
  route_table_id = data.aws_ssm_parameter.route_table_private_C_id[0].value
  subnet_id      = data.aws_ssm_parameter.subnet_es_id[0].value
}

resource "aws_security_group" "allow_internal_lz" {
  count       = var.is_dmz ? 0 : 1
  name        = "allow-internal"
  description = "Allow All VPC Internal Traffic"
  vpc_id      = data.aws_ssm_parameter.vpc_id[0].value

  ingress {
    description = "All Lambda Subnet"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [data.aws_ssm_parameter.vpc_cidr_block[0].value]
  }

  ingress {
    description = "Nessus Scan"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["10.232.0.94/32"]
  }

  ingress {
    description = "Crowdstrike Server"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["10.234.0.0/15", "10.232.0.0/15", "52.61.0.0/17", "10.236.0.0/24", "96.127.0.0/17"]
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
    Owner   = "Crossfeed managed resource"
  }
}

resource "aws_security_group" "worker_lz" {
  count       = var.is_dmz ? 0 : 1
  name        = "worker"
  description = "Worker"
  vpc_id      = data.aws_ssm_parameter.vpc_id[0].value

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Project = var.project
    Stage   = var.stage
    Owner   = "Crossfeed managed resource"
  }
}
