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
- Keep Qualys data calls behind `was_reports.qualys.qualys_client`.
- Keep stakeholder, scheduling, report-run, and password state in Postgres.
- Keep mutating Qualys operations separate from scheduled report generation.
- Add tests before replacing legacy behavior.

The observed production invocation uses only `-t` for the customer short name
and `--encrypt` for the report password. Other legacy flags are not part of the
active report-generation contract unless stakeholders explicitly restore them.

## Current Modernized Entry Points

| Capability | Current Modernized Entry Point | Status | Notes |
| --- | --- | --- | --- |
| Scheduled report batch | `was-report-batch` | Started | Selects due stakeholders from Postgres and atomically claims each stakeholder schedule before generation. Active schedule uniqueness prevents duplicate concurrent runs. |
| Single stakeholder report | `was-reports --tag` | Active | Runs the WAS-owned production pipeline. The frozen creator requires `--use-legacy-pipeline`. |
| Report password creation | `was-reports --create-missing-password` | Started | Generates and stores customer report passwords in Postgres. |
| Report password rotation | `was-reports --change-password` | Started | Generates a new password for the supplied stakeholder tag. |
| Report artifact storage | `was_reports.storage.s3_reports` | Active | Scheduled encrypted PDFs use run-specific S3 keys. The S3 URI is stored in `was_report_runs.output_path`; explicit local mode remains available for development. |
| Report email delivery | `was-mailer` | Active | Atomically claims each completed run, downloads its PDF from the configured S3 bucket into a private temporary directory, sends it through SES, and removes the local copy. Uncertain post-SES database failures require manual reconciliation instead of automatic retry. |
| Daily report tracker persistence | `was-update-tracker` | Started | Container command runs the legacy tracker flow and writes rows to Postgres. Optional `--tag` scopes scan retrieval and database writes after schedule discovery. Qualys webapp deletion requires `--delete-apps`. |
| Daily tracker assignees | `was_reports.data.assignees` | Started | Lookup table, seed SQL, and upsert helper exist. |
| Stakeholder inventory | `was-inventory` | Started | Lists child tags under `WAS_CUSTOMERS` and their web application counts. Live Qualys validation remains pending. |

## Original Report Generation Path

This path must be fully migrated before the legacy report creator can be
retired.

