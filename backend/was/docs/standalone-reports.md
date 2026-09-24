# Standalone reports for non-enrolled Qualys tags

In **Report Generation**, choose **5. Generate a standalone report for a Qualys
tag NOT in the stakeholder database**. Option 4 remains the on-demand path for
enrolled stakeholders; option 0 returns to the main menu.

Supply an exact, unique Qualys tag name and an email-enabled analyst address
(comma or semicolon separated lists are accepted). Confirm whether to send email
after S3 archiving, then confirm the operation. This path checks Qualys directly;
it does not insert a stakeholder or tracker row, assign an analyst, or make the
target eligible for daily reporting. Missing/ambiguous Qualys tags and tags already
enrolled by name or Qualys ID are rejected.

The `was_standalone_report_targets` table stores the Qualys ID, name, generated
PDF password, delivery email, and timestamps. Repeat requests reuse those values.
The password is not printed, included in command arguments, or emailed. It uses
the same database access protections as stakeholder passwords. Authorized
operators must arrange password delivery separately. The current command does
not rotate passwords or change saved addresses; different submitted addresses
are rejected for review. Enrollment later remains an explicit stakeholder action.

Standalone report runs use `delivery_purpose = 'standalone'`, a target foreign
key, no stakeholder foreign key, and no tracker link. Generation uses the existing
leases, isolated workspaces, PDF encryption, Qualys report-ID persistence, and S3
storage. Email uses the existing claim and uncertain-delivery handling. Saved
recipients are revalidated against email-enabled analysts at delivery; inactive
analysts are allowed when email-enabled. No recipient override is accepted.
Archive-only requests do not email. Daily bulk delivery selects customer runs
only, so it cannot send these reports later accidentally.

CLI equivalent, after installing the updated package:

```sh
was-report-standalone --tag HHS_NIH_1_1 --delivery-email analyst@example.gov --send-email
```

On repeat requests, omit `--delivery-email` to reuse the saved address. Omit
`--send-email` for archive-only generation. Failed/uncertain operations must be
reviewed by run ID before retrying; starting the command again requests a new
report, not an automatic resend. Active and held uncertain deliveries block a
new generation. Existing stakeholder reports and automatic batch rules are unchanged.

To deliver an already completed archive-only run without regenerating it, review
the run and use `was-mailer --report-run-id <ID> --delivery-purpose standalone`.
It uses the saved recipient and does not accept `--test-recipients`. Archive-only
runs with pending delivery remain eligible. Held uncertain deliveries remain
blocked, including when `--include-previous-failures` is supplied. Verify the SES
outcome and reconcile the run before any further delivery attempt; the ordinary
standalone mail command does not override a hold. Do not blindly regenerate them.

## Database schema and deployment

The operator confirmed the database modifications are complete on September 24,
2026. This workflow assumes that updated schema is already installed; there is no
outstanding migration step for the confirmed database.

The authoritative, comprehensive definition is
[`schema/stakeholders_table_creation.sql`](../schema/stakeholders_table_creation.sql).
It includes:

- `was_standalone_report_targets`, with a unique Qualys tag ID and tag name,
  stored report password, delivery email, and timestamps.
- A nullable `was_report_runs.stakeholder_tag` and the new
  `standalone_target_id` foreign key.
- The `standalone` delivery purpose and target constraints separating standalone
  runs from stakeholder runs and preventing standalone tracker links.
- A unique active-standalone index preventing simultaneous running or sending
  operations for the same standalone target.

After the schema changes, deploy the matching application code and rebuild the
image. Do not rerun the full creation script against an existing database. Other
environments must be checked against the comprehensive schema before deployment;
the operator's confirmation does not establish their migration status.
Incremental SQL remains local and ignored, not a required repository artifact.
The application does not apply migrations automatically.
