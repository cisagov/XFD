# Qualys API Inventory

This document tracks the Qualys API calls used by the WAS reporting project.
Keep this file updated whenever WAS API usage changes.

## Documentation Sources

- Qualys WAS API documentation: <https://docs.qualys.com/en/was/api/get_started/get_started.htm>
- Qualys release notes: <https://www.qualys.com/documentation/release-notes>
- Qualys WAS and TotalAppSec release notes: <https://docs.qualys.com/en/tas/release-notes/web_application_scanning/web_application_scanning.htm>
- Qualys API notifications: <https://community.qualys.com/community/developer/notifications-api>

## Current Modernization Position

- The active container entrypoint calls `was-report-batch`.
- `was-report-batch` selects due stakeholders from Postgres and delegates one
  report at a time to `was-reports`.
- `was-reports` executes only the production implementation under
  `src/was_reports`.
- `was_reports.qualys.qualys_client` is the WAS-owned API boundary for all
  production Qualys calls.
- The legacy report output format remains unchanged until the later ReportLab
  migration phase.

## Required For Report Generation

These calls are required for the current single-page PDF report generation path.

| Endpoint | Method | Legacy Function | Purpose | Payload Source | Response Use | Migration Risk |
| --- | --- | --- | --- | --- | --- | --- |
| `/create/was/report` | `POST` | `create_webapp_report_v2` | Creates the XML WAS report for a stakeholder tag. | `src/was_reports/resources/assets/was_report.xml` with template, target tag, report name, and XML format. | Reads `responseCode` and `data.Report.id`. | High, template IDs and response fields must be verified against current Qualys WAS API docs. |
| `/download/was/report/<id>` | `GET` | `get_report` | Downloads generated XML report content. | Report ID from `/create/was/report`. | XML is parsed into findings, charts, summaries, and appendix data. | High, XML schema changes can alter report output. |
| `/count/was/finding` | Not explicitly set by legacy call | `max_age` | Counts open critical and urgent findings by date range. | XML filter payload built in code. | Used for max-age calculations and trend context. | Medium, date filters and finding status semantics must be verified. |
| `/search/was/finding` | `POST` | `get_ssn_and_cc` | Searches findings that indicate SSN or credit-card exposure. | XML filter payload built in code for relevant QIDs. | Parses payload request links for sensitive-data appendix fields. The exact HTTP 400 `Module is not supported for this agent` response is logged and represented as unavailable data so report generation can continue. Other API errors remain fatal. | High, sensitive-data handling and QID assumptions need explicit validation. |
| `/search/was/webapp` | `POST` | `get_app_id`, `app_overview_table` | Finds web applications by URL or stakeholder tag. | XML filter payload built in code. | Reads web app IDs, URLs, scopes, and operating-system metadata. | Medium, output fields may vary by account permissions and scope. |

## Required For Detail Attachments

These calls support detail-report PDF attachments created by the production
report service.

| Endpoint | Method | Legacy Function | Purpose | Payload Source | Response Use | Migration Risk |
| --- | --- | --- | --- | --- | --- | --- |
| `/create/was/report` | `POST` | `create_details_report` | Creates a Qualys PDF detail report for a tag or web application ID. | Production templates under `src/was_reports/resources/assets`. | Reads `responseCode` and `data.Report.id`. | High, template ID `2201149` should be confirmed for the target Qualys subscription. |
| `/download/was/report/<id>` | `GET` through the WAS direct-download boundary | `download_report` | Downloads the Qualys-generated PDF detail report. | Environment-backed credentials and the shared timeout and retry policy. | Writes detail PDF, watermarks it, and redacts it. | Medium, direct-download authentication and response handling require live validation. |
| `/delete/was/report/<id>` | Not explicitly set by legacy call | `delete_report` | Deletes temporary Qualys reports after use. | Report ID. | Used as cleanup. | Medium, cleanup failure could leave reports in Qualys. |
| `/status/was/report/<id>` | `GET` | `get_report_status` | Checks generated report status. | Report ID. | Determines when report download can proceed. | Medium, polling states and timeout behavior need explicit handling. |

## Migrated API Boundary Coverage

The following original call patterns have WAS-owned wrappers in
`was_reports.qualys.report_data`. These wrappers are used by the production
report and tracker workflows and are covered by unit tests.

