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

The production boundary now logs endpoint and elapsed time without raw response
bodies or headers. XML payloads use serializer escaping and actual CDATA nodes,
not global entity replacement. The SSN and credit-card sensitive-finding
searches are temporarily disabled, as described below. XML export
uses a unique report name and waits for completion before downloading. Polling
continues through retryable transport/HTTP failures but stops on permanent
HTTP failures rather than waiting indefinitely. CSV attachments quote multiline
fields and neutralize spreadsheet formula prefixes. The PDF implementation
remains Mustache/XeLaTeX, with bounded, noninteractive rendering.

Tracked report creation first searches its stable run-specific name, then
persists `CREATE_REQUESTED` in the existing artifact status column before POST.
After an uncertain response, later attempts reconcile that name rather than
issuing another create request. Intent survives generation retries. If creation
never becomes visible, an operator must reconcile it; clearing the marker to
force another POST is not an automatic recovery action. XML and detail report
IDs are retained on retrieval/rendering failure and cleared only after a
confirmed cleanup following successful use.

## Required For Report Generation

These calls are required for the current single-page PDF report generation path.

| Endpoint | Method | Legacy Function | Purpose | Payload Source | Response Use | Migration Risk |
| --- | --- | --- | --- | --- | --- | --- |
| `/create/was/report` | `POST` | `create_webapp_report_v2` | Creates the XML WAS report for a stakeholder tag. | `src/was_reports/resources/assets/was_report.xml` with template, target tag, report name, and XML format. | Reads `responseCode` and `data.Report.id`. | High, template IDs and response fields must be verified against current Qualys WAS API docs. |
| `/search/was/report` | `POST` | Recovery addition | Finds a uniquely named report after an uncertain create response so the create request is not repeated. | Exact report name and format filters, without a preferences block, matching the documented Qualys filtered-search request. | Reads report ID, name, format, and status. | High, invalid search XML prevents safe timeout reconciliation and can encourage duplicate report creation. |
| `/download/was/report/<id>` | `GET` | `get_report` | Downloads generated XML report content. | Report ID from `/create/was/report`. | XML is parsed into findings, charts, summaries, and appendix data. | High, XML schema changes can alter report output. |
| `/count/was/finding` | Not explicitly set by legacy call | `max_age` | Counts open critical and urgent findings by date range. | XML filter payload built in code. | Used for max-age calculations and trend context. | Medium, date filters and finding status semantics must be verified. |
| `/search/was/finding` | `POST` | `get_ssn_and_cc` | Intended to search findings that indicate SSN or credit-card exposure. | XML builders and parsers remain in `report_artifacts.py`, but the two calls are disabled. | No production request is made. Attachment 7 is written as header-only `ssn-and-cc-found.csv`, and the report email states that it is not populated. | High, re-enable only after Qualys validation, operator review, and explicit approval. |
| `/search/was/webapp` | `POST` | `get_app_id`, `app_overview_table` | Finds web applications by URL or stakeholder tag. | XML filter payload built in code. | Reads web app IDs, URLs, scopes, and operating-system metadata. | Medium, output fields may vary by account permissions and scope. |

## Required For Detail Attachments

These calls support detail-report PDF attachments created by the production
report service.

| Endpoint | Method | Legacy Function | Purpose | Payload Source | Response Use | Migration Risk |
| --- | --- | --- | --- | --- | --- | --- |
| `/create/was/report` | `POST` | `create_details_report` | Creates a Qualys PDF detail report for a tag or web application ID. | Production templates under `src/was_reports/resources/assets`. | Reads `responseCode` and `data.Report.id`. | High, template ID `2201149` should be confirmed for the target Qualys subscription. |
| `/download/was/report/<id>` | `GET` through the WAS direct-download boundary | `download_report` | Downloads the Qualys-generated PDF detail report. | Environment-backed credentials, shared timeout and retry policy, maximum-byte limit, and free-space reserve. | Streams to a private partial file, validates PDF structure, atomically publishes it, then watermarks and redacts it. | Medium, direct-download authentication and representative live PDF validation remain required. |
| `/delete/was/report/<id>` | Not explicitly set by legacy call | `delete_report` | Deletes temporary Qualys reports after use. | Report ID. | Used as cleanup. | Medium, cleanup failure could leave reports in Qualys. |
| `/status/was/report/<id>` | `GET` | `get_report_status` | Checks generated report status. | Report ID. | Determines when report download can proceed. | Medium, polling states and timeout behavior need explicit handling. |

## Temporarily Disabled Sensitive-Finding Searches

