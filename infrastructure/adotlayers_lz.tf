# --- ADOT Python layer (GovCloud only) ---
resource "aws_lambda_layer_version" "adot_python" {
  count               = local.is_gov ? 1 : 0
  layer_name          = "crossfeed-adot-python"
  description         = "Crossfeed ADOT Python layer with collector (GovCloud)"
  filename            = "${path.module}/aws_resources/adot-python-with-collector.zip"
  compatible_runtimes = ["python3.10", "python3.9"]
  license_info        = "Apache-2.0"
  source_code_hash    = filebase64sha256("${path.module}/aws_resources/adot-python-with-collector.zip")
}

resource "aws_lambda_layer_version" "adot_node" {
  count               = local.is_gov ? 1 : 0
  layer_name          = "crossfeed-adot-node"
  description         = "Crossfeed ADOT Node layer (GovCloud)"
  filename            = "${path.module}/aws_resources/adot-nodejs.zip"
  compatible_runtimes = ["nodejs18.x"]
  license_info        = "Apache-2.0"
  source_code_hash    = filebase64sha256("${path.module}/aws_resources/adot-nodejs.zip")
}

# Write the Python layer ARN to SSM so serverless.yml can read it:
#   us-gov-*-1: ${ssm:/crossfeed/${self:provider.stage}/adot_python_layer_arn, ''}
resource "aws_ssm_parameter" "adot_python_layer_arn" {
  count = local.is_gov ? 1 : 0

  name  = "/crossfeed/${var.stage}/adot_python_layer_arn"
  type  = "String"
  value = aws_lambda_layer_version.adot_python[0].arn

  overwrite = true
}


output "adot_node_layer_arn" {
  value       = local.is_gov && length(aws_lambda_layer_version.adot_node) > 0 ? aws_lambda_layer_version.adot_node[0].arn : ""
  description = "ADOT Node layer ARN (GovCloud only)"
}