| Legacy Function | Migrated Function |
| --- | --- |
| `get_tag_id` | `report_data.get_tag_id` |
| `app_count` | `report_data.count_webapps` |
| `create_webapp_report_v2` | `report_data.create_webapp_xml_report` |
| `create_details_report` | `report_data.create_detail_pdf_report` |
| `get_report` | `report_data.get_report_xml` |
| `get_report_status` | `report_data.get_report_status` |
| `delete_report` | `report_data.delete_report` |
| `download_report` direct HTTP download | `detail_reports.download_detail_pdf` |
| `download_report` status polling | `detail_reports.wait_for_report_completion` |
| `qualys_redact` | `pdf_helpers.redact_qualys_pdf` |
| `watermarker` | `pdf_helpers.apply_watermark` |
| `unfirstpagify` | `pdf_helpers.remove_first_page` |

## Administrative And Inventory Coverage

These original operations are either exposed through production commands or
explicitly awaiting a stakeholder decision. They do not execute historical
source files.

| Endpoint | Method | Legacy Function | Purpose | Migration Recommendation |
| --- | --- | --- | --- | --- |
| `/search/am/tag` | `POST` | `tag_dict_v2`, `app_find` | Looks up Qualys asset-management tags and descriptions. | Implemented through `was-inventory`, report generation, and guarded `was-admin` commands. |
| `/count/was/webapp` | `POST` | `app_count`, `app_numbering` | Counts web applications by tag. | Implemented through `was-inventory`, report generation, and tracker refresh. |
| `/update/was/webapp/<id>` | `POST` | `add_tag`, `remove_tag` | Mutates Qualys web application tags. | Implemented through `was-admin add-tag` and `was-admin remove-tag`, both requiring explicit confirmation. |
| `/ignore/was/finding` | `POST` | `falsepos` | Marks a finding as a false positive. | Implemented through `was-admin false-positive` with explicit confirmation. |
| `/create/was/webapp` | `POST` | `reactivate_webapp` | Reactivates a web application with a replacement tag set. | Implemented through `was-admin reactivate` with explicit confirmation. |
| `/delete/was/webapp` | `POST` | `delete_webapp` | Removes a web application from the Qualys subscription. | Implemented through `was-admin delete-webapp` and the opt-in tracker `--delete-apps` path. |
| `/user.php` | Original method not explicit | `list_users` | Lists Qualys users. | Not exposed because no active original command called this function. Add a restricted command only if stakeholders confirm an operational need. |

## Current Concerns To Resolve

- Qualys credentials are read from WAS environment constants. During local
  execution those constants come from `backend/was/.env`; production should use
  AWS Secrets Manager or SSM Parameter Store to inject the same constants at
  runtime.
- Some report downloads use direct `requests.Session` authentication instead of
  the `qualysapi` connection. These downloads use the same WAS-owned timeout and
  retry policy, but authentication remains specific to the direct download path.
- Qualys mutation commands are separated from report generation and require
  explicit confirmation. Durable centralized audit retention still depends on
  the deployed logging configuration.
- Report template IDs remain constants for output compatibility. Validate them
  against each target Qualys subscription before deployment.
- Qualys XML response parsing is tightly coupled to current response shape. Any
  API update should be tested with representative XML fixtures before deployment.

## Retry And Timeout Policy

- Read-safe `search`, `count`, `status`, and `download` operations retry
  transient connection errors, request timeouts, HTTP `429`, and HTTP `500`,
  `502`, `503`, and `504` responses.
- Retries use capped exponential backoff with jitter. A Qualys `Retry-After`
  response is honored up to `WAS_QUALYS_RETRY_MAX_DELAY_SECONDS`.
- Qualys create, update, ignore, and delete operations remain single-attempt to
  prevent duplicate reports or repeated administrative side effects.
- Every production request has a bounded timeout, and detail-report status
  polling has a separate total timeout.
- Retry logs include the endpoint, attempt number, and delay. Request payloads,
  response bodies, and credentials are not logged by the WAS-owned client.

## Update Checklist

When a Qualys API call changes, update this document with:

- Endpoint path and HTTP method.
- Calling module and function.
- Request payload source.
- Expected response fields.
- Whether the call reads data or mutates Qualys state.
- Required Qualys account permission.
- Test fixture or mock coverage added for the change.