| Legacy Step | Legacy Function | Target Module | Status | Notes |
| --- | --- | --- | --- | --- |
| Validate operator arguments | `main` | `was_reports.commands.report_generator` | Active | Current CLI validates the tag and accepts the observed `-t` and `--encrypt` inputs. The production pipeline is the default. The compatibility subprocess receives its password through standard input and requires `--use-legacy-pipeline`. |
| Count web applications | `app_count` | `was_reports.reporting.report_retrieval` | Active | Included in the tested WAS-owned production retrieval sequence. |
| Resolve Qualys tag ID | `get_tag_id` | `was_reports.reporting.report_retrieval` | Active | Included in the tested WAS-owned production retrieval sequence. |
| Create detail report when app count is below threshold | `create_details_report` | `was_reports.reporting.report_retrieval` | Started | The legacy threshold of fewer than 35 web applications is preserved in the tested retrieval sequence. |
| Download detail report PDF | `download_report` | `was_reports.reporting.detail_reports` | Active | Direct download and post-processing are called by the WAS-owned production retrieval sequence. |
| Watermark detail report | `watermarker` | `was_reports.reporting.pdf_helpers` | Started | Migrated helper exists. It is not yet wired into the legacy execution path. |
| Remove first page from detail report | `unfirstpagify` | `was_reports.reporting.pdf_helpers` | Started | Migrated helper exists. It is not yet wired into the legacy execution path. |
| Redact Qualys detail PDF | `qualys_redact` | `was_reports.reporting.pdf_helpers` | Started | Migrated helper wraps `redact_qualys.py`. It is not yet wired into the legacy execution path. |
| Create XML web application report | `create_webapp_report_v2` | `was_reports.reporting.report_retrieval` | Started | Included in the tested retrieval sequence. Template ID remains fixed for compatibility. |
| Download XML report | `get_report` | `was_reports.reporting.report_retrieval` | Started | Included in the tested retrieval sequence with cleanup on download or downstream processing failures. |
| Parse XML findings | `csv_genner`, finding classes | `was_reports.reporting.report_transformer` | Active | Finding and QID models are used by production with representative XML fixture coverage. |
| Generate CSV artifacts | `csv_genner` | `was_reports.reporting.report_transformer` | Started | Legacy filenames, columns, fixed-finding exclusion, severity list, age list, and payload formatting are preserved in tests. |
| Calculate graph and summary metrics | `get_summary_info`, `totalgraphgen`, `qid_counter`, `percent_donut` | `was_reports.reporting.report_metrics` | Started | Global summary, severity totals, status counts, group and OWASP mappings, cumulative monthly trends, colors, and fixed percentage are fixture-tested. |
| Retrieve report-card finding ages | `max_age` | `was_reports.qualys.finding_ages` | Active | Critical and urgent searches preserve the tag, active-status, severity, false-positive, and one-result filters. Missing severities are handled independently instead of hiding an available age. |
| Render graph images | `owasp_graph_gen`, `vulnsbygroupgraphgen`, `percent_donut`, `plot_histogram`, `monthly_trend` | `was_reports.reporting.chart_renderer` | Active | All five production PNG outputs retain legacy filenames, labels, colors, dimensions, and ordering. Deterministic render tests verify valid PNG artifacts and figure cleanup. |
| Generate attachment artifacts | `webapp_vuln_table`, `app_overview_table`, `return_links`, `return_emails`, `return_rejects`, `get_ssn_and_cc` | `was_reports.reporting.report_artifacts` | Active | XML-derived CSV attachments and the two filtered Qualys sensitive-finding queries preserve legacy filenames and report-template inputs. The known unsupported-module response logs a warning and writes explicit unavailable markers. |
| Assemble report template data | `get_summary_info`, `generate_full` | `was_reports.reporting.report_template_data` | Active | All Mustache placeholders are assembled from production metrics and artifact filenames, including legacy colors, severity totals, report-card age positions, and the fewer-than-35-app detail attachment rule. |
| Generate report body | `mustache_generate`, `generate_full` | `was_reports.reporting.latex_renderer` | Started | Mustache rendering, legacy filename construction, HTML entity decoding, LaTeX escaping, and title-width thresholds are extracted. Template-data assembly and production cutover remain pending. |
| Compile PDF | `generate_pdf`, `cleanup` | `was_reports.reporting.latex_renderer` | Started | Runs two checked XeLaTeX passes and removes only known temporary files. The Docker image retains `texlive-xetex`; production cutover remains pending. |
| Orchestrate production report pipeline | `generate_full` and active `main` path | `was_reports.reporting.report_service` | Active | Connects managed Qualys retrieval, CSV transformation, metrics, charts, attachments, finding ages, template assembly, LaTeX rendering, and atomic password encryption. Each run uses a private production-resource copy. Postgres schedule claims prevent duplicate container runs, while the local lock protects writes within one output filesystem. Report comparison remains available while equivalence review continues. |
| Delete temporary Qualys report | `delete_report` | `was_reports.reporting.report_retrieval` | Active | Context-managed retrieval guarantees cleanup after downstream processing. |
| Encrypt final PDF | `encrypt_pdf` | `was_reports.reporting.pdf_security` | Active | Validates the stored password and atomically replaces the unencrypted PDF with PikePDF revision-4 owner and user encryption. Failure preserves the original file. |

## Original Alternate Workflows

These workflows are part of the original codebase and must receive explicit
migration treatment. Some may become separate administrative commands rather
than scheduled batch behavior.

