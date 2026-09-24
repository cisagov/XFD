# Operator menu workflows

`make menu` has three categories: Report generation, Report tracker, and
Stakeholder management. Quit and Back to main menu are always **0**, first in
the list; submenus retain `b` as a shortcut. Destination menus use 0 to cancel.
The Qualys category and slow inventory menu action have been removed. The
inventory CLI remains available for explicit use.

## Report generation

1. Run the complete recent scan batch.
2. Process eligible automated tracker reports: no tag prompt, no report-count
   limit; uses existing tracker rows and asks for the window (7 days by default,
   or `all`). Existing newest-row eligibility and duplicate guards still apply.
   Requires confirmation before customer delivery.
3. Process an eligible manual tracker report.
4. Generate an on-demand report to S3 (optional email), for enrolled stakeholders.
5. Generate a standalone report for a Qualys tag NOT in the stakeholder database.
6. Start an isolated parallel capacity load test: prompts for worker count
   (1 through 30, default 30), test recipients, and workload label. Confirmation
   starts real Qualys, S3, and SES operations against the configured test database.
   Customer POC addresses are not used. The coordinator automatically creates
   the run ID and uses the refreshed eligible count. This does not reset the
   test database; continuation and start-over remain separate Make commands.

## Report tracker

Existing table, row, error, manual sent-date, CSV export, and XLSX import actions
remain. Additional actions:

- **View all tracker entries for a customer tag** includes all dates and no row
  limit. Child-tag inclusion follows `parent_tag` recursively (not a name-prefix
  match) and is cycle-safe.
- **Refresh the report tracker from API** replaces the former Qualys menu action.
- **Export tracker CSV** offers local output, direct S3, or email to approved,
  email-enabled analysts. S3/email exports exclude the Password column and escape
  spreadsheet formulas. S3 objects are encrypted and use unique names under
  `tracker_exports`. Local exports retain the legacy CSV format, including the
  legacy password column; handle those files as sensitive.
- **Correct a tracker row** displays the row and lets an operator correct one
  supported field per confirmation: status, result, notes, template, NWS/error
  metadata, or Qualys tag ID. Use `CLEAR` for nullable metadata and `CANCEL` to
  stop. Status accepts Finished, Error, or Processing; templates must be approved
  template names. It compares the inspected row under a database lock and refuses
  stale edits, sent rows, active digest delivery, or any row already linked to a
  report run. Identity, scan dates, passwords, assignments, and delivery history
  are protected. It never resets a claim, reruns generation, sends mail, or changes
  Qualys. Existing failed/held report runs require separate reconciliation.
  Customer email addresses must be corrected in Stakeholder Management.

CLI examples:

```sh
was-tracker show --tag CUSTOMER --include-children --all-dates --limit all
was-tracker export-csv --days-back 7 --s3
was-tracker export-csv --days-back 7 --email-assignee analyst@example.gov
```

## Stakeholder management

The order is View, Update row, Update point of contact information, Add new by
CLI, Import new from CSV, Export to CSV, Retrieve password, Rotate password,
and Manually enter password. Operations check the tag before collecting further
inputs; Add rejects existing tags early. Contact prompts show and prefill current
values. Enter keeps them; `CLEAR` removes a value. Add shows the known CI type,
testing sector, subtype, and frequency options. State remains a direct entry with
the INTERNATIONAL guidance. These suggestions do not introduce new enum validation.

These menu/tracker changes require no additional schema migration. The operator
has confirmed the standalone-report database changes are complete. This workflow
assumes the schema described in [standalone reports](standalone-reports.md#database-schema-and-deployment),
with `schema/stakeholders_table_creation.sql` as the comprehensive reference.
