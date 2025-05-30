
resource "aws_security_group" "elasticache_security_group" {
  name_prefix = "elasticache-"
  description = "ElastiCache security group"
  vpc_id      = var.is_dmz ? aws_vpc.crossfeed_vpc[0].id : data.aws_ssm_parameter.vpc_id[0].value
  ingress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = [var.is_dmz ? aws_vpc.crossfeed_vpc[0].cidr_block : data.aws_ssm_parameter.vpc_cidr_block[0].value] // Dynamically restrict to a specific CIDR block, ideally your VPC's CIDR
  }
}


resource "aws_elasticache_subnet_group" "crossfeed_vpc" {
  name       = "crossfeed-${var.stage}-elasticache-subnet-group"
  subnet_ids = [var.is_dmz ? aws_subnet.backend[0].id : data.aws_ssm_parameter.subnet_db_1_id[0].value]

  tags = {
    Name = "crossfeed_vpc"
  }
}

resource "aws_elasticache_parameter_group" "xfd_redis_group" {
  name   = "crossfeed-${var.stage}-redis7-group"
  family = "redis7"

  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }
}

resource "aws_elasticache_cluster" "crossfeed_vpc_elasticache_cluster" {
  count                = var.create_elasticache_cluster ? 1 : 0
  cluster_id           = "crossfeed-${var.stage}-elasticache-cluster"
  engine               = "redis"
  node_type            = var.is_dmz ? "cache.r7g.xlarge" : "cache.r6g.xlarge"
  num_cache_nodes      = 1
  parameter_group_name = aws_elasticache_parameter_group.xfd_redis_group.name
  engine_version       = "7.1"
  port                 = 6379
  subnet_group_name    = aws_elasticache_subnet_group.crossfeed_vpc.name
  security_group_ids   = [aws_security_group.elasticache_security_group.id]

  tags = {
    Name    = "crossfeed_vpc_elasticache-cluster"
    Project = var.project
    Stage   = var.stage
  }
}

resource "aws_iam_policy" "elasticache_policy" {
  count       = var.is_dmz ? 1 : 0
  name        = "crossfeed-${var.stage}-elasticache-policy"
  description = "Policy to allow ElastiCache operations"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "elasticache:AddTagsToResource",
          "elasticache:CreateCacheCluster",
          "elasticache:CreateCacheParameterGroup",
          "elasticache:CreateCacheSubnetGroup",
          "elasticache:DeleteCacheParameterGroup",
          "elasticache:DeleteCacheSubnetGroup",
          "elasticache:DescribeCacheClusters",
          "elasticache:DescribeCacheEngineVersions",
          "elasticache:DescribeCacheParameterGroups",
          "elasticache:DescribeCacheParameters",
          "elasticache:DescribeCacheSecurityGroups",
          "elasticache:DescribeCacheSubnetGroups",
          "elasticache:ListTagsForResource",
          "elasticache:ModifyCacheParameterGroup",
          "elasticache:ModifyCacheSubnetGroup",
          "iam:AttachUserPolicy",
          "iam:CreatePolicy",
          "iam:CreatePolicyVersion",
          "iam:DeletePolicy",
          "iam:DetachUserPolicy",
          "iam:GetPolicyVersion",
          "iam:ListAttachedUserPolicies",
          "iam:ListPolicyVersions",
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_user_policy_attachment" "elasticache_user_policy_attachment" {
  count      = var.is_dmz ? 1 : 0
  user       = "crossfeed-deploy-staging"
  policy_arn = aws_iam_policy.elasticache_policy[0].arn
}
