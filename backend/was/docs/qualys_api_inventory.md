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
- `was-reports` still executes the legacy report creator as a subprocess.
- `was_reports.qualys_client` is the WAS-owned API boundary for new or migrated
  Qualys calls.
- The legacy report output format remains unchanged until the later ReportLab
  migration phase.

## Required For Report Generation

These calls are required for the current single-page PDF report generation path.

| Endpoint | Method | Legacy Function | Purpose | Payload Source | Response Use | Migration Risk |
| --- | --- | --- | --- | --- | --- | --- |
| `/create/was/report` | `POST` | `create_webapp_report_v2` | Creates the XML WAS report for a stakeholder tag. | `was_report/assets/was_report.xml` with template, target tag, report name, and XML format. | Reads `responseCode` and `data.Report.id`. | High, template IDs and response fields must be verified against current Qualys WAS API docs. |
| `/download/was/report/<id>` | `GET` | `get_report` | Downloads generated XML report content. | Report ID from `/create/was/report`. | XML is parsed into findings, charts, summaries, and appendix data. | High, XML schema changes can alter report output. |
| `/count/was/finding` | Not explicitly set by legacy call | `max_age` | Counts open critical and urgent findings by date range. | XML filter payload built in code. | Used for max-age calculations and trend context. | Medium, date filters and finding status semantics must be verified. |
| `/search/was/finding` | `POST` | `get_ssn_and_cc` | Searches findings that indicate SSN or credit-card exposure. | XML filter payload built in code for relevant QIDs. | Parses payload request links for sensitive-data appendix fields. | High, sensitive-data handling and QID assumptions need explicit validation. |
| `/search/was/webapp` | `POST` | `get_app_id`, `app_overview_table` | Finds web applications by URL or stakeholder tag. | XML filter payload built in code. | Reads web app IDs, URLs, scopes, and operating-system metadata. | Medium, output fields may vary by account permissions and scope. |

## Required For Detail Attachments

These calls support detail-report PDF attachments created by the legacy script.

| Endpoint | Method | Legacy Function | Purpose | Payload Source | Response Use | Migration Risk |
| --- | --- | --- | --- | --- | --- | --- |
| `/create/was/report` | `POST` | `create_details_report` | Creates a Qualys PDF detail report for a tag or web application ID. | `was_report/assets/was_report.xml` or `was_report/assets/was_report_details.xml`. | Reads `responseCode` and `data.Report.id`. | High, template ID `2201149` should be confirmed for the target Qualys subscription. |
| `/download/was/report/<id>` | `GET` outside `qgc` | `download_report` | Downloads the Qualys-generated PDF detail report. | Direct `requests.Session` call using credentials from `[info]`. | Writes detail PDF, watermarks it, and redacts it. | High, this bypasses `qualysapi` and should move behind the WAS-owned client boundary. |
| `/delete/was/report/<id>` | Not explicitly set by legacy call | `delete_report` | Deletes temporary Qualys reports after use. | Report ID. | Used as cleanup. | Medium, cleanup failure could leave reports in Qualys. |
| `/status/was/report/<id>` | `GET` | `get_report_status` | Checks generated report status. | Report ID. | Determines when report download can proceed. | Medium, polling states and timeout behavior need explicit handling. |

## Migrated API Boundary Coverage

The following legacy call patterns now have WAS-owned wrappers in
`was_reports.report_data`. These wrappers are covered by unit tests but are not
yet wired into the legacy report execution path.

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

## Legacy Operations Requiring Later Migration

These calls exist in the original WAS code and must be accounted for in the WAS
modernization effort. They are not part of the first scheduled report-generation
path being migrated, but they should not be treated as out of scope. Each one
needs a later migration decision, test coverage, and an operator or service
boundary before the legacy script is retired.

| Endpoint | Method | Legacy Function | Purpose | Migration Recommendation |
| --- | --- | --- | --- | --- |
| `/search/am/tag` | `POST` | `tag_dict_v2`, `app_find` | Looks up Qualys asset-management tags and descriptions. | Migrate behind a WAS-owned read-only Qualys tag service if stakeholder metadata or tag reconciliation still depends on Qualys. |
| `/count/was/webapp` | `POST` | `app_count`, `app_numbering` | Counts web applications by tag. | Migrate as a read-only inventory or validation function and compare against `was_stakeholders.num_web_apps`. |
| `/update/was/webapp/<id>` | `POST` | `add_tag`, `remove_tag`, `falsepos`, `reactivate_webapp` | Mutates Qualys web application settings, tags, false positives, or status. | Migrate behind a separate administrative command or service path with explicit authorization, audit logging, and least-privilege IAM or secret access. |
| `/delete/was/webapp/<id>` | `POST` | `delete_webapp` | Deletes web applications from Qualys. | Migrate only as a separate destructive administrative operation with confirmation, audit logging, and restricted operator permissions. |
| `/count/was/webapp` plus repeated tag iteration | `POST` | `app_numbering`, `app_numbering_V2` | Generates web application counts for all tags. | Migrate as a reconciliation command if still needed for stakeholder onboarding or scheduled data quality checks. |
| `/user.php` | Not explicitly set by legacy call | `list_users` | Lists Qualys users. | Migrate only if administrative visibility is required. Keep separate from report generation and restrict access. |

## Current Concerns To Resolve

- Qualys credentials are read from WAS environment constants. During local
  execution those constants come from `backend/was/.env`; production should use
  AWS Secrets Manager or SSM Parameter Store to inject the same constants at
  runtime.
- The legacy script creates `qgc` at import time. Migrated code should create
  clients inside functions so tests do not connect to Qualys.
- Some report downloads use direct `requests.Session` authentication instead of
  the `qualysapi` connection. This should be consolidated behind
  `was_reports.qualys_client`.
- Several Qualys endpoints mutate assets or delete records. Those should be
  migrated into separate administrative paths with explicit authorization,
  audit logging, and restricted operator access.
- Template IDs are hardcoded in the legacy script. The modernization should move
  those IDs into validated configuration.
- Qualys XML response parsing is tightly coupled to current response shape. Any
  API update should be tested with representative XML fixtures before deployment.

## Update Checklist

When a Qualys API call changes, update this document with:

- Endpoint path and HTTP method.
- Calling module and function.
- Request payload source.
- Expected response fields.
- Whether the call reads data or mutates Qualys state.
- Required Qualys account permission.
- Test fixture or mock coverage added for the change.
