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

- `source_row_number` is included so imports can preserve the workbook row
  origin.
- `assignee_id` links tracker rows to `was_assignees.id`. The original workbook
  name is still preserved in `assignee` for auditability during migration.
- No uniqueness constraint is applied yet because the workbook appears to
  preserve historical daily rows and duplicate business keys may be valid.
- `legacy_password` should not be treated as the source of truth for generated
  PDF encryption. Use `was_stakeholders.report_password` for current report
  password management.

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
