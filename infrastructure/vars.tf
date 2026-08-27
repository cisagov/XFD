variable "aws_region" {
  description = "aws_region"
  type        = string
  default     = "us-east-1"
}

variable "aws_other_region" {
  description = "aws_other_region"
  type        = string
  default     = "us-east-1"
}

variable "aws_partition" {
  description = "aws_partition"
  type        = string
  default     = "aws"
}

variable "is_dmz" {
  description = "is_dmz"
  type        = bool
  default     = false
}

variable "project" {
  description = "project"
  type        = string
  default     = "Crossfeed"
}

variable "stage" {
  description = "stage"
  type        = string
  default     = "staging"
}

variable "db_port" {
  description = "db_port"
  type        = number
  default     = 5432
}

variable "db_name" {
  description = "db_name"
  type        = string
  default     = "crossfeed-stage-db"
}

variable "db_instance_class" {
  description = "db_instance_class"
  type        = string
  default     = "db.t3.micro"
}

variable "api_domain" {
  description = "api_domain"
  type        = string
  default     = "api.staging.crossfeed.cyber.dhs.gov"
}

variable "frontend_domain" {
  description = "frontend_domain"
  type        = string
  default     = "staging.crossfeed.cyber.dhs.gov"
}

variable "frontend_bucket" {
  description = "frontend_bucket"
  type        = string
  default     = "staging.crossfeed.cyber.dhs.gov"
}

variable "frontend_lambda_function" {
  description = "frontend_lambda_function"
  type        = string
  default     = "crossfeed-security-headers-staging"
}

variable "log_metric_namespace" {
  description = "log_metric_namespace"
  type        = string
  default     = "LogMetrics"
}

variable "log_metric_api_error_rate" {
  description = "log_metric_filter_api_error_rate"
  type        = string
  default     = "crossfeed-staging-APIErrorRate"
}

variable "log_metric_root_user" {
  description = "log_metric_filter_root_user"
  type        = string
  default     = "crossfeed-staging-RootUserAccess"
}

variable "log_metric_unauthorized_api_call" {
  description = "log_metric_filter_unauthorized_api_call"
  type        = string
  default     = "crossfeed-staging-UnauthorizedAPICall"
}

variable "log_metric_login_without_mfa" {
  description = "log_metric_filter_login_without_mfa"
  type        = string
  default     = "crossfeed-staging-ConsoleLoginWithoutMFA"
}

variable "log_metric_iam_policy" {
  description = "log_metric_filter_iam_policy"
  type        = string
  default     = "crossfeed-staging-IAMPolicyChange"
}

variable "log_metric_cloudtrail" {
  description = "log_metric_filter_cloudtrail"
  type        = string
  default     = "crossfeed-staging-CloudTrailConfigurationChange"
}

variable "log_metric_login_failure" {
  description = "log_metric_filter_login_failure"
  type        = string
  default     = "crossfeed-staging-ConsoleLoginFailure"
}

variable "log_metric_cmk_delete_disable" {
  description = "log_metric_filter_cmk_delete_disable"
  type        = string
  default     = "crossfeed-staging-DisablingOrScheduledDeletionOfCMK"
}

variable "log_metric_s3_bucket_policy" {
  description = "log_metric_filter_s3_bucket_policy"
  type        = string
  default     = "crossfeed-staging-S3BucketPolicyChange"
}

variable "log_metric_aws_config" {
  description = "log_metric_filter_aws_config"
  type        = string
  default     = "crossfeed-staging-AWSConfigConfigurationChange"
}

variable "log_metric_security_group" {
  description = "log_metric_filter_security_group"
  type        = string
  default     = "crossfeed-staging-SecurityGroupChange"
}

variable "log_metric_nacl" {
  description = "log_metric_filter_nacl"
  type        = string
  default     = "crossfeed-staging-NACLChange"
}

variable "log_metric_network_gateway" {
  description = "log_metric_filter_network_gateway"
  type        = string
  default     = "crossfeed-staging-NetworkGatewayChange"
}

variable "log_metric_route_table" {
  description = "log_metric_filter_route_table"
  type        = string
  default     = "crossfeed-staging-RouteTableChange"
}

variable "log_metric_vpc" {
  description = "log_metric_filter_vpc"
  type        = string
  default     = "crossfeed-staging-VPCChange"
}

variable "log_metric_ec2_shutdown" {
  description = "log_metric_filter_ec2_shutdown"
  type        = string
  default     = "crossfeed-staging-EC2Shutdown"
}

variable "log_metric_db_shutdown" {
  description = "log_metric_filter_DB_shutdown"
  type        = string
  default     = "crossfeed-staging-DBShutdown"
}

variable "log_metric_db_deletion" {
  description = "log_metric_filter_db_deletion"
  type        = string
  default     = "crossfeed-staging-DBDeletion"
}

variable "matomo_force_index_url" {
  description = "Public URL for Matomo dashboard; should match {frontend_domain}/matomo"
  type        = string
  default     = "staging.crossfeed.cyber.dhs.gov/matomo"
}

