# Purpose: Manage ADOT Lambda layer ARN (GovCloud) and optional VPC endpoints for X-Ray and CloudWatch Logs.
# ---- Inputs (new) ----
variable "adot_python_layer_arn_govcloud" {
  type        = string
  default     = ""
  description = "Your ADOT Python Lambda Layer ARN to use in aws-us-gov partitions. Publish once per GovCloud region and paste the ARN here."

  # Fail fast if deploying to GovCloud without providing the layer ARN
  validation {
    condition     = var.adot_python_layer_arn_govcloud == "" || can(regex("^arn:aws-us-gov:lambda:[a-z0-9-]+:\\d{12}:layer:[A-Za-z0-9._-]+:\\d+$", var.adot_python_layer_arn_govcloud))
    error_message = "GovCloud detected (aws-us-gov) but 'adot_python_layer_arn_govcloud' is empty. Publish your ADOT layer in this region and set its ARN."
  }
}

variable "create_vpc_endpoints" {
  type        = bool
  default     = true
  description = "Whether to create interface VPC endpoints for X-Ray and CloudWatch Logs."
}


# ---- Network ids pulled from SSM (you already pass these in tfvars) ----
locals {
  is_gov = var.aws_partition == "aws-us-gov"

  # Use DMZ resources in commercial-DMZ, otherwise (GovCloud+endpoints) use SSM, else null
  vpc_id   = var.is_dmz ? aws_vpc.crossfeed_vpc[0].id : (local.is_gov && var.create_vpc_endpoints ? data.aws_ssm_parameter.vpc_id[0].value : null)
  vpc_cidr = var.is_dmz ? aws_vpc.crossfeed_vpc[0].cidr_block : (local.is_gov && var.create_vpc_endpoints ? data.aws_ssm_parameter.vpc_cidr_block[0].value : null)

  subnets_ep = var.is_dmz ? [aws_subnet.backend[0].id, aws_subnet.worker[0].id, aws_subnet.matomo_1[0].id] : (local.is_gov && var.create_vpc_endpoints ? compact([
    data.aws_ssm_parameter.subnet_backend_id[0].value,
    data.aws_ssm_parameter.subnet_worker_id[0].value,
    data.aws_ssm_parameter.subnet_matomo_id[0].value
    ])
    : []
  )

  adot_python_layer_arn_resolved = local.is_gov ? var.adot_python_layer_arn_govcloud : ""
}

resource "aws_security_group" "telemetry_endpoints_sg" {
  count  = (local.vpc_id != null && length(local.subnets_ep) > 0) ? 1 : 0
  name   = "crossfeed-${var.stage}-telemetry-endpoints"
  vpc_id = local.vpc_id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.is_dmz ? aws_vpc.crossfeed_vpc[0].cidr_block : data.aws_ssm_parameter.vpc_cidr_block[0].value]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.is_dmz ? aws_vpc.crossfeed_vpc[0].cidr_block : data.aws_ssm_parameter.vpc_cidr_block[0].value]
  }

  tags = { Project = var.project, Stage = var.stage, Owner = "Crossfeed managed resource" }
}


# ---- Interface VPC Endpoints (toggle via create_vpc_endpoints) ----
# X-Ray endpoint service name: com.amazonaws.${region}.xray
resource "aws_vpc_endpoint" "xray" {
  count               = (local.vpc_id != null && length(local.subnets_ep) > 0) ? 1 : 0
  vpc_id              = var.is_dmz ? aws_vpc.crossfeed_vpc[0].id : data.aws_ssm_parameter.vpc_id[0].value
  service_name        = "com.amazonaws.${var.aws_region}.xray"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  subnet_ids          = local.subnets_ep
  security_group_ids  = [aws_security_group.telemetry_endpoints_sg[0].id]
  tags                = { Project = var.project, Stage = var.stage, Owner = "Crossfeed managed resource" }
}

# CloudWatch Logs endpoint service name: com.amazonaws.${region}.logs
resource "aws_vpc_endpoint" "logs" {
  count               = (local.vpc_id != null && length(local.subnets_ep) > 0) ? 1 : 0
  vpc_id              = var.is_dmz ? aws_vpc.crossfeed_vpc[0].id : data.aws_ssm_parameter.vpc_id[0].value
  service_name        = "com.amazonaws.${var.aws_region}.logs"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  subnet_ids          = local.subnets_ep
  security_group_ids  = [aws_security_group.telemetry_endpoints_sg[0].id]
  tags                = { Project = var.project, Stage = var.stage, Owner = "Crossfeed managed resource" }
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
