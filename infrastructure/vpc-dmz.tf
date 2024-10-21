resource "aws_vpc" "crossfeed_vpc" {
  count                = var.is_dmz ? 1 : 0
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = {
    Project = var.project
  }
}

resource "aws_subnet" "db_1" {
  count             = var.is_dmz ? 1 : 0
  availability_zone = data.aws_availability_zones.available.names[0]
  vpc_id            = aws_vpc.crossfeed_vpc[0].id
  cidr_block        = "10.0.1.0/28"

  tags = {
    Project = var.project
  }
}

resource "aws_subnet" "db_2" {
  count             = var.is_dmz ? 1 : 0
  availability_zone = data.aws_availability_zones.available.names[1]
  vpc_id            = aws_vpc.crossfeed_vpc[0].id
  cidr_block        = "10.0.1.16/28"

  tags = {
    Project = var.project
  }
}

resource "aws_subnet" "backend" {
  count             = var.is_dmz ? 1 : 0
  availability_zone = data.aws_availability_zones.available.names[1]
  vpc_id            = aws_vpc.crossfeed_vpc[0].id
  cidr_block        = "10.0.2.0/24"

  tags = {
    Project = var.project
  }
}

resource "aws_subnet" "worker" {
  count             = var.is_dmz ? 1 : 0
  availability_zone = data.aws_availability_zones.available.names[1]
  vpc_id            = aws_vpc.crossfeed_vpc[0].id
  cidr_block        = "10.0.3.0/24"

  tags = {
    Project = var.project
    Stage   = var.stage
  }
}

resource "aws_subnet" "es_1" {
  count             = var.is_dmz ? 1 : 0
  availability_zone = data.aws_availability_zones.available.names[0]
  vpc_id            = aws_vpc.crossfeed_vpc[0].id
  cidr_block        = "10.0.4.0/28"

  tags = {
    Project = var.project
  }
}

resource "aws_subnet" "matomo_1" {
  count             = var.is_dmz ? 1 : 0
  availability_zone = data.aws_availability_zones.available.names[0]
  vpc_id            = aws_vpc.crossfeed_vpc[0].id
  cidr_block        = "10.0.5.0/28"

  tags = {
    Project = var.project
  }
}

resource "aws_route_table" "r" {
  count  = var.is_dmz ? 1 : 0
  vpc_id = aws_vpc.crossfeed_vpc[0].id

  tags = {
    Project = var.project
    Stage   = var.stage
  }
}

resource "aws_route_table" "r2" {
  count  = var.is_dmz ? 1 : 0
  vpc_id = aws_vpc.crossfeed_vpc[0].id

  route {
    nat_gateway_id = aws_nat_gateway.nat[0].id
    cidr_block     = "0.0.0.0/0"
  }

  tags = {
    Project = var.project
    Stage   = var.stage
  }
}

resource "aws_route_table" "worker" {
  count  = var.is_dmz ? 1 : 0
  vpc_id = aws_vpc.crossfeed_vpc[0].id

  route {
    gateway_id = aws_internet_gateway.gw[0].id
    cidr_block = "0.0.0.0/0"
  }

  tags = {
    Project = var.project
    Stage   = var.stage
  }
}

resource "aws_route_table_association" "r_assoc_db_1" {
  count          = var.is_dmz ? 1 : 0
  route_table_id = aws_route_table.r[0].id
  subnet_id      = aws_subnet.db_1[0].id
}

resource "aws_route_table_association" "r_assoc_db_2" {
  count          = var.is_dmz ? 1 : 0
  route_table_id = aws_route_table.r[0].id
  subnet_id      = aws_subnet.db_2[0].id
}

resource "aws_route_table_association" "r_assoc_backend" {
  count          = var.is_dmz ? 1 : 0
  route_table_id = aws_route_table.r2[0].id
  subnet_id      = aws_subnet.backend[0].id
}

resource "aws_route_table_association" "r_assoc_matomo" {
  count          = var.is_dmz ? 1 : 0
  route_table_id = aws_route_table.r2[0].id
  subnet_id      = aws_subnet.matomo_1[0].id
}

resource "aws_route_table_association" "r_assoc_worker" {
  count          = var.is_dmz ? 1 : 0
  route_table_id = aws_route_table.worker[0].id
  subnet_id      = aws_subnet.worker[0].id
}

resource "aws_internet_gateway" "gw" {
  count  = var.is_dmz ? 1 : 0
  vpc_id = aws_vpc.crossfeed_vpc[0].id

  tags = {
    Project = var.project
  }
}

resource "aws_eip" "nat_eip" {
  count = var.is_dmz ? 1 : 0
  tags = {
    Project = var.project
    Stage   = var.stage
  }
}

resource "aws_nat_gateway" "nat" {
  count         = var.is_dmz ? 1 : 0
  allocation_id = aws_eip.nat_eip[0].id
  subnet_id     = aws_subnet.worker[0].id

  tags = {
    Project = var.project
    Stage   = var.stage
  }
}

resource "aws_security_group" "allow_internal" {
  count       = var.is_dmz ? 1 : 0
  name        = "allow-internal"
  description = "Allow All VPC Internal Traffic"
  vpc_id      = aws_vpc.crossfeed_vpc[0].id

  ingress {
    description = "All Lambda Subnet"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [aws_vpc.crossfeed_vpc[0].cidr_block]
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

# TODO: remove this security group. We can't remove it right now because
# AWS created an ENI in this security group that can't be deleted at the moment.
# See https://www.reddit.com/r/aws/comments/4fncrl/dangling_enis_after_deleting_an_invpc_lambda_with/
resource "aws_security_group" "backend" {
  count       = var.is_dmz ? 1 : 0
  name        = "backend"
  description = "Backend"
  vpc_id      = aws_vpc.crossfeed_vpc[0].id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [aws_vpc.crossfeed_vpc[0].cidr_block]
  }

  tags = {
    Project = var.project
    Stage   = var.stage
  }
}


resource "aws_security_group" "worker" {
  count       = var.is_dmz ? 1 : 0
  name        = "worker"
  description = "Worker"
  vpc_id      = aws_vpc.crossfeed_vpc[0].id

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