variable "sns_topic_alarms" {
  description = "sns_alarm_topic_name"
  type        = string
  default     = "crossfeed-staging-cis-alarms"
}

variable "ssm_db_name" {
  description = "ssm_db_name"
  type        = string
  default     = "/crossfeed/staging/DATABASE_NAME"
}

variable "ssm_db_host" {
  description = "ssm_db_host"
  type        = string
  default     = "/crossfeed/staging/DATABASE_HOST"
}

variable "ssm_pe_db_name" {
  description = "ssm_pe_db_name"
  type        = string
  default     = "/crossfeed/staging/PE_DB_NAME"
}

variable "ssm_pe_db_username" {
  description = "ssm_pe_db_username"
  type        = string
  default     = "/crossfeed/staging/PE_DB_USERNAME"
}

variable "ssm_pe_db_password" {
  description = "ssm_pe_db_password"
  type        = string
  default     = "/crossfeed/staging/PE_DB_PASSWORD"
}

variable "ssm_pe_db_password_key" {
  description = "SSM path to the pgcrypto symmetric passphrase used by PGP_SYM_DECRYPT to decrypt the organizations.password column (pe_reports.data.config.db_password_key / pe_mailer's per-org report password lookup). Distinct from ssm_pe_db_password (the Postgres auth password) -- this key must exactly match whatever value originally encrypted those rows, since it can't be safely rotated or regenerated."
  type        = string
  default     = "/crossfeed/staging/PE_DB_PASSWORD_KEY"
}

variable "ssm_crossfeed_vpc_name" {
  description = "ssm_crossfeed_vpc_name"
  type        = string
  default     = "/crossfeed/staging/VPC_NAME"
}

variable "ssm_lambda_sg" {
  description = "ssm_lambda_sg"
  type        = string
  default     = "/crossfeed/staging/SG_ID"
}

variable "ssm_lambda_subnet" {
  description = "ssm_lambda_subnet"
  type        = string
  default     = "/crossfeed/staging/SUBNET_ID"
}

variable "ssm_worker_sg" {
  description = "ssm_worker_sg"
  type        = string
  default     = "/crossfeed/staging/WORKER_SG_ID"
}

variable "ssm_worker_subnet" {
  description = "ssm_worker_subnet"
  type        = string
  default     = "/crossfeed/staging/WORKER_SUBNET_ID"
}

variable "ssm_worker_arn" {
  description = "ssm_worker_arn"
  type        = string
  default     = "/crossfeed/staging/WORKER_CLUSTER_ARN"
}

variable "db_table_name" {
  description = "db_table_name"
  type        = string
  default     = "cfstagedb"
}

variable "ssm_db_username" {
  description = "ssm_db_username"
  type        = string
  default     = "/crossfeed/staging/DATABASE_USER"
}

variable "ssm_db_password" {
  description = "ssm_db_password"
  type        = string
  default     = "/crossfeed/staging/DATABASE_PASSWORD"
}

variable "ssm_matomo_db_password" {
  description = "ssm_matomo_db_password"
  type        = string
  default     = "/crossfeed/staging/MATOMO_DATABASE_PASSWORD"
}

variable "ssm_worker_signature_public_key" {
  description = "ssm_worker_signature_public_key"
  type        = string
  default     = "/crossfeed/staging/WORKER_SIGNATURE_PUBLIC_KEY"
}

variable "ssm_worker_signature_private_key" {
  description = "ssm_worker_signature_private_key"
  type        = string
  default     = "/crossfeed/staging/WORKER_SIGNATURE_PRIVATE_KEY"
}

variable "ssm_censys_api_id" {
  description = "ssm_censys_api_id"
  type        = string
  default     = "/crossfeed/staging/CENSYS_API_ID"
}

variable "ssm_censys_api_secret" {
  description = "ssm_censys_api_secret"
  type        = string
  default     = "/crossfeed/staging/CENSYS_API_SECRET"
}

variable "ssm_shodan_api_key" {
  description = "ssm_shodan_api_key"
  type        = string
  default     = "/crossfeed/staging/SHODAN_API_KEY"
}

variable "ssm_shodan_ip_chunk_size" {
  description = "ssm_shodan_ip_chunk_size"
  type        = string
  default     = "/crossfeed/staging/SHODAN_IP_CHUNK_SIZE"
}

variable "ssm_shodan_query_days_back" {
  description = "ssm_shodan_query_days_back"
  type        = string
  default     = "/crossfeed/staging/SHODAN_QUERY_DAYS_BACK"
}

variable "ssm_pe_shodan_api_keys" {
  description = "ssm_pe_shodan_api_keys"
  type        = string
  default     = "/crossfeed/staging/PE_SHODAN_API_KEYS"
}

variable "ssm_wiz_registry_secret_arn" {
  description = "ssm_wiz_registry_secret_arn"
  type        = string
  default     = "/crossfeed/staging/WIZ_REGISTRY_CREDENTIAL_SECRET_ARN"
}

