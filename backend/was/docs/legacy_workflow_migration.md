# Legacy WAS Workflow Migration Checklist

This checklist tracks the original `was_report/WAS_report_creator.py`
functionality that must be incorporated into the modernized WAS project. The
goal is an inclusive lift and shift with targeted improvements, not a partial
rewrite.

## Migration Principles

- Preserve the existing report output format until the ReportLab migration is
  explicitly started.
- Move functionality into WAS-owned modules under `src/was_reports` or
  `src/was_mailer`.
- Keep Qualys data calls behind `was_reports.qualys_client`.
- Keep stakeholder, scheduling, report-run, and password state in Postgres.
- Keep mutating Qualys operations separate from scheduled report generation.
- Add tests before replacing legacy behavior.

## Current Modernized Entry Points

| Capability | Current Modernized Entry Point | Status | Notes |
| --- | --- | --- | --- |
| Scheduled report batch | `was-report-batch` | Started | Selects due stakeholders from Postgres and runs one report per stakeholder. |
| Single stakeholder report | `was-reports --tag` | Started | Delegates to legacy creator while managing config, password, and output verification. |
| Report password creation | `was-reports --create-missing-password` | Started | Generates and stores customer report passwords in Postgres. |
| Report password rotation | `was-reports --change-password` | Started | Generates a new password for the supplied stakeholder tag. |
| Report email delivery | `was-mailer` | Started | Sends completed PDF report artifacts through SES-style email flow. |
| Daily report tracker persistence | `was-update-tracker` | Started | Container command runs the legacy tracker flow and writes rows to Postgres. Qualys webapp deletion requires `--delete-apps`. |
| Daily tracker assignees | `was_reports.data.assignees` | Started | Lookup table, seed SQL, and upsert helper exist. |

## Original Report Generation Path

This path must be fully migrated before the legacy report creator can be
retired.

| Legacy Step | Legacy Function | Target Module | Status | Notes |
| --- | --- | --- | --- | --- |
| Validate operator arguments | `main` | `was_reports.report_generator` | Started | Current CLI validates tag and config path. |
| Count web applications | `app_count` | `was_reports.report_data` | Started | Migrated helper exists. It is not yet wired into the legacy report execution path. |
| Resolve Qualys tag ID | `get_tag_id` | `was_reports.report_data` | Started | Migrated helper exists. It is not yet wired into the legacy report execution path. |
| Create detail report when app count is below threshold | `create_details_report` | `was_reports.report_data` | Started | Payload and response handling are migrated. Download and PDF post-processing remain pending. |
| Download detail report PDF | `download_report` | `was_reports.detail_reports` | Started | Direct download is behind a tested helper. It is not yet wired into the legacy execution path. |
| Watermark detail report | `watermarker` | `was_reports.pdf_helpers` | Started | Migrated helper exists. It is not yet wired into the legacy execution path. |
| Remove first page from detail report | `unfirstpagify` | `was_reports.pdf_helpers` | Started | Migrated helper exists. It is not yet wired into the legacy execution path. |
| Redact Qualys detail PDF | `qualys_redact` | `was_reports.pdf_helpers` | Started | Migrated helper wraps `redact_qualys.py`. It is not yet wired into the legacy execution path. |
| Create XML web application report | `create_webapp_report_v2` | `was_reports.report_data` | Started | Payload and response handling are migrated and used by `was-export-xml`. Template ID is still hardcoded for compatibility. |
| Download XML report | `get_report` | `was_reports.report_data` | Started | Migrated helper is used by `was-export-xml`; the main PDF path still invokes the legacy script. |
| Parse XML findings | `csv_genner`, finding classes | Transformation module | Pending | Needs XML fixture coverage. |
| Generate CSV artifacts | `csv_genner` | Transformation or artifact module | Pending | Preserve naming and content if still required. |
| Generate graphs | graph helper functions | Chart module | Pending | Uses matplotlib and seaborn. |
| Generate report body | `mustache_generate`, `generate_full` | Renderer module | Pending | Keep Mustache and LaTeX until ReportLab phase. |
| Compile PDF | `generate_pdf` | Renderer module | Pending | Uses external LaTeX command. |
| Delete temporary Qualys report | `delete_report` | `was_reports.report_data` | Started | Migrated helper returns success state. It is not yet wired into the legacy report execution path. |
| Encrypt final PDF | `encrypt_pdf` | PDF security helper | Started | Current CLI supplies Postgres-managed password to legacy encrypt behavior. |

