# WAS Delivery Failure Review and Retry

The **Report tracker > Review failed report deliveries** menu entry reviews
persisted SES failures and retries one confirmed failed recipient using the
archived S3 PDF. This workflow does not regenerate the report or change its
generation status. It does not update `was_stakeholders` contact addresses;
an optional correction applies only to the new delivery attempt. A confirmed
failure can also be retried at the same address when the original block has
cleared.

## Deployment prerequisites

1. Have the DBA compare the target database with
   [`schema/stakeholders_table_creation.sql`](../schema/stakeholders_table_creation.sql)
   and review the one-time
   [`20261118_delivery_failure_review.sql`](../schema/migrations/20261118_delivery_failure_review.sql)
   additive migration. It creates the four new delivery tables and their
   indexes in one transaction. It assumes `was_stakeholders` and
   `was_report_runs` already exist in the expected shape and none of the new
   delivery tables exist. Apply it through the approved database change
   process before deploying code that records initial sends. For `psql`, use
   `-v ON_ERROR_STOP=1` so a failed statement stops the migration. Do not run
   the complete creation script against a populated database, and do not
   rerun the one-time migration after success.
2. Provision exact stakeholder grants in
   `was_delivery_stakeholder_grants`. The menu identifies the effective host UID
   passed to its container by `make menu` as `os-uid:<uid>`; no new CLI login is
   added. Missing grants deny list, detail, and retry operations, including
   any recipient correction made as part of a retry.
   Grant provisioning and revocation require the approved DBA process. A shared
   host UID has shared audit attribution and **does not identify an individual
   analyst**. Individual attribution remains open until an approved identity
   mechanism is connected.
3. Keep the existing SES sending role. Confirm its event source with the owner. An
   SNS topic alone does not receive SES sending events: the SES identity
   notification or configuration-set event destination must publish to the
   exact topic. For configuration-set publishing, set
   `WAS_SES_CONFIGURATION_SET` to the approved set name so `SendRawEmail` uses
   it. The sending account must permit publishing to the topic, restricted to
   the SES source account and identity or configuration-set ARN. Subscribe the
   `was_reports.delivery.ses_events.handler` Lambda to the exact SNS topic and
   set `WAS_SES_EVENTS_TOPIC_ARN`. Its Lambda invocation permission must be
   restricted to that topic. Deploy the Lambda with a role that can access only
   the WAS database and required logging service. The handler stores only
   classified event fields, affected recipient addresses, and an allowlisted
   SMTP status code; it does not store the raw SNS or SES payload.
4. Verify the sender role, S3 object prefix, KMS key, database grants, bucket
   lifecycle, and topic subscription in the target environment. The codebase
   does not own the external SES role or prove its event destination. The
   backend alone retrieves S3 objects under its assigned role; no browser or
   customer receives AWS credentials or a direct S3 download route.
5. Ticket 4631 sets a 14-day retention period for recipient addresses copied
   into delivery-review records and for retry records, measured from each
   record's creation. Build the updated image and run
   `make delivery-retention-cleanup` to preview counts without recipient data.
   After the DBA reviews the new schema and cleanup behavior, install and
   enable `systemd/was-delivery-retention.service` and
   `systemd/was-delivery-retention.timer` on the EC2 host. The timer applies
   cleanup hourly. Verify its first run with `systemctl status` and `journalctl`.
   The host operator must be able to run the existing Docker image and access
   the approved `.env` database configuration. No AWS role change is required.

   From `backend/was` on the EC2 host, after the image and migration are ready:

   ```sh
   sudo install -m 0644 systemd/was-delivery-retention.service \
     /etc/systemd/system/was-delivery-retention.service
   sudo install -m 0644 systemd/was-delivery-retention.timer \
     /etc/systemd/system/was-delivery-retention.timer
   sudo systemctl daemon-reload
   sudo systemctl enable --now was-delivery-retention.timer
   sudo systemctl status was-delivery-retention.timer --no-pager
   ```

   Run `make delivery-retention-cleanup` first to preview and
   `make delivery-retention-cleanup APPLY=1` for a reviewed manual application.