variable "ssm_wiz_service_account_secret_arn" {
  description = "ssm_wiz_service_account_secret_arn"
  type        = string
  default     = "/crossfeed/staging/WIZ_SERVICE_ACCOUNT_SECRET_ARN"
}

variable "ssm_wiz_http_proxy_cert_secret_arn" {
  description = "ssm_wiz_http_proxy_cert_secret_arn"
  type        = string
  default     = "/crossfeed/staging/WIZ_HTTP_PROXY_CERT_SECRET_ARN"
}

variable "ssm_sixgill_client_id" {
  description = "ssm_sixgill_client_id"
  type        = string
  default     = "/crossfeed/staging/SIXGILL_CLIENT_ID"
}

variable "ssm_sixgill_client_secret" {
  description = "ssm_sixgill_client_secret"
  type        = string
  default     = "/crossfeed/staging/SIXGILL_CLIENT_SECRET"
}

variable "ssm_intelx_api_key" {
  description = "ssm_intelx_api_key"
  type        = string
  default     = "/crossfeed/staging/INTELX_API_KEY"
}

variable "ssm_checksum_salt" {
  description = "ssm_checksum_salt"
  type        = string
  default     = "/crossfeed/staging/CHECKSUM_SALT"
}

variable "ssm_xpanse_api_key" {
  description = "ssm_xpanse_api_key"
  type        = string
  default     = "/crossfeed/staging/XPANSE_API_KEY"
}

variable "ssm_whoisxml_api_key" {
  description = "ssm_whoisxml_api_key"
  type        = string
  default     = "/crossfeed/staging/WHOIS_XML_KEY"
}

variable "ssm_whoisxml_thread_count" {
  description = "ssm_whoisxml_thread_count"
  type        = string
  default     = "/crossfeed/staging/WHOIS_XML_THREAD_COUNT"
}

variable "ssm_qualys_username" {
  description = "ssm_qualys_username"
  type        = string
  default     = "/crossfeed/staging/QUALYS_USERNAME"
}

variable "ssm_qualys_password" {
  description = "ssm_qualys_password"
  type        = string
  default     = "/crossfeed/staging/QUALYS_PASSWORD"
}

variable "ssm_xpanse_auth_id" {
  description = "ssm_xpanse_auth_id"
  type        = string
  default     = "/crossfeed/staging/XPANSE_AUTH_ID"
}

variable "ssm_nist_api_key" {
  description = "ssm_nist_api_key"
  type        = string
  default     = "/crossfeed/staging/NIST_API_KEY"
}

variable "ssm_lg_api_key" {
  description = "ssm_lg_api_key"
  type        = string
  default     = "/crossfeed/staging/LG_API_KEY"
}

variable "ssm_lg_workspace_name" {
  description = "ssm_lg_workspace_name"
  type        = string
  default     = "/crossfeed/staging/LG_WORKSPACE_NAME"
}

variable "db_group_name" {
  description = "db_group_name"
  type        = string
  default     = "crossfeed-db-group"
}

variable "worker_ecs_repository_name" {
  description = "worker_ecs_repository_name"
  type        = string
  default     = "crossfeed-worker-staging"
}

variable "worker_ecs_cluster_name" {
  description = "worker_ecs_cluster_name"
  type        = string
  default     = "crossfeed-worker-staging"
}

variable "worker_ecs_task_definition_family" {
  description = "worker_ecs_task_definition_family"
  type        = string
  default     = "crossfeed-worker-staging"
}

variable "worker_ecs_log_group_name" {
  description = "worker_ecs_log_group_name"
  type        = string
  default     = "crossfeed-worker-staging"
}

variable "worker_ecs_role_name" {
  description = "worker_ecs_role_name"
  type        = string
  default     = "crossfeed-worker-staging"
}

variable "logging_bucket_name" {
  description = "logging_bucket_name"
  type        = string
  default     = "cisa-crossfeed-staging-logging"
}

variable "export_bucket_name" {
  description = "export_bucket_name"
  type        = string
  default     = "cisa-crossfeed-staging-exports"
}

variable "reports_bucket_name" {
  description = "reports_bucket_name"
  type        = string
  default     = "cisa-crossfeed-reports"
}

variable "pe_db_backups_bucket_name" {
  description = "pe_db_backups_bucket_name"
  type        = string
  default     = "cisa-crossfeed-pe-db-backups"
}

variable "user_pool_name" {
  description = "user_pool_name"
  type        = string
  default     = "crossfeed-staging"
}

variable "user_pool_domain" {
  description = "user_pool_domain"
  type        = string
  default     = "crossfeed-staging"
}

variable "ssm_user_pool_id" {
  description = "ssm_user_pool_id"
  type        = string
  default     = "/crossfeed/staging/USER_POOL_ID"
}

variable "ssm_user_pool_client_id" {
  description = "ssm_user_pool_client_id"
  type        = string
  default     = "/crossfeed/staging/USER_POOL_CLIENT_ID"
}