| Legacy Option | Legacy Function Path | Target Boundary | Status | Notes |
| --- | --- | --- | --- | --- |
| `--xml` | `create_webapp_report_v2`, `get_report`, XML file write | `was-export-xml` | Started | Noninteractive container command generates sanitized XML for a stakeholder tag and deletes the temporary Qualys report. Live Qualys validation remains pending. |
| `--details-only` | `get_app_id`, `create_details_report`, `download_report` | Deprecated file-driven workflow | Deprecated | The operator-supplied CSV mechanism is deprecated. If the capability is retained, discover web applications by stakeholder tag through Qualys instead of requiring a local list file. |
| `--list` | `app_numbering` | `was-inventory` | Started | Read-only container command lists WAS stakeholder tags and web application counts. |
| `--add-tag` | `get_app_id`, `get_tag_id`, `add_tag` | `was-admin add-tag` | Started | Accepts an exact URL and tag directly, safely builds XML, and requires `--confirm`. Live Qualys validation remains pending. |
| `--remove-tag` | `get_app_id`, `get_tag_id`, `remove_tag` | `was-admin remove-tag` | Started | Accepts an exact URL and tag directly, safely builds XML, and requires `--confirm`. Live Qualys validation remains pending. |
| `--false-positive` | `falsepos` | `was-admin false-positive` | Started | Accepts one finding ID and comment directly, safely builds XML, and requires `--confirm`. Live Qualys validation remains pending. |
| `--reactivate` | `reactivate_webapp` | `was-admin reactivate` | Started | Accepts one exact URL and repeated tag names, replaces the tag set, and requires `--confirm`. Live Qualys validation remains pending. |
| `--delete-webapp` | `delete_webapp` | `was-admin delete-webapp` | Started | Requires the operator to repeat the exact URL before removing the web app from the Qualys subscription. Durable centralized audit retention depends on deployment logging. Live Qualys validation remains pending. |
| `--update-tracker` | `update_tracker` import | `was-update-tracker` | Started | Container command runs the legacy tracker flow and writes rows to Postgres. Qualys webapp deletion requires `--delete-apps`. |
| `--check-dates` | Documented but not implemented in observed `main` path | Scheduling report command | Pending | Confirm whether this existed elsewhere in the original export. |
| `--mailer` | Documented but not implemented in observed `main` path | `was-mailer` | Started | Modernized mailer exists, but exact legacy behavior still needs comparison. |
| `--check-passwords` | Documented but not implemented in observed `main` path | Password audit command | Pending | Should verify all due stakeholders have stored passwords. |
| `--onboard` | Documented as not functional | Onboarding command or remove by approval | Pending | Keep documented until stakeholders decide whether to implement. |
| `--noninteractive` | Commented-out batch Excel path | `was-report-batch` | Started | Replaced by Postgres due-report selection. Confirm no template-specific behavior remains required. |

## Supporting Legacy Files

| File | Purpose | Migration Status | Notes |
| --- | --- | --- | --- |
| `was_report/NEW_BIG.mustache` | LaTeX report template | Active copy | The production copy is under `src/was_reports/resources`; the frozen source remains for comparisons. |
| `was_report/assets/was_report.xml` | Qualys report request template | Active copy | The production copy is under `src/was_reports/resources/assets`. |
| `was_report/assets/was_report_details.xml` | Qualys detail report request template | Active copy | The production copy is under `src/was_reports/resources/assets`. |
| `was_report/redact_qualys.py` | Detail PDF redaction helper | Copied | An unchanged package copy exists for migration compatibility; replacement of the subprocess boundary remains pending. |
| `was_report/pdf_redactor.py` | PDF redaction implementation | Copied | An unchanged package copy exists for migration compatibility; dependency review remains pending. |
| `was_report/assets/*` | PDF backgrounds, logos, fonts, and graph placeholders | Active copies | Production copies are staged in Docker under `/WAS_REPORT_RESOURCES`; the frozen legacy root remains available for comparison. |

## Next Migration Order

1. Move read-only Qualys calls used by normal report generation behind
   `was_reports.qualys.qualys_client`.
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

## Validation Checkpoints

- Offline extracted-pipeline smoke test: available through
  `scripts/offline_pipeline_smoke.py`; it performs real chart, Mustache,
  XeLaTeX, encryption, and publication work without Qualys or Postgres.
- Live Qualys equivalence test: pending valid nonproduction credentials and an
  approved stakeholder tag. Compare the legacy and extracted encrypted PDFs,
  attachments, metrics, charts, report metadata, and Qualys cleanup behavior
  with `was-compare-reports` before changing the default route. The offline
  PDF contains all eight expected CSVs as page-level `/FileAttachment`
  annotations rather than a document `/EmbeddedFiles` names tree; the
  comparator validates both representations. Follow
  `docs/live_qualys_equivalence_runbook.md` for execution, evidence, failure,
  and cutover requirements.

Legacy `read_file()` CSV inputs are deprecated. Administrative capabilities
that remain required should accept explicit validated arguments or query
authoritative data sources rather than depend on operator-managed files in
`docs/`.
