resource "aws_security_group" "elasticache_security_group" {
  name_prefix = "elasticache-"
  description = "ElastiCache security group"
  vpc_id      = aws_vpc.crossfeed_vpc.id
  ingress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.crossfeed_vpc.cidr_block] // Dynamically restrict to a specific CIDR block, ideally your VPC's CIDR
  }
}

resource "aws_elasticache_subnet_group" "crossfeed_vpc" {
  name       = "crossfeed-vpc-subnet-group"
  subnet_ids = [aws_subnet.backend.id]

  tags = {
    Name = "crossfeed_vpc"
  }
}

resource "aws_elasticache_parameter_group" "xfd_redis_group" {
  name   = "my-redis7-1"
  family = "redis7"

  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }
}

resource "aws_elasticache_cluster" "crossfeed_vpc_elasticache_cluster" {
  count                = var.create_elasticache_cluster ? 1 : 0
  cluster_id           = "crossfeed-vpc-cluster"
  engine               = "redis"
  node_type            = "cache.r7g.xlarge"
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
  name        = "elasticache_policy"
  description = "Policy to allow ElastiCache operations"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "elasticache:CreateCacheCluster",
          "elasticache:CreateCacheSubnetGroup",
          "elasticache:DeleteCacheSubnetGroup",
          "elasticache:DescribeCacheSubnetGroups",
          "elasticache:DescribeCacheClusters",
          "elasticache:DescribeCacheEngineVersions",
          "elasticache:DescribeCacheSecurityGroups",
          "elasticache:DescribeCacheParameters",
          "elasticache:DescribeCacheParameterGroups",
          "elasticache:ModifyCacheSubnetGroup",
          "elasticache:AddTagsToResource",
          "elasticache:ListTagsForResource",
          "elasticache:CreateCacheParameterGroup",
          "elasticache:DeleteCacheParameterGroup",
          "elasticache:DescribeCacheParameterGroups",
          "elasticache:ModifyCacheParameterGroup",
          "iam:ListAttachedUserPolicies",
          "iam:CreatePolicy",
          "iam:CreatePolicyVersion",
          "iam:AttachUserPolicy",
          "iam:GetPolicyVersion",
          "iam:ListPolicyVersions",
          "iam:DeletePolicy",
          "iam:DetachUserPolicy"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_user_policy_attachment" "elasticache_user_policy_attachment" {
  user       = "crossfeed-deploy-staging"
  policy_arn = aws_iam_policy.elasticache_policy.arn
}