variable "ses_support_email_sender" {
  type        = string
  description = "Email address from which SES emails are sent"
  default     = "noreply@staging.crossfeed.cyber.dhs.gov"
}

variable "ses_support_email_replyto" {
  type        = string
  description = "Email address set in the Reply-To header for SES emails"
  default     = "support@staging.crossfeed.cyber.dhs.gov"
}

variable "matomo_ecs_cluster_name" {
  description = "matomo_ecs_cluster_name"
  type        = string
  default     = "crossfeed-matomo-staging"
}

variable "matomo_ecs_task_definition_family" {
  description = "matomo_ecs_task_definition_family"
  type        = string
  default     = "crossfeed-matomo-staging"
}

variable "matomo_ecs_log_group_name" {
  description = "matomo_ecs_log_group_name"
  type        = string
  default     = "crossfeed-matomo-staging"
}

variable "matomo_db_name" {
  description = "matomo_db_name"
  type        = string
  default     = "crossfeed-matomo-staging"
}

variable "matomo_db_instance_class" {
  description = "matomo_db_instance_class"
  type        = string
  default     = "db.t3.micro"
}

variable "matomo_ecs_role_name" {
  description = "matomo_ecs_role_name"
  type        = string
  default     = "crossfeed-matomo-staging"
}

variable "es_instance_type" {
  description = "es_instance_type"
  type        = string
  default     = "t2.micro.elasticsearch"
}

variable "es_instance_count" {
  description = "es_instance_count"
  type        = number
  default     = 1
}

variable "es_instance_volume_size" {
  description = "es_instance_volume_size"
  type        = number
  default     = 100
}

variable "create_db_accessor_instance" {
  description = "Whether to create a DB accessor instance. This instance can be used to access RDS and is spun up in a private subnet. It can be accessed using AWS Systems Manager Session Manager."
  type        = bool
  default     = false
}

variable "create_pe_instance" {
  description = "Whether to create a PE EC2 instance. This instance can be used to access RDS and is spun up in a private subnet. It can be accessed using AWS Systems Manager Session Manager."
  type        = bool
  default     = false
}


variable "create_email_sender_instance" {
  description = "Whether to create a email sending EC2 instance. This instance can be used to access AWS SES and is spun up in a private subnet. It can be accessed using AWS Systems Manager Session Manager."
  type        = bool
  default     = false
}

variable "email_sender_instance_type" {
  description = "Instance type of the email sender instance."
  type        = string
  default     = false
}

variable "create_open_cti_instance" {
  description = "Whether to manage the existing OpenCTI EC2 instance in Terraform. This instance already exists (created out-of-band) running OpenCTI via Docker Compose -- this flag must only be true in the environment where that live instance actually resides, since the resource is imported, not freshly created."
  type        = bool
  default     = false
}

variable "open_cti_instance_id" {
  description = "Instance ID of the existing OpenCTI EC2 instance (used for the one-time `terraform import`, and for reference)."
  type        = string
  default     = "i-033771e2a6a9a26ca"
}

variable "open_cti_ami_id" {
  description = "AMI ID of the existing, already-running stage-cd (is_dmz) OpenCTI EC2 instance -- must match reality, since that instance is adopted rather than created. Commercial-partition only: it does not exist in gov-cloud, so LZ (!is_dmz) instances use var.lz_open_cti_ami_id instead -- see aws_instance.open_cti's `ami` ternary in open_cti.tf."
  type        = string
  default     = "ami-0fb0b230890ccd1e6"
}

variable "lz_open_cti_ami_id" {
  description = "AMI ID for a genuinely new OpenCTI EC2 instance in the gov-cloud Landing Zone (!is_dmz, e.g. stage/prod) -- this instance is created fresh, not adopted, so unlike var.open_cti_ami_id this doesn't need to match an already-running box. Gov-cloud-partition only: var.open_cti_ami_id's commercial AMI ID does not exist here -- see aws_instance.open_cti's `ami` ternary in open_cti.tf. NOT independently verified against real aws-us-gov credentials as of 2026-08-20 -- see open-cti/STATUS.md's AMI section."
  type        = string
  default     = "ami-035b0309a54bd5b23"
}

variable "open_cti_instance_type" {
  description = "Instance type of the existing OpenCTI EC2 instance. Must be set to the real value (see `aws ec2 describe-instances --instance-ids <id>`) before running `terraform plan` -- an incorrect value here will show as a replace diff."
  type        = string
  default     = ""
}

variable "open_cti_root_volume_size" {
  description = "Root volume size (GiB) of the existing OpenCTI EC2 instance's single EBS volume, which also hosts all Docker data (no separate data volume exists today). Must match the real volume size."
  type        = number
  default     = 1000
}

variable "open_cti_subnet_id" {
  description = "Subnet ID the existing OpenCTI EC2 instance is in."
  type        = string
  default     = "subnet-0b1b2c61141354e25"
}

variable "open_cti_security_group_id" {
  description = "Existing security group ID attached to the OpenCTI EC2 instance. Referenced read-only via a data source (not managed as a Terraform resource) since its origin/ownership predates this config and is unverified."
  type        = string
  default     = "sg-0947bc9960c82a0b2"
}

