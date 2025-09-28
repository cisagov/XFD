# Purpose: Manage ADOT Lambda layer ARN (GovCloud) and optional VPC endpoints for X-Ray and CloudWatch Logs.
# ---- Inputs (new) ----
variable "adot_python_layer_arn_govcloud" {
  type        = string
  default     = ""
  description = "Your ADOT Python Lambda Layer ARN to use in aws-us-gov partitions. Publish once per GovCloud region and paste the ARN here."

  # Fail fast if deploying to GovCloud without providing the layer ARN
  validation {
    condition     = var.aws_partition != "aws-us-gov" || length(trim(var.adot_python_layer_arn_govcloud)) > 0
    error_message = "GovCloud detected (aws-us-gov) but 'adot_python_layer_arn_govcloud' is empty. Publish your ADOT layer in this region and set its ARN."
  }
}

variable "create_vpc_endpoints" {
  type        = bool
  default     = true
  description = "Whether to create interface VPC endpoints for X-Ray and CloudWatch Logs."
}

# ---- Identity ----
data "aws_caller_identity" "current" {}

# ---- Network ids pulled from SSM (you already pass these in tfvars) ----
data "aws_ssm_parameter" "vpc_id" { name = var.ssm_vpc_id }
data "aws_ssm_parameter" "vpc_cidr" { name = var.ssm_vpc_cidr_block }
data "aws_ssm_parameter" "subnet_ep_a" { name = var.ssm_subnet_backend_id }
data "aws_ssm_parameter" "subnet_ep_b" { name = var.ssm_subnet_worker_id }
data "aws_ssm_parameter" "subnet_ep_c" { name = var.ssm_subnet_matomo_id }

# ---- Locals ----
locals {
  is_gov = var.aws_partition == "aws-us-gov"
  subnets_ep = compact([
    data.aws_ssm_parameter.subnet_ep_a.value,
    data.aws_ssm_parameter.subnet_ep_b.value,
    data.aws_ssm_parameter.subnet_ep_c.value
  ])
  vpc_id           = data.aws_ssm_parameter.vpc_id.value
  vpc_cidr         = data.aws_ssm_parameter.vpc_cidr.value
  account_root_arn = "arn:${var.aws_partition}:iam::${data.aws_caller_identity.current.account_id}:root"

  # GovCloud: use your published layer ARN from tfvars
  # Commercial: let Serverless use AWS-managed ARNs directly (no SSM needed)
  adot_python_layer_arn_resolved = local.is_gov ? var.adot_python_layer_arn_govcloud : ""
}

# ---- Publish the layer ARN for Serverless to consume (GovCloud only) ----
resource "aws_ssm_parameter" "adot_python_layer_arn" {
  count       = local.is_gov ? 1 : 0
  name        = "/crossfeed/${var.stage}/adot_python_layer_arn"
  description = "ADOT Python Lambda Layer ARN for ${var.stage} (${var.aws_region})"
  type        = "String"
  value       = local.adot_python_layer_arn_resolved
}

# ---- Security group for Interface VPC Endpoints (tight inbound on 443) ----
resource "aws_security_group" "telemetry_endpoints_sg" {
  count       = var.create_vpc_endpoints ? 1 : 0
  name        = "crossfeed-${var.stage}-telemetry-endpoints"
  description = "Restrict access to X-Ray and CloudWatch Logs interface endpoints"
  vpc_id      = local.vpc_id

  ingress {
    description = "HTTPS from within VPC"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [local.vpc_cidr]
  }

  # Allow return traffic; scope to VPC CIDR
  egress {
    description = "Responses to VPC"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [local.vpc_cidr]
  }

  tags = {
    Project = var.project
    Stage   = var.stage
    Owner   = "Crossfeed managed resource"
  }
}

# ---- Endpoint policies (limit use to our account) ----
locals {
  xray_vpce_policy = {
    Version = "2012-10-17",
    Statement = [
      {
        Sid       = "AllowXRayWritesFromThisAccount",
        Effect    = "Allow",
        Principal = { AWS = local.account_root_arn },
        Action = [
          "xray:PutTraceSegments",
          "xray:PutTelemetryRecords",
          "xray:GetSamplingRules",
          "xray:GetSamplingTargets",
          "xray:GetSamplingStatisticSummaries"
        ],
        Resource = "*"
      }
    ]
  }

  logs_vpce_policy = {
    Version = "2012-10-17",
    Statement = [
      {
        Sid       = "AllowCWLogsFromThisAccount",
        Effect    = "Allow",
        Principal = { AWS = local.account_root_arn },
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams"
        ],
        Resource = "*"
      }
    ]
  }
}

# ---- Interface VPC Endpoints (toggle via create_vpc_endpoints) ----
# X-Ray endpoint service name: com.amazonaws.${region}.xray
resource "aws_vpc_endpoint" "xray" {
  count               = var.create_vpc_endpoints ? 1 : 0
  vpc_id              = local.vpc_id
  service_name        = "com.amazonaws.${var.aws_region}.xray"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  subnet_ids          = local.subnets_ep
  security_group_ids  = [aws_security_group.telemetry_endpoints_sg[0].id]
  policy              = jsonencode(local.xray_vpce_policy)

  tags = {
    Project = var.project
    Stage   = var.stage
    Owner   = "Crossfeed managed resource"
  }
}

# CloudWatch Logs endpoint service name: com.amazonaws.${region}.logs
resource "aws_vpc_endpoint" "logs" {
  count               = var.create_vpc_endpoints ? 1 : 0
  vpc_id              = local.vpc_id
  service_name        = "com.amazonaws.${var.aws_region}.logs"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  subnet_ids          = local.subnets_ep
  security_group_ids  = [aws_security_group.telemetry_endpoints_sg[0].id]
  policy              = jsonencode(local.logs_vpce_policy)

  tags = {
    Project = var.project
    Stage   = var.stage
    Owner   = "Crossfeed managed resource"
  }
}

# ---- Outputs ----
output "adot_python_layer_arn" {
  value       = local.adot_python_layer_arn_resolved
  description = "Resolved ADOT Lambda layer ARN for this region/partition (empty in Commercial)"
}

output "xray_vpc_endpoint_id" {
  value       = try(aws_vpc_endpoint.xray[0].id, null)
  description = "ID of the X-Ray Interface VPC Endpoint (if created)"
}

output "logs_vpc_endpoint_id" {
  value       = try(aws_vpc_endpoint.logs[0].id, null)
  description = "ID of the CloudWatch Logs Interface VPC Endpoint (if created)"
}
