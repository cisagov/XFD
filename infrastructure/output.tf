output "worker_ecs_repository_url" {
  value = aws_ecr_repository.worker.repository_url
}

output "open_cti_backfill_script" {
  description = <<-EOT
    The exact boot-time payload aws_instance.open_cti's user_data runs at a
    genuine first boot (see open_cti.tf's local.open_cti_user_data and its
    header comment). Because user_data_replace_on_change = false never fires
    it against an instance that's already running, the already-running
    stage-cd instance needs this replayed against it by hand, once, to pick
    up the .env-automation systemd units:

      terraform output -raw open_cti_backfill_script > /tmp/open-cti-backfill.sh
      aws ssm send-command \
        --instance-ids <stage-cd instance id> \
        --document-name AWS-RunShellScript \
        --parameters commands="$(cat /tmp/open-cti-backfill.sh)"

    open-cti/env.static's 11 STABLE IDENTIFIERS (XTM_COMPOSER_ID + the 10
    CONNECTOR_*_ID values) already match stage-cd's real, registered values as
    of 2026-08-17 -- confirmed against that box's actual .env, not left as
    placeholders. bootstrap.sh still refuses to render .env if any of them
    are ever reset to the literal REPLACE_ME_STABLE_UUID placeholder, but a
    value that's simply wrong (e.g. a freshly-generated UUID swapped in by
    mistake) would pass that check silently and cause OpenCTI to register
    duplicate connectors on next boot -- don't regenerate these for stage-cd.

    docker-compose.yml, rabbitmq.conf, bootstrap.sh, env.static, and both
    systemd units are NOT part of this payload either -- this script only
    installs open-cti/refresh-repo.sh, which git-clones/pulls
    var.open_cti_repo_url at var.open_cti_repo_branch into
    /opt/open-cti-repo and runs everything straight out of that checkout.
    That means the instance needs real outbound internet access to reach
    that URL (git-over-HTTPS) -- confirm that before backfilling, or
    refresh-repo.sh's `git clone` step will simply hang or fail.
  EOT
  value       = local.open_cti_user_data
  sensitive   = true
}

# output "db_accessor_instance_id" {
#   value = try(aws_instance.db_accessor[0].id, null)
# }

output "was_reporting_instance_id" {
  description = "ID of the WAS reporting EC2 instance when enabled in the DMZ environment."
  value       = try(aws_instance.was_reporting[0].id, null)
}

output "was_reporting_private_ip" {
  description = "Private IP address of the WAS reporting EC2 instance when enabled in the DMZ environment."
  value       = try(aws_instance.was_reporting[0].private_ip, null)
}