variable "open_cti_ssm_path_prefix" {
  description = "SSM Parameter Store path prefix for OpenCTI/XTM One secrets. Deliberately its own hierarchical path segment (/crossfeed/staging/opencti/<KEY>) rather than the flat /crossfeed/<env>/<KEY> convention used elsewhere (e.g. ssm_matomo_db_password) -- OpenCTI's docker-compose.yml reuses generic var names (SHODAN_API_KEY, CENSYS_API_KEY, etc.) that would otherwise collide with Crossfeed's own existing ssm_shodan_api_key/ssm_censys_api_id parameters, which already occupy the flat namespace. staging-cd shares the staging namespace, same as other Crossfeed secrets in this repo."
  type        = string
  default     = "/crossfeed/staging/opencti"
}

variable "open_cti_secret_keys" {
  description = "Names (suffix only, appended to open_cti_ssm_path_prefix) of OpenCTI/XTM One secrets that must exist in SSM Parameter Store as SecureString placeholders. Real values already exist only in the live instance's .env and are set here once, out-of-band, via `aws ssm put-parameter --overwrite` -- Terraform creates the parameter shells but never generates or overwrites the real values, since these secrets can't be safely regenerated (e.g. rotating the encryption key breaks decryption of existing data)."
  type        = set(string)
  default = [
    "CENSYS_API_KEY",
    "CONNECTOR_CENSYS_API_KEY",
    "CONNECTOR_CISA_KEV_API_KEY",
    "CONNECTOR_CVE_API_KEY",
    "CONNECTOR_QUALYS_CVE_ENRICHMENT_API_KEY",
    "CONNECTOR_SHODAN_API_KEY",
    "CONNECTOR_VULNCHECK_API_KEY",
    "MINIO_ROOT_PASSWORD",
    "NVD_API_KEY",
    "OPENCTI_ADMIN_PASSWORD",
    "OPENCTI_ADMIN_TOKEN",
    "OPENCTI_ENCRYPTION_KEY",
    "OPENCTI_HEALTHCHECK_ACCESS_KEY",
    "PLATFORM_REGISTRATION_TOKEN",
    "QUALYS_API_PASSWORD",
    "RABBITMQ_DEFAULT_PASS",
    "SHODAN_API_KEY",
    "VULNCHECK_API_KEY",
    "XTM_ONE_ADMIN_PASSWORD",
    "XTM_ONE_ENTERPRISE_LICENSE",
    "XTM_ONE_POSTGRES_PASSWORD",
    "XTM_ONE_SECRET_KEY",
    # Found by diffing stage-cd's real .env against this list on 2026-08-17 --
    # none of these three were tracked here before.
    "MINIO_ROOT_USER",                   # confirmed live: a UUID, not a plain username -- credential-grade, paired with MINIO_ROOT_PASSWORD as effectively access_key+secret_key
    "OPENSEARCH_ADMIN_PASSWORD",         # confirmed live, but docker-compose.yml's elasticsearch service has xpack.security.enabled=false -- unclear if this is actually consumed or vestigial from a different compose config
    "CONNECTOR_CENSYS_ENRICHMENT_TOKEN", # confirmed live (still literally "NEED_TO_SET" there) -- not referenced anywhere in docker-compose.yml today, likely stale/vestigial
  ]
}

variable "open_cti_host" {
  description = "Per-environment, non-secret hostname OpenCTI is reached at (OPENCTI_HOST in open-cti/.env.example). Baked into env.deploy by open_cti.tf's user_data -- see open-cti/bootstrap.sh. Must be set to the real value in each environment's .tfvars before create_open_cti_instance is turned on there; the empty default is intentionally invalid so an unset value fails loudly (an empty OPENCTI_HOST breaks APP__BASE_URL) rather than silently deploying broken config."
  type        = string
  default     = ""
}

variable "open_cti_admin_email" {
  description = "Per-environment, non-secret OpenCTI admin account email (OPENCTI_ADMIN_EMAIL). See open_cti_host for how/when this is used."
  type        = string
  default     = ""
}

variable "open_cti_smtp_hostname" {
  description = "Per-environment, non-secret SMTP relay hostname OpenCTI sends mail through (SMTP_HOSTNAME). See open_cti_host for how/when this is used."
  type        = string
  default     = ""
}

variable "open_cti_censys_org_id" {
  description = "Per-environment, non-secret Censys organization ID (CENSYS_ORG_ID) -- not a credential, just an account identifier, which is why it's not in open_cti_secret_keys/SSM. See open_cti_host for how/when this is used."
  type        = string
  default     = ""
}

variable "open_cti_qualys_api_username" {
  description = "Per-environment, non-secret Qualys API username (QUALYS_API_USERNAME) -- the paired QUALYS_API_PASSWORD is a real secret and stays in SSM (open_cti_secret_keys); the username alone is not. See open_cti_host for how/when this is used."
  type        = string
  default     = ""
}