## Delivery-record retention

After 14 days, the cleanup removes retry attempt rows. It keeps the SES
event's nonaddress classification and SNS message ID for audit and duplicate
notification suppression, but removes copied recipient addresses.
The audit rows keep the historical retry attempt ID, actor, action, and time,
without recipient data. Original attempts remain, but their copied recipient
arrays are emptied and marked redacted. SES events retained for original
failures keep classification and timestamps while their copied recipient
arrays are emptied. A retry claim and transition to SES sending are refused
after the attempt's 14-day window, so removal cannot reopen a duplicate send.
The cleanup waits for a recently active pending or sending retry to settle
before deleting it; a stale one is eligible on a later hourly run.

This rule does not change saved contact addresses in `was_stakeholders`, the
S3 object lifecycle, or the separate `WAS_LOG_RETENTION_DAYS=14` log-file
setting. It does not establish a retention period for the original failure's
nonaddress metadata or for access-audit metadata. The database cleanup is
not active until its migration, container image, and timer are deployed.

Historical `was_report_runs.email_status`, `email_message_id`, and
`email_error` values cannot reconstruct original recipients or SES events.
Review lists include new attempts recorded after the additive schema is
deployed; do not manufacture a confirmed failure from a historical error
string.

## Operator procedure

1. Open `make menu`, select **Report tracker**, then **Review failed report
   deliveries**. Filter by stakeholder tag, exact recipient, failure date or
   date range, bounce type, delivery status, or report run ID. The list is
   bounded and scoped to the current principal's stakeholder grants.
2. Select an attempt to see its report run, recipients, attempt history,
   classified SES events, and sanitized diagnostic. List and
   detail reads each create a minimal audit event. Unknown and inaccessible
   attempts yield the same menu response.
3. For a **confirmed customer failure**, enter the exact failed recipient.
   Press Enter to resend to that same address, or enter a corrected address for
   this retry only. Review the displayed pair and enter the exact confirmation
   phrase. The service validates the destination and checks that SES identified
   that recipient as failed. It atomically records the retry request, plus a
   correction audit action only when the address changes, and creates a child
   attempt holding the chosen destination. The saved stakeholder contact
   remains unchanged.
   A transient or undetermined bounce, complaint, or uncertain SES request is
   held for manual review and cannot be retried through this menu.
4. Each confirmed submission has a request key. Repeated submission of that
   same key returns its existing attempt; a different key cannot send again
   while another retry may have reached SES. A pre-send failure is recorded
   separately and permits a new confirmed request after its cause is fixed.
   A different failed recipient on the same original message can have its own
   child attempt. The next authorized review or retry reclassifies a retry
   left pending or sending beyond `WAS_EMAIL_CLAIM_STALE_SECONDS`. Stale pending
   becomes a pre-send failure; stale sending is held for manual review and is
   never automatically resent.
5. The backend downloads the original run-specific encrypted PDF from the
   configured bucket and prefix into a private temporary file, validates its
   structure and SHA-256 digest recorded before the original send, then builds
   a message for only the selected address. This allows a stakeholder PDF
   password change without accepting a different or unvalidated archive. If S3
   is missing, inaccessible, or invalid, it records a separate pre-send failure
   and sends nothing. SES acceptance records a new message ID on the child;
   later SES events update its outcome. An uncertain result after the SES call
   begins is held for manual reconciliation. The original attempt and events
   are preserved.

The audit table stores the principal key, action, affected attempt, and UTC
timestamp. It omits recipient addresses, report contents, passwords, and raw
diagnostics. Private operational logs use sanitized exception details.

There is no report-download endpoint in this CLI release. Any future download
route must enforce the same stakeholder authorization before the backend
retrieves an object from S3.
