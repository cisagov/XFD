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

    docker-compose.yml and rabbitmq.conf are NOT part of this payload (18KB,
    over EC2's user_data limit) -- bootstrap.sh instead fetches both from S3
    itself, every boot (step 0). That means the S3 bucket needs to actually
    have current objects in it before backfilling: confirm
    .github/workflows/open-cti-config-sync.yml has run at least once (it
    fires on every push to develop touching either file) -- a bucket that's
    never been populated will make bootstrap.sh fail on its `aws s3 cp` step.
  EOT
  value       = local.open_cti_user_data
  sensitive   = true
}

# output "db_accessor_instance_id" {
#   value = try(aws_instance.db_accessor[0].id, null)
# }
