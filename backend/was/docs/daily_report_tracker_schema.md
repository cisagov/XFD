# Daily Report Tracker Schema

This document maps the legacy daily report tracker workbook to the Postgres
`was_daily_report_tracker` table. The source workbook inspected was
`WAS_TRACKER_DailyReports_UpdatedDaily.xlsx`.

## Workbook Summary

- Sheet name: `Sheet1`
- Rows inspected: `82636`
- Columns inspected: `20`
- Purpose: Preserve daily WAS report tracker state that was previously stored in
  Excel so `update_tracker` can write to Postgres.

## Column Mapping

| Workbook Column | Database Column | Type | Notes |
| --- | --- | --- | --- |
| `DataPullDate` | `data_pull_date` | `DATE` | Workbook values are dates. |
| `Tag` | `tag` | `VARCHAR(128)` | Stakeholder tag. Indexed. |
| `Scan Name` | `scan_name` | `TEXT` | Long descriptive scan names. |
| `Assignee` | `assignee` | `VARCHAR(256)` | Legacy analyst or operator name preserved from the workbook. |
| `Status` | `status` | `VARCHAR(128)` | Examples include `Finished`, `Error`, and `Running`. |
| `Result` | `result` | `VARCHAR(128)` | Examples include `Successful`, `Service Error`, and `Time Limit Reached`. |
| `Report Sent Date` | `report_sent_date` | `DATE` | Workbook values are dates. |
| `Report/Scan Notes` | `report_scan_notes` | `TEXT` | Mixed text and date-like notes, stored as text. |
| `Scan Start Date` | `scan_start_date` | `DATE` | Workbook values are dates. |
| `Next Scan Date` | `next_scan_date` | `DATE` | Workbook values are dates. Indexed. |
| `POC` | `poc` | `TEXT` | May contain multiple names. |
| `POC Email` | `poc_email` | `TEXT` | May contain multiple addresses separated by semicolons. |
| `Customer Notes` | `customer_notes` | `TEXT` | Mixed text, time-like values, and notes. |
| `NWS` | `nws` | `TEXT` | Mixed integer counts and comma-separated count triplets. |
| `Template` | `template` | `VARCHAR(128)` | Examples include `Results`, `Action Required`, and `Deactivated`. |
| `Recent NWS` | `recent_nws` | `TEXT` | May contain HTML break-delimited URLs. |
| `Remove NWS` | `remove_nws` | `TEXT` | May contain HTML break-delimited URLs. |
| `Password` | `legacy_password` | `TEXT` | Preserves legacy workbook value. Stakeholder-level report passwords remain in `was_stakeholders.report_password`. |
| `Schedule ID` | `schedule_id` | `BIGINT` | Qualys schedule identifier. Indexed. |
| `Qualys Error` | `qualys_error` | `TEXT` | May contain HTML break-delimited URLs or error context. |

## Operational Notes

- `assignee_id` links tracker rows to `was_assignees.id`. The original workbook
  name is still preserved in `assignee` for auditability during migration.
- New API tracker rows use `scan_execution_key`, combining the schedule ID
  and actual UTC launch timestamp. A partial unique index prevents duplicate
  ingestion of the same execution while allowing a recurring schedule's next
  execution. Imported historical rows may keep a NULL key; do not invent an
  exact timestamp from a date-only workbook cell.
- `legacy_password` should not be treated as the source of truth for generated
  PDF encryption. Use `was_stakeholders.report_password` for current report
  password management.

## Existing Database Hardening Upgrade

`schema/stakeholders_table_creation.sql` is the complete schema for a new
database. For an existing database, stop old workers, take an approved backup,
confirm `SELECT current_database();` returns `was`, and apply the following
additive SQL. Do not rerun the complete CREATE TABLE file. No historical rows
are deleted by this update.

```sql
BEGIN;
ALTER TABLE was_report_runs
    ADD COLUMN IF NOT EXISTS generation_token TEXT,
    ADD COLUMN IF NOT EXISTS email_claim_token TEXT,
    ADD COLUMN IF NOT EXISTS delivery_purpose TEXT NOT NULL DEFAULT 'customer'
        CHECK (delivery_purpose IN ('customer', 'analyst'));

ALTER TABLE was_daily_report_tracker
    ADD COLUMN IF NOT EXISTS scan_execution_key TEXT,
    ADD COLUMN IF NOT EXISTS assignee_email_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (assignee_email_status IN ('pending', 'sending', 'sent', 'failed', 'held')),
    ADD COLUMN IF NOT EXISTS assignee_email_claim_token TEXT,
    ADD COLUMN IF NOT EXISTS assignee_email_claimed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS digest_revision BIGINT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS digest_claimed_revision BIGINT;

CREATE UNIQUE INDEX IF NOT EXISTS was_daily_report_tracker_scan_execution_uidx
    ON was_daily_report_tracker (scan_execution_key)
    WHERE scan_execution_key IS NOT NULL;

UPDATE was_daily_report_tracker
SET assignee_email_status = CASE
    WHEN assignee_emailed_at IS NOT NULL THEN 'sent'
    ELSE 'held' END
WHERE assignee_email_status = 'pending'
  AND (assignee_emailed_at IS NOT NULL OR assignee_email_error IS NOT NULL);

UPDATE was_report_runs
SET delivery_purpose = 'analyst'
WHERE generation_token IS NULL
  AND scheduled_epoch IS NULL
  AND (source_tracker_id IS NULL OR email_status = 'held');

UPDATE was_report_runs
SET qualys_xml_report_status = CASE
        WHEN qualys_xml_report_id IS NULL AND qualys_xml_report_status IS NULL
            THEN 'CREATE_REQUESTED' ELSE qualys_xml_report_status END,
    qualys_detail_report_status = CASE
        WHEN qualys_detail_report_id IS NULL AND qualys_detail_report_status IS NULL
            THEN 'CREATE_REQUESTED' ELSE qualys_detail_report_status END
WHERE generation_token IS NULL AND status IN ('running', 'failed');
COMMIT;
```

The audience update conservatively classifies historical standalone/held runs
as analyst-only. Review other historical runs' intended audience before sending.
An existing digest error might represent uncertain delivery, so the upgrade
holds it instead of automatically retrying it. Re-running the upgrade does not
reset current claims or sent records. Apply only with workers stopped.
Historical failed/running rows without an artifact ID or creation status are
conservatively marked `CREATE_REQUESTED`: the old code did not record whether
a timed-out POST was accepted. Reconcile these in Qualys before retrying; do
not clear an uncertain marker merely to force creation of a replacement.

Verify the additional columns with:

```sql
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('was_report_runs', 'was_daily_report_tracker')
  AND (column_name LIKE '%token' OR column_name LIKE 'assignee_email%'
       OR column_name IN ('delivery_purpose', 'scan_execution_key',
                          'digest_revision', 'digest_claimed_revision'))
ORDER BY table_name, ordinal_position;
```

Rollback means stopping the new workers and restoring the previous image after
reviewing active/held runs. Leave the additive columns in place; do not drop
ownership or delivery evidence to make an older image run.

## Assignee Seed Data

The workbook contained seven unique assignee names:

- Mina Salehi
- Tenesa Ellis
- Brycen Ford
- Zack Cogswell
- Justin Rothfleisch
- Oscar Saunders
- Wale Ojelabi

The seed script is `schema/updates/005_seed_was_assignees.sql`.