## Original Alternate Workflows

These workflows are part of the original codebase and must receive explicit
migration treatment. Some may become separate administrative commands rather
than scheduled batch behavior.

| Legacy Option | Legacy Function Path | Target Boundary | Status | Notes |
| --- | --- | --- | --- | --- |
| `--xml` | `create_webapp_report_v2`, `get_report`, XML file write | `was-export-xml` | Started | Noninteractive container command generates sanitized XML for a stakeholder tag and deletes the temporary Qualys report. Live Qualys validation remains pending. |
| `--details-only` | `get_app_id`, `create_details_report`, `download_report` | Detail report command | Pending | Generates detail reports for a list of web apps. |
| `--list` | `app_numbering` | Inventory command | Pending | Lists WAS stakeholders and web app counts. |
| `--add-tag` | `get_app_id`, `get_tag_id`, `add_tag` | Admin command | Pending | Mutates Qualys tags and needs operator controls. |
| `--remove-tag` | `get_app_id`, `get_tag_id`, `remove_tag` | Admin command | Pending | Mutates Qualys tags and needs operator controls. |
| `--false-positive` | `falsepos` | Admin command | Pending | Mutates Qualys finding status. |
| `--reactivate` | `reactivate_webapp` | Admin command | Pending | Reactivates web apps and adds tags. |
| `--delete-webapp` | `delete_webapp` | Admin command | Pending | Destructive operation requiring confirmation and audit logging. |
| `--update-tracker` | `update_tracker` import | `was-update-tracker` | Started | Container command runs the legacy tracker flow and writes rows to Postgres. Qualys webapp deletion requires `--delete-apps`. |
| `--check-dates` | Documented but not implemented in observed `main` path | Scheduling report command | Pending | Confirm whether this existed elsewhere in the original export. |
| `--mailer` | Documented but not implemented in observed `main` path | `was-mailer` | Started | Modernized mailer exists, but exact legacy behavior still needs comparison. |
| `--check-passwords` | Documented but not implemented in observed `main` path | Password audit command | Pending | Should verify all due stakeholders have stored passwords. |
| `--onboard` | Documented as not functional | Onboarding command or remove by approval | Pending | Keep documented until stakeholders decide whether to implement. |
| `--noninteractive` | Commented-out batch Excel path | `was-report-batch` | Started | Replaced by Postgres due-report selection. Confirm no template-specific behavior remains required. |

## Supporting Legacy Files

| File | Purpose | Migration Status | Notes |
| --- | --- | --- | --- |
| `was_report/NEW_BIG.mustache` | LaTeX report template | Preserve | Must remain unchanged until the renderer migration. |
| `was_report/assets/was_report.xml` | Qualys report request template | Pending | Move template ID and path handling into config or package data. |
| `was_report/assets/was_report_details.xml` | Qualys detail report request template | Pending | Move template ID and path handling into config or package data. |
| `was_report/redact_qualys.py` | Detail PDF redaction helper | Pending | Wrap in a testable PDF redaction boundary. |
| `was_report/pdf_redactor.py` | PDF redaction implementation | Pending | Review dependency and behavior before moving. |
| `was_report/assets/*` | PDF backgrounds, logos, and graph placeholders | Preserve | Required to keep current visual output. |

## Next Migration Order

1. Move read-only Qualys calls used by normal report generation behind
   `was_reports.qualys_client`.
2. Add XML fixtures for report creation, report download, app count, tag lookup,
   and web app search responses.
3. Extract report-data retrieval into a service that returns raw XML and detail
   artifact paths without changing output.
4. Extract transformation functions into testable modules using fixture XML.
5. Extract PDF rendering and encryption into modules while preserving the
   Mustache and LaTeX output.
6. Migrate alternate XML/detail/inventory/admin workflows into separate CLI
   commands.
7. Replace any remaining workbook, DynamoDB, direct `requests`, and import-time
   Qualys connection behavior.
