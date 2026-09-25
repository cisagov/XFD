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

The API-backed tracker also stores fields that do not exist in the legacy
workbook:

| Database Column | Type | Purpose |
| --- | --- | --- |
| `id` | `BIGSERIAL` | Stable tracker-row identifier. |
| `assignee_id` | `BIGINT` | Optional foreign key to `was_assignees.id`. |
| `scan_started_at` | `TIMESTAMPTZ` | Actual Qualys execution start timestamp. |
| `scan_ended_at` | `TIMESTAMPTZ` | Actual or safely derived Qualys execution end timestamp. |
| `tag_id` | `BIGINT` | Qualys tag identifier associated with the execution. |
| `scan_execution_key` | `TEXT` | Exact execution identity used by the partial unique index. |
| `assignee_emailed_at` | `TIMESTAMPTZ` | Historical assignee-delivery timestamp. |
| `assignee_email_message_id` | `TEXT` | SES acceptance identifier for the historical assignee delivery. |
| `assignee_email_error` | `TEXT` | Safe delivery failure summary. |
| `assignee_email_status` | `TEXT` | `pending`, `sending`, `sent`, `failed`, or `held`. |
| `assignee_email_claim_token` | `TEXT` | Ownership token for concurrent-safe email claims. |
| `assignee_email_claimed_at` | `TIMESTAMPTZ` | Claim timestamp used for stale-operation handling. |
| `digest_revision` | `BIGINT` | Monotonic revision for shared analyst summaries. |
| `digest_claimed_revision` | `BIGINT` | Revision owned by an in-progress summary claim. |
| `created_at`, `updated_at` | `TIMESTAMPTZ` | Database audit timestamps. |

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
- `scan_start_date` is the calendar-date selection field. It is not a substitute
  for `scan_started_at`, which is the timestamp shown in customer email text.
  Date-only CSV/XLSX imports do not invent execution timestamps.
- `scan_started_at` and `scan_ended_at` are nullable because historical imports
  and incomplete Qualys responses may not provide defensible timestamps.
- `source_tracker_id` on `was_report_runs` is unique when present. Together with
  report-run claims and `scan_execution_key`, this prevents the same tracker row
  from being generated concurrently or delivered as a new customer run twice.

## Canonical Schema And Deployment State

[`schema/stakeholders_table_creation.sql`](../schema/stakeholders_table_creation.sql)
is the authoritative desired-state schema for a new, empty database. It defines
the current stakeholder, standalone target, report-run, assignee, tracker,
special-case, batch-summary, capacity-attempt, and test-replay structures,
including their indexes, constraints, and foreign keys.

The currently managed WAS database is assumed to have already received the
approved schema changes. Do not rerun the comprehensive creation file against
an existing populated database: it contains unconditional `CREATE TABLE`
statements and is a desired-state reference, not an idempotent migration.

Incremental files retained locally under `schema/updates/` are historical or
operator-specific records. They are intentionally ignored by Git and are not
release artifacts or a supported ordered migration chain. When a populated
environment needs a future change, generate a narrowly scoped DBA-reviewed
migration from the canonical desired state, back up the database, stop writers,
apply it through the approved change process, verify it, and update both the
canonical schema and this document in the same code change.

## Current Related Tables

The tracker participates in these current schema relationships:

- `was_stakeholders` stores enrolled customer metadata and the current PDF
  password.
- `was_assignees` controls operational assignment (`active`) independently from
  permitted email recipients (`email_enabled`).
- `was_report_runs.source_tracker_id` links a generated run to one tracker row;
  `delivery_purpose` allows `customer`, `analyst`, and `standalone`.
- `was_standalone_report_targets` supports approved on-demand reporting for a
  Qualys tag that is not enrolled as a stakeholder. Standalone runs do not
  create or change tracker rows.
- `was_batch_runs` and `was_batch_report_attempts` record production and
  capacity-batch scope, progress, summary delivery, timing, and outcomes.
- `was_test_replay_batches` and `was_test_replay_items` preserve controlled
  analyst-recipient replay scope without deleting original report history.
- `was_special_cases` stores active tags that bypass automated NWS removal.

## Read-Only Schema Verification

Run these checks after a deployment or database restore. They inspect metadata
only and do not modify application data.

Confirm the expected application tables:

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name LIKE 'was_%'
ORDER BY table_name;
```

Confirm the execution, claim, and delivery fields used by current code:

```sql
SELECT table_name, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND (
    (table_name = 'was_daily_report_tracker' AND column_name IN (
      'scan_execution_key', 'scan_started_at', 'scan_ended_at',
      'assignee_email_status', 'assignee_email_claim_token',
      'assignee_email_claimed_at', 'digest_revision',
      'digest_claimed_revision'
    ))
    OR
    (table_name = 'was_report_runs' AND column_name IN (
      'source_tracker_id', 'standalone_target_id', 'generation_token',
      'delivery_purpose', 'email_status', 'email_claim_token',
      'qualys_detail_report_status', 'qualys_xml_report_status'
    ))
  )
ORDER BY table_name, ordinal_position;
```

Confirm the duplicate-prevention indexes:

```sql
SELECT indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND indexname IN (
    'was_daily_report_tracker_scan_execution_uidx',
    'was_report_runs_source_tracker_id_uidx',
    'was_report_runs_active_schedule_uidx',
    'was_report_runs_active_standalone_uidx'
  )
ORDER BY indexname;
```

Treat a missing table, column, constraint, or index as a deployment blocker.
Do not repair drift by copying a historical local increment into production
without review. Rollback should restore the approved database backup and prior
application image together, while preserving evidence for held or uncertain
Qualys and SES operations.

## Assignee Seed Data

The workbook contained seven unique assignee names:

- Mina Salehi
- Tenesa Ellis
- Brycen Ford
- Zack Cogswell
- Justin Rothfleisch
- Oscar Saunders
- Wale Ojelabi

Assignee seed data is deployment-specific and is intentionally excluded from
the canonical schema.