variable "open_cti_xtm_one_host" {
  description = "Per-environment, non-secret hostname XTM One is reached at (XTM_ONE_HOST). Unlike open_cti_host and its siblings, bootstrap.sh does NOT fail closed on this being empty -- confirmed on 2026-08-17 that XTM One isn't actually active on stage-cd, so an empty value here is the expected/normal case, not a misconfiguration. Set it for real once XTM One is actually turned on for a given environment."
  type        = string
  default     = ""
}

variable "open_cti_xtm_one_admin_email" {
  description = "Per-environment, non-secret XTM One admin account email (XTM_ONE_ADMIN_EMAIL). See open_cti_xtm_one_host -- same optional-until-XTM-One-is-active treatment."
  type        = string
  default     = ""
}

variable "open_cti_repo_url" {
  description = "Git URL open-cti/refresh-repo.sh clones/pulls from on every boot -- the source of truth for bootstrap.sh, env.static, docker-compose.yml, rabbitmq.conf, and both systemd units, none of which are embedded in user_data or delivered via S3 anymore (see open_cti.tf's header comment on that decision). Defaults to this repo's current public URL, which needs no credentials. When this repo moves to the enterprise remote (already configured locally as `enterprise` -- https://github.com/cisa-vulnerability-management/asm-xfd.git) and stops being publicly cloneable, this needs to change AND refresh-repo.sh needs real git auth added -- see open-cti/STATUS.md for that plan."
  type        = string
  default     = "https://github.com/cisagov/XFD.git"
}

variable "open_cti_repo_branch" {
  description = "Branch open-cti/refresh-repo.sh tracks -- a merge here reaches every instance's next boot, no CI push and no terraform apply required."
  type        = string
  default     = "develop"
}

variable "open_cti_db_username" {
  description = "Dedicated Postgres role OpenCTI connects to the Crossfeed RDS DB as, via IAM database authentication (rds-db:connect) -- see aws_iam_role_policy.open_cti_rds_iam_auth in open_cti.tf. Deliberately separate from var.db_username (the worker/backend's own role), for least privilege. NOT Terraform-managed: this role, and the one-time `GRANT rds_iam TO <role>` it needs, must be created in Postgres itself, out-of-band -- there's no postgresql provider in this repo. Only used in the LZ (!is_dmz) branch; stage-cd has no DB connectivity of this kind."
  type        = string
  default     = "open_cti"
}

variable "db_accessor_instance_class" {
  description = "db_accessor_instance_class"
  type        = string
  default     = "t3.micro"
}

variable "elk_instance_class" {
  description = "elk_instance_class"
  type        = string
  default     = "t3.micro"
}

variable "create_elk_instance" {
  description = "Whether to create a ELK instance. This instance can be used to run a ELK cluseter. It can be accessed using AWS Systems Manager Session Manager."
  type        = bool
  default     = false
}

variable "severity_critical" {
  description = "severity_critical"
  type        = string
  default     = "CRITICAL"
}

variable "severity_high" {
  description = "severity_high"
  type        = string
  default     = "HIGH"
}

variable "severity_medium" {
  description = "severity_medium"
  type        = string
  default     = "MEDIUM"
}

variable "severity_low" {
  description = "severity_low"
  type        = string
  default     = "LOW"
}

variable "ami_id" {
  description = "ID of the AMI to use for EC2 instances."
  type        = string
  default     = "ami-0a1445a13e666a557"
}

variable "create_was_reporting_instance" {
  description = "Whether to create or manage the WAS reporting EC2 instance."
  type        = bool
  default     = false
}

variable "was_reporting_ami_id" {
  description = "AMI ID for the WAS reporting EC2 instance in the DMZ environment. Initially matches the OpenCTI DMZ AMI but can evolve independently."
  type        = string
  default     = "ami-0fb0b230890ccd1e6"
}

variable "was_reporting_instance_type" {
  description = "EC2 instance type for the WAS reporting instance. Initially matches the P&E EC2 instance but can evolve independently."
  type        = string
  default     = "m5.4xlarge"
}

variable "was_reporting_root_volume_size" {
  description = "Size in GiB of the encrypted WAS reporting root volume."
  type        = number
  default     = 50

  validation {
    condition     = var.was_reporting_root_volume_size > 0
    error_message = "The WAS reporting root volume size must be greater than zero."
  }
}

variable "was_reporting_root_volume_type" {
  description = "EBS volume type for the WAS reporting root volume."
  type        = string
  default     = "gp3"
}

variable "was_reporting_subnet_id" {
  description = "ID of the existing DMZ subnet for WAS reporting. Initially matches the P&E EC2 subnet but can evolve independently."
  type        = string
  default     = "subnet-0b1b2c61141354e25"
}

variable "was_reporting_security_group_id" {
  description = "ID of the existing DMZ security group for WAS reporting. Initially matches the P&E EC2 security group but can evolve independently."
  type        = string
  default     = "sg-0947bc9960c82a0b2"
}