`write_sensitive_data_attachment()` deliberately does not call
`/search/was/finding` for the SSN and credit-card QID sets. A known vendor issue
made that request unreliable. The current behavior is fail-open for the rest of
report generation while remaining explicit about missing data:

- write `ssn-and-cc-found.csv` with its header and no finding rows;
- log that sensitive-data results are unavailable, not that no findings exist;
- continue generating the remaining report and attachments; and
- include the approved Attachment 7 vendor-maintenance notice in customer
  report emails.

The code contains a TODO, but no date-based automatic re-enablement. Restoring
the calls requires a successful nonproduction API validation, operator review,
explicit approval, and updated fixtures and documentation. The separate
`/count/was/finding` calls used for critical and urgent finding ages remain
active.

## Required For Daily Tracker Refresh

| Endpoint | Method | Purpose | Request Handling | Failure Handling |
| --- | --- | --- | --- | --- |
| `/search/was/wasscanschedule` | `POST` | Finds recently launched vulnerability schedules. | Pages from a bounded reporting window and resolves each unique stakeholder tag ID once. | Missing launch or next-scan timestamps are logged and skipped with schedule context. |
| `/search/was/wasscan` | `POST` | Retrieves scan slices for eligible schedules. | Reuses one immutable, sorted, deduplicated tag-ID filter across every result page. Matched executions are maintained separately from the request filter. | Required pages are never silently skipped. A permanent Qualys error stops tracker refresh before partial tracker rows are persisted. |

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
| `download_report` status polling | `detail_reports.wait_for_report_completion`, which polls until `COMPLETE`, stops on terminal failure, survives transient request failures, and emits periodic progress logs. |
| `qualys_redact` | `pdf_helpers.redact_qualys_pdf` |
| `watermarker` | `pdf_helpers.apply_watermark` |
| `unfirstpagify` | `pdf_helpers.remove_first_page` |

## Administrative And Inventory Coverage

These original operations are either exposed through production commands or
explicitly awaiting a stakeholder decision. They do not execute historical
source files.

| Endpoint | Method | Legacy Function | Purpose | Migration Recommendation |
| --- | --- | --- | --- | --- |
| `/search/am/tag` | `POST` | `tag_dict_v2`, `app_find` | Looks up Qualys asset-management tags and descriptions. | Implemented through `was-inventory`, report generation, and guarded `was-admin` commands. Report generation uses one exact lookup to obtain both the tag ID and organization description. |
| `/count/was/webapp` | `POST` | `app_count`, `app_numbering` | Counts web applications by tag. | Implemented through `was-inventory`, report generation, and tracker refresh. |
| `/update/was/webapp/<id>` | `POST` | `add_tag`, `remove_tag` | Mutates Qualys web application tags. | Implemented through `was-admin add-tag` and `was-admin remove-tag`, both requiring explicit confirmation. |
| `/ignore/was/finding` | `POST` | `falsepos` | Marks a finding as a false positive. | Implemented through `was-admin false-positive` with explicit confirmation. |
| `/create/was/webapp` | `POST` | `reactivate_webapp` | Reactivates a web application with a replacement tag set. | Implemented through `was-admin reactivate` with explicit confirmation. |
| `/delete/was/webapp` | `POST` | `delete_webapp` | Removes a web application from the Qualys subscription. | Implemented through `was-admin delete-webapp` and the opt-in tracker `--delete-apps` path. |
| `/user.php` | Original method not explicit | `list_users` | Lists Qualys users. | Not exposed because no active original command called this function. Add a restricted command only if stakeholders confirm an operational need. |

## Credentials, permissions, and deployment boundary

The checked-in `dev.env` is an environment-key inventory containing placeholder
values. Never put a Qualys username, password, API token, database password, or
AWS credential in `dev.env`. For the supported local and current EC2 workflow,
create the ignored `backend/was/.env` with `scripts/create-local-env.sh`, keep it
at mode `0600`, replace every required placeholder, and pass that file to the
container. Do not print its contents or include it in logs or support bundles.

Current WAS code reads `WAS_QUALYS_USERNAME`, `WAS_QUALYS_PASSWORD`, and
`WAS_QUALYS_HOSTNAME` from the process environment. The repository does not
currently retrieve these values from AWS Secrets Manager or SSM Parameter
Store, and the WAS EC2 Terraform does not grant secret-read permissions or
inject managed secrets into the process. Managed-secret injection is a
recommended production improvement, not a capability that operators may assume
is already deployed. It requires a separately reviewed infrastructure and
runtime change with resource-scoped read permissions.

