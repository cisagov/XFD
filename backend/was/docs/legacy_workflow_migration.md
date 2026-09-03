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
| Scheduled report batch | `was-report-batch` | Complete | Selects due stakeholders from Postgres and atomically claims each stakeholder schedule before generation. Active schedule uniqueness prevents duplicate concurrent runs. |
| Single stakeholder report | `was-reports --tag` | Complete | Runs only the WAS-owned production pipeline. |
| Tracked manual stakeholder report | `make manual-report TAG="CUSTOMER_TAG"` | Active | Reuses or safely retries one manual tracker claim, uploads the encrypted PDF, sends it through SES, and stamps the tracker sent date only after accepted delivery. |
| Report password creation | `was-reports --create-missing-password` | Complete | Generates and stores customer report passwords in Postgres. |
| Report password rotation | `was-reports --change-password` | Complete | Generates a new password for the supplied stakeholder tag. |
| Report artifact storage | `was_reports.storage.s3_reports` | Active | Scheduled encrypted PDFs use run-specific S3 keys. The S3 URI is stored in `was_report_runs.output_path`; explicit local mode remains available for development. |
| Report email delivery | `was-mailer` | Active | Atomically claims each completed run, downloads its PDF from the configured S3 bucket into a private temporary directory, sends it through SES, and removes the local copy. Uncertain post-SES database failures require manual reconciliation instead of automatic retry. |
| Daily report tracker persistence | `was-update-tracker` | Complete | The WAS-owned tracker discovers Qualys schedules and scans, consolidates scan slices, writes Postgres rows, supports exact `--tag` scoping, and requires `--delete-apps` for Qualys webapp deletion. It does not read or create `was_config.txt`. |
| Manual tracker queue | `make tracker-table REPORT_STATUS=manual` | Active | Displays manual tracker rows across all assignees or for one selected assignee and date window. |
| Persisted report errors | `make report-errors` | Active | Displays bounded generation and SES error summaries from Postgres without exposing passwords or recipient addresses. |
| Stakeholder contact maintenance | `was-stakeholders update-contacts` | Active | Updates only explicitly supplied POC and email fields after operator confirmation. |
| Stakeholder CSV export | `make stakeholder-export` | Active | Exports non-secret fields by default. Report-password export requires separate explicit sensitive-data confirmation. |
| Manual tracker sent-date reconciliation | `make tracker-mark-sent` | Active | Sets a sent date only for an unsent tracker row already classified for manual handling. |
| Interactive operator menu | `make menu` | Active | Provides guided numbered access to existing report, tracker, stakeholder, and safe Qualys commands without duplicating business logic. |
| Daily tracker assignees | `was_reports.data.assignees` | Complete | Reads active assignees from Postgres and distributes tracker rows in stable round-robin order. |
| Stakeholder inventory | `was-inventory` | Implemented | Lists child tags under `WAS_CUSTOMERS` and their web application counts. Live Qualys validation remains pending. |

## Original Report Generation Path

This path is implemented under `src/was_reports`. The historical report creator
is retained only as local reference material and is not packaged or executable.