variable "cloudtrail_name" {
  description = "cloudtrail_name"
  type        = string
  default     = "crossfeed-staging-all-events"
}

variable "cloudtrail_bucket_name" {
  description = "cloudtrail_bucket_name"
  type        = string
  default     = "cisa-crossfeed-staging-cloudtrail"
}

variable "cloudtrail_role_name" {
  description = "cloudtrail_role_name"
  type        = string
  default     = "crossfeed-staging-cloudtrail-role"
}

variable "cloudtrail_log_group_name" {
  description = "cloudtrail_log_group_name"
  type        = string
  default     = "crossfeed-staging-cloudtrail-logs"
}

variable "es_instance_master_count" {
  description = "es_instance_master_count"
  type        = number
  default     = 3
}

variable "ssm_vpc_id" {
  description = "ssm_vpc_id"
  type        = string
  default     = "/LZ/VPC_ID"
}

variable "ssm_vpc_cidr_block" {
  description = "ssm_vpc_cidr_block"
  type        = string
  default     = "/LZ/VPC_CIDR_BLOCK"
}

variable "ssm_sctask_cidr_block" {
  description = "ssm_sctask_cidr_block"
  type        = string
  default     = "/LZ/SCTASK_CIDR_BLOCK"
}

variable "ssm_route_table_endpoints_id" {
  description = "ssm_route_table_endpoints_id"
  type        = string
  default     = ""
}
variable "ssm_route_table_private_A_id" {
  description = "ssm_route_table_private_A_id"
  type        = string
  default     = ""
}
variable "ssm_route_table_private_B_id" {
  description = "ssm_route_table_private_B_id"
  type        = string
  default     = ""
}

variable "ssm_route_table_private_C_id" {
  description = "ssm_route_table_private_C_id"
  type        = string
  default     = ""
}

variable "ssm_subnet_backend_id" {
  description = "ssm_subnet_backend_id"
  type        = string
  default     = ""
}

variable "ssm_subnet_worker_id" {
  description = "ssm_subnet_worker_id"
  type        = string
  default     = ""
}

variable "ssm_subnet_matomo_id" {
  description = "ssm_subnet_matomo_id"
  type        = string
  default     = ""
}

variable "ssm_subnet_db_1_id" {
  description = "ssm_subnet_db_1_id"
  type        = string
  default     = ""
}

variable "ssm_subnet_db_2_id" {
  description = "ssm_subnet_db_2_id"
  type        = string
  default     = ""
}

variable "ssm_subnet_es_id" {
  description = "ssm_subnet_es_id"
  type        = string
  default     = ""
}

variable "ssm_ses_email_identity_arn" {
  description = "ssm_ses_email_identity_arn"
  type        = string
  default     = "/crossfeed/staging/SES_EMAIL_IDENTITY_ARN"
}

variable "ssm_worker_kms_keys" {
  description = "ssm_worker_kms_keys"
  type        = string
  default     = "/crossfeed/staging/WORKER_KMS_KEYS"
}

variable "ssm_pe_api_key" {
  description = "ssm_pe_api_key"
  type        = string
  default     = "/crossfeed/staging/PE_API_KEY"
}

variable "ssm_pe_api_url" {
  description = "ssm_pe_api_url"
  type        = string
  default     = "/crossfeed/staging/PE_API_URL"
}

variable "ssm_mailer_arn" {
  description = "SSM parameter holding the IAM role ARN that pe-mailer (email_reports.py) assumes to send via SES"
  type        = string
  default     = "/crossfeed/staging/MAILER_ARN"
}

variable "ssm_cf_api_key" {
  description = "ssm_cf_api_key"
  type        = string
  default     = "/crossfeed/staging/CF_API_KEY"
}

variable "cloudwatch_bucket_name" {
  description = "cloudwatch_bucket_name"
  type        = string
  default     = "cisa-crossfeed-staging-cloudwatch"
}

variable "cloudwatch_log_group_name" {
  description = "cloudwatch_log_group_name"
  type        = string
  default     = "crossfeed-staging-cloudwatch-bucket"
}

variable "pe_worker_ecs_repository_name" {
  description = "pe_worker_ecs_repository_name"
  type        = string
  default     = "pe-staging-worker"
}

variable "pe_worker_ecs_cluster_name" {
  description = "pe_worker_ecs_cluster_name"
  type        = string
  default     = "pe-staging-worker"
}

variable "pe_worker_ecs_task_definition_family" {
  description = "pe_worker_ecs_task_definition_family"
  type        = string
  default     = "pe-staging-worker"
}

variable "pe_worker_ecs_log_group_name" {
  description = "pe_worker_ecs_log_group_name"
  type        = string
  default     = "pe-staging-worker"
}

variable "pe_worker_ecs_role_name" {
  description = "pe_worker_ecs_role_name"
  type        = string
  default     = "pe-staging-worker"
}

variable "matomo_availability_zone" {
  description = "matomo_availability_zone"
  type        = string
  default     = "us-east-1"

}
variable "ssm_mdl_name" {
  description = "ssm_mdl_name"
  type        = string
  default     = "/crossfeed/staging/MDL_NAME"
}