The Qualys service account and its roles are administered outside this
repository. Before enabling a workflow, a Qualys administrator must verify that
the account has only the permissions needed for the endpoint groups actually in
use:

- search, count, status, and download for read-only inventory, tracker, and
  report generation;
- report creation and temporary report deletion for report generation; and
- web-application update, ignore, create, or delete only for separately
  approved administrative and production-deletion workflows.

Do not grant mutation permissions solely because the same account can generate
reports. Record the account, subscription, approved endpoint groups, and
validation evidence in the deployment change record without recording the
credential values.

AWS IAM is a separate boundary. The current WAS EC2 Terraform attaches SSM
core access, exact `sts:AssumeRole` permission for the configured SES role, and
`s3:GetObject` and `s3:PutObject` under the configured bucket's
`was_reports/*` and `capacity/*` prefixes. It does not grant secret-read or
`s3:DeleteObject` permissions. Optional KMS permissions are limited to one
exact key ARN. Verify the deployed role and external SES trust policy against
the enabled runtime features before production or capacity execution. Do not
broaden it with wildcard permissions.

## Qualys report-template validation

Current code fixes the web-application report template ID at `1994875` and the
detail PDF template ID at `2201149`. `was-inventory` validates tags and web
application counts, not report templates. The repository has no command that
proves either template exists or is correct in a target Qualys subscription.

Before deployment to each subscription, an authorized Qualys administrator must
use the approved Qualys UI or API process to verify both IDs, the expected XML
and PDF formats, required report fields, active status, and service-account
access. Then generate a controlled nonproduction report and compare it with an
independently approved baseline. Record the subscription, template IDs,
validation date, and reviewer in the change evidence. Do not record credentials
or raw sensitive report data. Missing or unverified templates are a deployment
blocker.

## Current Concerns To Resolve

- Qualys credentials are read from WAS environment constants. Production
  Secrets Manager or SSM Parameter Store injection remains unimplemented and
  requires a separately reviewed infrastructure and runtime change.
- Some report downloads use direct `requests.Session` authentication instead of
  the `qualysapi` connection. These downloads use the same WAS-owned timeout and
  retry policy, but authentication remains specific to the direct download path.
- Qualys mutation commands are separated from report generation and require
  explicit confirmation. Durable centralized audit retention still depends on
  the deployed logging configuration.
- Report template IDs remain constants for output compatibility. Complete the
  subscription-specific validation and evidence described above before
  deployment.
- Qualys XML response parsing is tightly coupled to current response shape. Any
  API update should be tested with representative XML fixtures before deployment.

## Retry And Timeout Policy

- Read-safe `search`, `count`, `status`, and `download` operations retry
  transient connection errors, request timeouts, HTTP `429`, and HTTP `500`,
  `502`, `503`, and `504` responses.
- A read-safe operation retries one HTTP `401` response once after
  `WAS_QUALYS_AUTH_RETRY_DELAY_SECONDS`. A second HTTP `401` fails immediately
  so persistent credential or account failures remain visible.
- Retries use capped exponential backoff with jitter. A Qualys `Retry-After`
  response is honored up to `WAS_QUALYS_RETRY_MAX_DELAY_SECONDS`.
- Qualys create, update, ignore, and delete operations remain single-attempt to
  prevent duplicate reports or repeated administrative side effects.
- Every individual production request has a bounded timeout. Report-status
  polling continues until `COMPLETE` by default, with an optional positive
  total timeout available through configuration.
- Active Qualys detail and XML report IDs and observed statuses are stored on
  the database report run. A reclaimed tracker-linked run resumes those reports
  rather than submitting duplicate create requests. Temporary XML report state
  is cleared after the Qualys report is deleted.
- Create-timeout reconciliation searches `/search/was/report` using only the
  unique report name and format filters accepted by the documented Qualys
  filtered-search request.
- Retry logs include the endpoint path, attempt number, and delay. A final
  failure records the HTTP method, path without query values, HTTP status,
  approved correlation and transport headers, byte counts, and SHA-256 digests.
  Request and response bodies, query values, customer identifiers, URLs,
  comments, findings, credentials, authorization, cookies, tokens, and
  unapproved response headers are not logged.

## Update Checklist

When a Qualys API call changes, update this document with:

- Endpoint path and HTTP method.
- Calling module and function.
- Request payload source.
- Expected response fields.
- Whether the call reads data or mutates Qualys state.
- Required Qualys account permission.
- Test fixture or mock coverage added for the change.