| Legacy Step | Legacy Function | Target Module | Status | Notes |
| --- | --- | --- | --- | --- |
| Validate operator arguments | `main` | `was_reports.commands.report_generator` | Complete | Current CLI validates the tag, accepts the observed `-t` and `--encrypt` inputs, and exposes no legacy execution route. |
| Count web applications | `app_count` | `was_reports.reporting.report_retrieval` | Active | Included in the tested WAS-owned production retrieval sequence. |
| Resolve Qualys tag ID | `get_tag_id` | `was_reports.reporting.report_retrieval` | Active | Included in the tested WAS-owned production retrieval sequence. |
| Create detail report when app count is below threshold | `create_details_report` | `was_reports.reporting.report_retrieval` | Active | The threshold of fewer than 35 web applications is preserved in the tested production retrieval sequence. |
| Download detail report PDF | `download_report` | `was_reports.reporting.detail_reports` | Active | Direct download and post-processing are called by the WAS-owned production retrieval sequence. |
| Watermark detail report | `watermarker` | `was_reports.reporting.pdf_helpers` | Active | Called by the production detail-report post-processing path. |
| Remove first page from detail report | `unfirstpagify` | `was_reports.reporting.pdf_helpers` | Active | Called by the production detail-report post-processing path. |
| Redact Qualys detail PDF | `qualys_redact` | `was_reports.reporting.pdf_helpers` | Active | The production helper uses the copied redaction implementation under `src/was_reports/resources`. |
| Create XML web application report | `create_webapp_report_v2` | `was_reports.reporting.report_retrieval` | Active | Included in the tested production retrieval sequence. Template ID remains fixed for compatibility. |
| Download XML report | `get_report` | `was_reports.reporting.report_retrieval` | Active | Included in the tested production retrieval sequence with cleanup on download or downstream processing failures. |
| Parse XML findings | `csv_genner`, finding classes | `was_reports.reporting.report_transformer` | Active | Finding and QID models are used by production with representative XML fixture coverage. |
| Generate CSV artifacts | `csv_genner` | `was_reports.reporting.report_transformer` | Active | Original filenames, columns, fixed-finding exclusion, severity list, age list, and payload formatting are preserved in tests. |
| Calculate graph and summary metrics | `get_summary_info`, `totalgraphgen`, `qid_counter`, `percent_donut` | `was_reports.reporting.report_metrics` | Active | Global summary, severity totals, status counts, group and OWASP mappings, cumulative monthly trends, colors, and fixed percentage are fixture-tested. |
| Retrieve report-card finding ages | `max_age` | `was_reports.qualys.finding_ages` | Active | Critical and urgent searches preserve the tag, active-status, severity, false-positive, and one-result filters. Missing severities are handled independently instead of hiding an available age. |
| Render graph images | `owasp_graph_gen`, `vulnsbygroupgraphgen`, `percent_donut`, `plot_histogram`, `monthly_trend` | `was_reports.reporting.chart_renderer` | Active | All five production PNG outputs retain legacy filenames, labels, colors, dimensions, and ordering. Deterministic render tests verify valid PNG artifacts and figure cleanup. |
| Generate attachment artifacts | `webapp_vuln_table`, `app_overview_table`, `return_links`, `return_emails`, `return_rejects`, `get_ssn_and_cc` | `was_reports.reporting.report_artifacts` | Active | XML-derived CSV attachments and the two filtered Qualys sensitive-finding queries preserve legacy filenames and report-template inputs. The known unsupported-module response logs a warning and writes explicit unavailable markers. |
| Assemble report template data | `get_summary_info`, `generate_full` | `was_reports.reporting.report_template_data` | Active | All Mustache placeholders are assembled from production metrics and artifact filenames, including legacy colors, severity totals, report-card age positions, and the fewer-than-35-app detail attachment rule. |
| Generate report body | `mustache_generate`, `generate_full` | `was_reports.reporting.latex_renderer` | Active | Mustache rendering, filename construction, HTML entity decoding, LaTeX escaping, and title-width thresholds run in production. |
| Compile PDF | `generate_pdf`, `cleanup` | `was_reports.reporting.latex_renderer` | Active | Production runs two checked XeLaTeX passes and removes only known temporary files. The Docker image retains `texlive-xetex`. |
| Orchestrate production report pipeline | `generate_full` and active `main` path | `was_reports.reporting.report_service` | Active | Connects managed Qualys retrieval, CSV transformation, metrics, charts, attachments, finding ages, template assembly, LaTeX rendering, and atomic password encryption. Each run uses a private production-resource copy. Postgres schedule claims prevent duplicate container runs, while the local lock protects writes within one output filesystem. Report comparison remains available while equivalence review continues. |
| Delete temporary Qualys report | `delete_report` | `was_reports.reporting.report_retrieval` | Active | Context-managed retrieval guarantees cleanup after downstream processing. |
| Encrypt final PDF | `encrypt_pdf` | `was_reports.reporting.pdf_security` | Active | Validates the stored password and atomically replaces the unencrypted PDF with PikePDF revision-4 owner and user encryption. Failure preserves the original file. |

## Original Alternate Workflows

These workflows are part of the original codebase and must receive explicit
migration treatment. Some may become separate administrative commands rather
than scheduled batch behavior.