variable "ssm_mdl_username" {
  description = "ssm_mdl_username"
  type        = string
  default     = "/crossfeed/staging/MDL_USERNAME"
}

variable "ssm_mdl_password" {
  description = "ssm_mdl_password"
  type        = string
  default     = "/crossfeed/staging/MDL_PASSWORD"
}

variable "ssm_redshift_host" {
  description = "ssm_redshift_host"
  type        = string
  default     = "/crossfeed/staging/REDSHIFT_HOST"
}

variable "ssm_redshift_database" {
  description = "ssm_redshift_database"
  type        = string
  default     = "/crossfeed/staging/REDSHIFT_DATABASE"
}

variable "ssm_redshift_user" {
  description = "ssm_redshift_user"
  type        = string
  default     = "/crossfeed/staging/REDSHIFT_USER"
}

variable "ssm_redshift_password" {
  description = "ssm_redshift_password"
  type        = string
  default     = "/crossfeed/staging/REDSHIFT_PASSWORD"
}

variable "ssm_dmz_api_key" {
  description = "ssm_dmz_api_key"
  type        = string
  default     = "/crossfeed/staging/DMZ_API_KEY"
}

variable "ssm_vs_pull_date_range" {
  description = "ssm_vs_pull_date_range"
  type        = string
  default     = "/crossfeed/staging/VS_PULL_DATE_RANGE"
}

variable "ssm_latest_port_scan_cutoff" {
  description = "ssm_latest_port_scan_cutoff"
  type        = string
  default     = "/crossfeed/staging/LATEST_PORT_SCAN_CUTOFF"
}

variable "ssm_dmz_sync_endpoint" {
  description = "ssm_dmz_sync_endpoint"
  type        = string
  default     = "/crossfeed/staging/DMZ_SYNC_ENDPOINT"
}

variable "create_elasticache_cluster" {
  description = "Whether to create a elasticache cluster."
  type        = bool
  default     = false
}

variable "crossfeed-lz-sync_name" {
  type        = string
  description = "The name of the S3 bucket for Crossfeed LZ sync"
  default     = "crossfeed-lz-sync"
}

variable "image_tag" {
  description = "The tag for the image in ECR"
  type        = string
  default     = "latest"
}

variable "crossfeed_playwright" {
  description = "The name of the Crossfeed Playwright environment"
  type        = string
}

variable "automated_test_reports_bucket_name" {
  description = "The name of the automated test report S3 bucket"
  type        = string
}

variable "playwright_worker_ecs_task_definition_family" {
  description = "playwright_worker_ecs_task_definition_family"
  type        = string
  default     = "crossfeed-playwright-worker-staging-cd"
}

variable "xpanse_org_sync_bucket_name" {
  type        = string
  description = "The name of the S3 bucket for Crossfeed Xpanse Org sync"
  default     = "crossfeed-xpanse-org-sync"
}

variable "playwright_worker_repository_name" {
  description = "playwright_worker_repository_name"
  type        = string
  default     = "crossfeed-playwright-staging-worker"
}

variable "zscaler_cert_bucket_name" {
  description = "zscaler_cert_bucket_name"
  type        = string
  default     = "cisa-crossfeed-staging-zscaler"
}

variable "backend_api_log_group_name" {
  description = "backend_api_log_group_name"
  type        = string
  default     = "cyhy-staging-backend-api"
}

variable "backend_api_requests_log_group_name" {
  description = "backend_api_requests_log_group_name"
  type        = string
  default     = "cyhy-staging-backend-api-requests"
}

variable "django_env_bucket_name" {
  description = "django_env_bucket_name"
  type        = string
  default     = "cyhy-staging-django-env"
}

variable "ssm_django_env_kms_arn" {
  description = "django_env_kms_key_arn"
  type        = string
  default     = "/crossfeed/prod/DJANGO_ENV_KMS_ARN"
}

variable "ssm_dnsmonitor_client_id" {
  description = "ssm_dnsmonitor_client_id"
  type        = string
  default     = "/crossfeed/staging/DNSMONITOR_CLIENT_ID"
}

variable "ssm_dnsmonitor_client_secret" {
  description = "ssm_dnsmonitor_client_secret"
  type        = string
  default     = "/crossfeed/staging/DNSMONITOR_CLIENT_SECRET"
}

variable "ssm_flare_tenant_id" {
  description = "ssm_flare_tenant_id"
  type        = string
  default     = "/crossfeed/staging/FLARE_TENANT_ID"
}

variable "ssm_flare_api_keys" {
  description = "Comma-separated Flare API keys (SSM parameter path)"
  type        = string
  default     = "/crossfeed/staging/FLARE_API_KEYS"
}

variable "ssm_shodan_org_exception" {
  description = "ssm_shodan_org_exception"
  type        = string
  default     = "/crossfeed/staging/SHODAN_ORG_EXCEPTION"
}