| Legacy Option | Legacy Function Path | Target Boundary | Status | Notes |
| --- | --- | --- | --- | --- |
| `--xml` | `create_webapp_report_v2`, `get_report`, XML file write | `was-export-xml` | Implemented | Noninteractive container command generates sanitized XML for a stakeholder tag and deletes the temporary Qualys report. Live Qualys validation remains pending. |
| `--details-only` | `get_app_id`, `create_details_report`, `download_report` | Deprecated file-driven workflow | Deprecated | The operator-supplied CSV mechanism is deprecated. If the capability is retained, discover web applications by stakeholder tag through Qualys instead of requiring a local list file. |
| `--list` | `app_numbering` | `was-inventory` | Implemented | Read-only container command lists WAS stakeholder tags and web application counts. |
| `--add-tag` | `get_app_id`, `get_tag_id`, `add_tag` | `was-admin add-tag` | Implemented | Accepts an exact URL and tag directly, safely builds XML, and requires `--confirm`. Live Qualys validation remains pending. |
| `--remove-tag` | `get_app_id`, `get_tag_id`, `remove_tag` | `was-admin remove-tag` | Implemented | Accepts an exact URL and tag directly, safely builds XML, and requires `--confirm`. Live Qualys validation remains pending. |
| `--false-positive` | `falsepos` | `was-admin false-positive` | Implemented | Accepts one finding ID and comment directly, safely builds XML, and requires `--confirm`. Live Qualys validation remains pending. |
| `--reactivate` | `reactivate_webapp` | `was-admin reactivate` | Implemented | Accepts one exact URL and repeated tag names, replaces the tag set, and requires `--confirm`. Live Qualys validation remains pending. |
| `--delete-webapp` | `delete_webapp` | `was-admin delete-webapp` | Implemented | Requires the operator to repeat the exact URL before removing the web app from the Qualys subscription. Durable centralized audit retention depends on deployment logging. Live Qualys validation remains pending. |
| `--update-tracker` | `update_tracker` import | `was-update-tracker` | Complete | Container command runs the WAS-owned tracker service under `src/was_reports/tracker` and writes rows to Postgres. Qualys webapp deletion requires `--delete-apps`. |
| `--check-dates` | Documented but not implemented in observed `main` path | Scheduling report command | Pending | Confirm whether this existed elsewhere in the original export. |
| `--mailer` | Documented but not implemented in observed `main` path | `was-mailer` | Active | Production mailer sends S3-backed reports and tracker digests through SES with Postgres delivery tracking. |
| `--check-passwords` | Documented but not implemented in observed `main` path | Password audit command | Pending | Should verify all due stakeholders have stored passwords. |
| `--onboard` | Documented as not functional | Onboarding command or remove by approval | Pending | Keep documented until stakeholders decide whether to implement. |
| `--noninteractive` | Commented-out batch Excel path | `was-report-batch` | Complete | Replaced by Postgres due-report and recent-tracker selection. The commented workbook path was not active behavior. |

## Supporting Legacy Files

| File | Purpose | Migration Status | Notes |
| --- | --- | --- | --- |
| `was_report/NEW_BIG.mustache` | LaTeX report template | Complete | The production copy is under `src/was_reports/resources`; historical source is not packaged. |
| `was_report/assets/was_report.xml` | Qualys report request template | Complete | The production copy is under `src/was_reports/resources/assets`. |
| `was_report/assets/was_report_details.xml` | Qualys detail report request template | Complete | The production copy is under `src/was_reports/resources/assets`. |
| `was_report/redact_qualys.py` | Detail PDF redaction helper | Complete | The production-owned copy is under `src/was_reports/resources`; the historical source is not packaged. |
| `was_report/pdf_redactor.py` | PDF redaction implementation | Complete | The production-owned copy is under `src/was_reports/resources`; the historical source is not packaged. |
| `was_report/assets/*` | PDF backgrounds, logos, fonts, and graph placeholders | Complete | Production copies are staged from `src/was_reports/resources` under `/WAS_REPORT_RESOURCES`; the historical root is not packaged. |

## Remaining Modernization Work

1. Complete live nonproduction validation for commands marked `Implemented`.
2. Obtain stakeholder decisions for the documented but previously inactive
   `--check-dates`, `--check-passwords`, and `--onboard` options.
3. Replace Mustache and XeLaTeX with ReportLab only as a separate, reviewed
   change after output-equivalence requirements are defined.

## Validation Checkpoints

- Offline extracted-pipeline smoke test: available through
  `scripts/offline_pipeline_smoke.py`; it performs real chart, Mustache,
  XeLaTeX, encryption, and publication work without Qualys or Postgres.
- Live Qualys production validation: compare the generated encrypted PDF with
  an independently supplied approved baseline, including attachments, metrics,
  charts, report metadata, and Qualys cleanup behavior. The offline
  PDF contains all eight expected CSVs as page-level `/FileAttachment`
  annotations rather than a document `/EmbeddedFiles` names tree; the
  comparator validates both representations. Follow
  `docs/live_qualys_equivalence_runbook.md` for execution, evidence, failure,
  and cutover requirements.

Legacy `read_file()` CSV inputs are deprecated. Administrative capabilities
that remain required should accept explicit validated arguments or query
authoritative data sources rather than depend on operator-managed files in
`docs/`.
