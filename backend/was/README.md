# WAS Reporting

For isolated load testing and production timing metrics, see
[Capacity testing](docs/capacity-testing.md). The target is 600 report outcomes
within eight hours through persisted SES acceptance, with no operational tracker
updates during the isolated test. Keep capacity database settings as
`TEST_WAS_DB_*` alongside normal `WAS_DB_*` settings in the private `dev.env`
copied to `.env` on EC2. The capacity launcher selects the test database;
normal commands retain their ordinary database settings. See the guide for all
seven required test settings and isolation prerequisites.

For non-enrolled Qualys tags, see [Standalone reports](docs/standalone-reports.md)
for the separate menu path, saved delivery address, and comprehensive schema
reference. The operator has confirmed the standalone database changes are complete.

WAS Reporting generates Web Application Scanning PDF reports from Qualys data.
The production implementation runs from `src/was_reports` and
`src/was_mailer`. Legacy source directories may be retained outside the
container for historical comparison, but they are not packaged or executable
through supported commands.

## Quick Start: Docker On EC2

Operators need Git, Make, a running Docker engine, and approved repository
access. Python and a uv environment are not required on the host for container
commands. The EC2 instance also needs database and Qualys connectivity, S3
permissions, and permission to assume the configured SES sending role.

### First Checkout And Build

From your EC2 home directory, clone the current WAS development branch using
your approved GitHub SSH access. Do not repeat the clone if this checkout
already exists; use the update cycle below instead.

```bash
mkdir -p ~/code
cd ~/code
git clone --branch cd_WAS_update --single-branch \
  git@github.com:cisagov/XFD.git cd_WAS_update
cd cd_WAS_update/backend/was
./scripts/create-local-env.sh
```

Populate `.env` using the **Local Environment File** instructions below before
running any commands against live services. The setup script will not overwrite
an existing `.env`. Never commit credentials or paste them into logs.

```bash
make build
make menu
```

For an approved standalone functional test, select **Report generation**, then
**4, Generate an on-demand report to S3 (optional email)**. Enter the approved stakeholder tag and,
if emailing, an address configured as an email-enabled functional-test
recipient. Leave the tracker ID blank unless intentionally linking an existing
test tracker row. This generates a PDF, archives it to S3, and optionally emails
it to analysts. It does not require recent-scan eligibility and does not deliver
directly to customers.

### Update And Rebuild Cycle

Finish or reconcile active report jobs before updating. Inspect the checkout
first; if the branch is not `cd_WAS_update` or there are local source changes,
resolve that before pulling. Do not discard local work or force-reset it.

```bash
cd ~/code/cd_WAS_update
git branch --show-current
git status --short
git pull --ff-only origin cd_WAS_update
cd backend/was
make build
make menu
```

Only continue if the pull and build succeed. Pulling source does not update the
container image. Rebuild after Python, dependency, template/resource, Dockerfile,
or worker-script changes. Menu and Make commands do not rebuild automatically.
Already-running containers retain their original image; new runs use the newly
built image.

Before deploying the ownership and tracker hardening update, apply the
[existing-database upgrade](docs/daily_report_tracker_schema.md#existing-database-hardening-upgrade).
Stop old workers first. Do not run the full table-creation script against an
existing database. The new code requires the additional columns and index.

Changes only to `.env` do not require a build; start a new container to load
them. Compare updated `dev.env` with your local configuration after pulls and
add required keys without replacing secrets. Documentation-only changes do not
require rebuilding. After an approved live test, verify the S3 object, database
run status, inbox delivery, and PDF content, not just the exit code.

## Workstation Access To The WAS EC2

Cross-platform Python access scripts are located in
`scripts/awsAccessScripts`. They replace the local Bash, GNU Screen, `lsof`,
and `nc` workflow for Windows users while also supporting macOS and Linux.
Workstations still require Python 3.10 or newer, AWS CLI v2, the AWS Session
Manager plugin, OpenSSH, an approved AWS CLI profile, and the approved SSH key
pair. Detailed setup is in `scripts/awsAccessScripts/README.md`.

From Windows PowerShell, set the WAS instance ID for the current window and run:

```powershell
cd scripts\awsAccessScripts
$env:INSTANCE_ID_WAS = "i-replace-with-approved-instance-id"
py .\checkAccessorWAS.py
py .\sshConnectWAS.py
```

The tunnel listens on local port `7777`. Diagnostics are retained at
`%USERPROFILE%\.was-access\tunnel.log`. Use `WAS_AWS_PROFILE` when the approved
AWS profile is not named `default`; do not add access keys or instance IDs to
the repository.

## Current Architecture

- `was-report-batch` is the default container command for scheduled reports.
- `was-reports` generates or manages one stakeholder report.
- `src/was_reports/commands` contains container command implementations. The
  report generator validates CLI input and calls only the production pipeline.
- `src/was_reports/qualys` provides the WAS-owned Qualys API boundary and
  migrated report-data helpers
  for tag lookup, app counts, report creation, XML download, status checks, and
  temporary report cleanup.
- `src/was_reports/reporting` contains report retrieval, transformation,
  metrics, artifacts, charts, LaTeX rendering, PDF security, and comparison.
- `src/was_reports/storage` uploads scheduled encrypted reports to S3 and
  materializes them in private temporary directories for email delivery.
- `src/was_reports/resources` contains the production report template, Qualys
  XML templates, images, fonts, PDF backgrounds, watermark, and redaction
  helpers.
- `src/was_reports/tracker` contains Qualys schedule and scan discovery,
  scan-slice consolidation, assignee allocation, Postgres tracker updates, and
  CSV export logic.
- `src/was_reports/data/stakeholders.py` reads stakeholder report metadata and
  updates scan status fields in Postgres.
- `src/was_reports/data/report_runs.py` records scheduled report execution
  status in Postgres.
- `src/was_reports/data/daily_report_tracker.py` records daily tracker rows and
  assignee digest email status in Postgres.
- `src/was_reports/data/assignees.py` reads and maintains report assignees in
  Postgres.
- `src/was_reports/data/special_cases.py` reads active special-case tag values
  from Postgres for upstream tracker logic.
- `src/was_reports/tracker/tracker_csv.py` exports tracker rows as CSV for email
  attachments or operator review.
- `src/was_reports/tracker/assignments.py` assigns tracker rows to active assignees
  using round-robin distribution.
- `src/was_reports/utils/database.py` creates Postgres connections from
  environment variables.
- `src/was_reports/utils/passwords.py` generates and validates WAS report
  passwords.
- `worker/was-report-start.sh` runs the scheduled report batch command.

## Local Environment File

Create a local `.env` file from the checked-in template:

```bash
cd backend/was
./scripts/create-local-env.sh
```

The script copies `dev.env` to `.env`, sets local file permissions to `600`, and
refuses to overwrite an existing `.env`. Replace all placeholder values before
running WAS.

`dev.env` documents the required constants:

```bash
WAS_DB_HOST=replace-me-rds-endpoint
WAS_DB_NAME=was
WAS_DB_USERNAME=was_app
WAS_DB_PASSWORD=replace-me
WAS_DB_PORT=5432
WAS_DB_SSLMODE=require
WAS_QUALYS_USERNAME=replace-me
WAS_QUALYS_PASSWORD=replace-me
WAS_QUALYS_HOSTNAME=replace-me-qualys-hostname
WAS_QUALYS_MAX_ATTEMPTS=4
WAS_QUALYS_REQUEST_TIMEOUT_SECONDS=120
WAS_QUALYS_AUTH_RETRY_DELAY_SECONDS=5
WAS_QUALYS_RETRY_BASE_DELAY_SECONDS=1
WAS_QUALYS_RETRY_MAX_DELAY_SECONDS=30
WAS_QUALYS_RETRY_JITTER_RATIO=0.25
WAS_QUALYS_CREATE_RECONCILE_TIMEOUT_SECONDS=300
WAS_QUALYS_CREATE_RECONCILE_POLL_SECONDS=10
WAS_QUALYS_REPORT_POLL_SECONDS=60
WAS_QUALYS_REPORT_PROGRESS_SECONDS=300
WAS_QUALYS_REPORT_POLL_TIMEOUT_SECONDS=0
WAS_OPERATION_HEARTBEAT_SECONDS=30
WAS_REPORT_RUN_STALE_SECONDS=300
WAS_EMAIL_CLAIM_STALE_SECONDS=300
WAS_LOG_DIRECTORY=/output/logs
WAS_LOG_RETENTION_DAYS=14
WAS_LOG_MAX_BYTES=10485760
WAS_LOG_BACKUP_COUNT=5
WAS_RESOURCE_ROOT=/WAS_REPORT_RESOURCES
WAS_OUTPUT_DIRECTORY=/output
WAS_WORKSPACE_ROOT=/tmp/was-report-workspaces
WAS_REPORT_STAGING_DIRECTORY=/tmp/was-report-storage
WAS_REPORT_STORAGE=s3
WAS_REPORTS_BUCKET_NAME=cisa-was-reports
WAS_REPORTS_PREFIX=was_reports
WAS_PASSWORD_LENGTH=24
AWS_DEFAULT_REGION=us-east-1
WAS_EMAIL_SOURCE=verified-sender@example.gov
WAS_SES_ROLE_ARN=arn:aws:iam::246048611598:role/SesSendEmail-cyber.dhs.gov
```

Long-running report generation and report-email delivery refresh database lease
timestamps every `WAS_OPERATION_HEARTBEAT_SECONDS`. A generation claim with no
heartbeat for `WAS_REPORT_RUN_STALE_SECONDS` is marked failed before new work is
claimed. A stale SES claim is placed on hold because delivery may have succeeded,
so the software never blindly resends an uncertain email. Tracker-linked report
failures are marked for manual handling with a safe failure summary, which is
included in the complete batch's assignee digest.

Generation and email claims carry unique ownership tokens. An expired worker
cannot update a replacement worker's state. Heartbeat failures stop subsequent
side effects rather than silently continuing. S3 keys include a generation token
so an old worker cannot overwrite the replacement artifact. If upload succeeds
but database completion is uncertain, retain the object and reconcile the run;
do not delete the object or resend email blindly.
SES SDK-level retries are disabled for delivery requests, so an uncertain send
is not repeated internally before the application can place it on hold.

All WAS commands log to container stdout for `docker logs`. When `/output` is
mounted, the same messages are retained on the host under `local-output/logs/`.
Each process writes a timestamped `was-reporting-*.log` file, rotates it at 10
MiB, and retains five segments. Command startup removes WAS log files older than
14 days. Change the log settings only when operational retention requirements
differ. Every log entry includes the logging statement's Python filename and
line number. Handled exception summaries also include `origin=<path>:<line>`
for the deepest traceback frame where the failure originated.

Log files are owner-readable only, including rotated files. Their random suffix
prevents separate containers with the same PID and start second from sharing a
file. Qualys requests log endpoint, elapsed time, and safe HTTP error metadata.
A final Qualys request failure logs the exact prepared request URL and API
version in a credential-free `curl` replay command containing the HTTP method
and sanitized XML request. It also logs the HTTP status, approved response
headers, and sanitized response XML limited to 16,384 characters. A network
failure that produced no response is identified explicitly. The command
references the existing
`WAS_QUALYS_USERNAME`, `WAS_QUALYS_PASSWORD`, and `WAS_QUALYS_HOSTNAME`
environment variables instead of printing their values. Review the command and
run it only from an approved environment because its sanitized payload may
still identify the stakeholder tag or report ID. Authorization, cookies,
tokens, credential values, unapproved response headers, and unsanitizable
response bodies are not logged. Database failures include
SQLSTATE and available table/column names without SQL values. Connection
establishment is bounded by `WAS_DB_CONNECT_TIMEOUT_SECONDS` (default `10`).
Inventory queries also show which stakeholder count is being retrieved and
progress through the list.

Make targets that mount `local-output` run the container with the invoking
operator's UID and GID. This keeps private host log and export files readable by
that operator without requiring `sudo`. Files created by older root-running
containers retain their existing ownership.

After all WAS containers have finished, repair an existing root-owned output
tree once from `backend/was`:

```bash
sudo chown -R "$(id -u):$(id -g)" local-output
```

Do not change ownership while a report or mailer container is writing there.

Do not commit `.env`, database passwords, Qualys credentials, or generated
reports.

SES report and tracker-digest delivery assume `WAS_SES_ROLE_ARN` using the
default AWS credential chain, which uses the EC2 instance role when no higher
priority credentials are configured. Temporary SES credentials refresh
automatically in memory. S3 continues using its own default credentials.
No `was-ses` profile, credentials-file mount, or static access keys are required.
The EC2 role must allow `sts:AssumeRole` on the sending role, that role must
trust the EC2 role, and the sending role must permit `ses:SendRawEmail` for the
approved sender identity. Role-assumption failures fail delivery without
falling back to the EC2 role for SES.

On EC2, replace the unused `WAS_SES_PROFILE` entry in `.env` with the
`WAS_SES_ROLE_ARN` entry above, retain `AWS_DEFAULT_REGION=us-east-1`, and set
`WAS_EMAIL_SOURCE` to your approved sender. Leave the role ARN blank only
when intentionally using default credentials for direct SES delivery.
After pulling code updates, run `make build` before running the mailer or menu.
Verify the actual report mailer with an approved test recipient; an SES
message ID indicates acceptance, not confirmed delivery.

The modern WAS code reads constants from `backend/was/.env` during local
execution. In a container, pass the same file with `docker run --env-file .env`.
Production Qualys clients use the three `WAS_QUALYS_*` values directly and do
not create or read `was_config.txt`. Daily tracker, customer data, and
special-case XLSX paths are no longer required by the active tracker workflow.

Qualys read operations retry transient connection failures, timeouts, HTTP
`429`, and selected HTTP `5xx` responses. Retries use capped exponential
backoff with jitter and honor `Retry-After` up to the configured maximum delay.
Read-safe operations also retry one HTTP `401` response once after
`WAS_QUALYS_AUTH_RETRY_DELAY_SECONDS`; a repeated HTTP `401` fails so invalid
credentials remain visible. Mutating operations never receive this retry.
Create, update, ignore, and delete operations are never blindly retried because
repeating them could duplicate or alter Qualys state. Every generated report
uses a unique name containing its database run ID. If a create response times
out, WAS searches Qualys for that exact name and format for up to
`WAS_QUALYS_CREATE_RECONCILE_TIMEOUT_SECONDS`, recovers the assigned Qualys
report ID, and continues polling. Report-status polling runs every
`WAS_QUALYS_REPORT_POLL_SECONDS` until Qualys returns `COMPLETE` or a terminal
failure status. Progress is written to the terminal and retained log every
`WAS_QUALYS_REPORT_PROGRESS_SECONDS`. The default value of `0` for
`WAS_QUALYS_REPORT_POLL_TIMEOUT_SECONDS` allows multi-hour reports to continue
without an elapsed-time cutoff. Set a positive number of seconds only when an
environment requires a bounded polling window.

Active Qualys detail and XML report IDs, current statuses, and last-poll
timestamps are stored on `was_report_runs`. If a tracker-linked failed run is
reclaimed after a container interruption, report generation reuses those IDs
and resumes polling instead of creating duplicate Qualys reports. The temporary
XML report ID is cleared after Qualys cleanup so a later retry cannot reference
a deleted report. Existing databases require a DBA-reviewed additive change
before deploying code that depends on these columns. Incremental SQL history is
kept locally and is intentionally not distributed in the repository. The
canonical final schema is `schema/stakeholders_table_creation.sql`; do not run
that complete creation file against an existing database.

### Qualys API Rate Limit

The operator-reported Qualys API rate limit for this WAS environment is
**2,000 requests per hour**. Confirm the applicable subscription limit and
its scope with the Qualys administrator before increasing workload concurrency;
this value should not be assumed to apply to every Qualys subscription or API.

Plan concurrent report generation, tracker refreshes, and inventory queries
within that limit, accounting for other clients sharing the same quota. The
retry behavior described above handles throttling responses; it is not a
guarantee that combined workloads stay below 2,000 requests per hour.
Each report generation resolves the stakeholder tag ID and organization
description from one exact Qualys tag lookup. It does not repeat the tag search
for those two values.
Daily tracker refreshes likewise resolve each unique stakeholder tag once and
reuse one immutable, deduplicated tag-ID filter for every scan-search page.
Matched scan executions cannot expand later Qualys pagination requests.

### S3 Report Storage

Scheduled reports use S3 by default. Each encrypted PDF is uploaded to a
run-specific key and the resulting S3 URI is stored in
`was_report_runs.output_path`:

```text
s3://<WAS_REPORTS_BUCKET_NAME>/<WAS_REPORTS_PREFIX>/<YYYY-MM-DD>/<TAG>/<REPORT_RUN_ID>/<FILENAME>
```

The report task needs `s3:PutObject` and `s3:DeleteObject` for the configured
prefix. Delete permission is used only to make an uploaded object unavailable
when the corresponding database completion update fails. Because the reports
bucket is versioned, this operation creates a delete marker rather than
permanently deleting the stored version. Permanent version retention remains a
separate bucket-governance decision and is not changed by this application.
The mailer task needs
`s3:GetObject` for the same prefix. Grant these permissions to the task or
instance role, not the execution role or static AWS credentials. `s3:ListBucket`
is not required. The configured bucket must block public access and encrypt data
at rest.

The staging environment uses the dedicated `cisa-was-reports` bucket through
`WAS_REPORTS_BUCKET_NAME`. WAS objects remain isolated under
`WAS_REPORTS_PREFIX=was_reports`. Each deployed environment must supply its own
bucket name and grant the two object-level permissions before deployment.

Existing databases require a DBA-reviewed additive change for the report-run
claim columns and indexes before deploying this code. Use
`schema/stakeholders_table_creation.sql` as the canonical final-state reference,
but do not execute the complete creation file against an existing database.

The unique active-schedule index prevents separate report containers from
generating the same stakeholder schedule concurrently. Email delivery uses an
atomic database claim before calling SES. If SES accepts a message but the
database cannot record the result, the claim remains in `sending` status for
manual reconciliation rather than being retried automatically.

For local batch development without AWS access, explicitly select local storage
and mount an output directory:

```bash
docker run --rm \
  --env-file .env \
  -v "$(pwd)/local-output:/output" \
  was-reporting \
  --storage-mode local \
  --limit 1
```

## Install Locally

From the repository root:

```bash
cd backend/was
../../cd_WAS_update/bin/python -m pip install -r requirements.txt
../../cd_WAS_update/bin/python -m pip install --no-deps -e .
```

If the virtual environment path differs, replace `../../cd_WAS_update/bin/python`
with the Python executable for your active `uv` environment.

## Operator Usage

The WAS software runs inside Docker containers, locally or on the WAS EC2
instance. ECS/serverless deployment is future work and is not part of the
current operator workflow.

Use `docker run` when starting a new one-off WAS report container. Use
`docker exec -it` only when a WAS container is already running.

### Generate Due Reports

Generate all due stakeholder reports from `was_stakeholders.next_scheduled`:

```bash
docker run --rm \
  --env-file .env \
  was-reporting \
  --create-missing-password
```

Limit a test run to one due stakeholder:

```bash
docker run --rm \
  --env-file .env \
  was-reporting \
  --create-missing-password \
  --limit 1
```

Each scheduled batch report creates a `was_report_runs` record. Successful
reports are marked `completed` with the uploaded S3 URI and artifact type after
S3 upload succeeds. Failed generation or upload attempts are marked `failed`.

### Generate One Report

Run one stakeholder through the same tracked workflow used by the recent-scan
batch:

```bash
make single-report TAG="CUSTOMER_TAG"
```

The command refreshes recent Qualys activity for only that tag. When an
eligible tracker row has not already been emailed, it generates the encrypted
report, uploads it under the current S3 date prefix, sends it through SES, and
sets `report_sent_date` after SES accepts the message. Existing completed but
unsent report runs are also recovered only for the requested tag. If no unsent
tracker gap exists, the command does not create or email a duplicate report.

Equivalent Docker command:

```bash
docker run --rm \
  --env-file .env \
  was-reporting \
  --recent-scans \
  --tag "CUSTOMER_TAG" \
  --create-missing-password \
  --send-email
```

Generate a local PDF without S3 upload, SES delivery, or tracker updates only
when performing development or report comparison:

```bash
docker run --rm \
  --env-file .env \
  -v /local/output:/output \
  was-reporting \
  was-reports \
  --tag "CUSTOMER_TAG"
```

Do not place a production password directly in interactive shell history.
Normal operation resolves the stakeholder password from Postgres by omitting
`--encrypt`. The production route always requires encryption and deletes its
isolated temporary workspace after completion.

Before Qualys credentials are available, run the offline container smoke test.
It uses representative XML with the real Mustache template, static report
assets, chart generators, XeLaTeX compiler, and PikePDF encryption:

```bash
mkdir -p local-output/offline-smoke
docker run --rm \
  -v "$(pwd):/workspace:ro" \
  -v "$(pwd)/local-output/offline-smoke:/offline-output" \
  --entrypoint python \
  was-reporting \
  /workspace/scripts/offline_pipeline_smoke.py \
  --resource-root /WAS_REPORT_RESOURCES \
  --fixture /workspace/tests/fixtures/was_report_sample.xml \
  --output-directory /offline-output
```

This test does not call Qualys or Postgres. A successful result proves local
artifact generation, template compilation, encryption, and publication, but it
does not prove live API compatibility or production data equivalence.

When both live reports are available, compare them without placing the report
password on the command line:

```bash
read -s WAS_REPORT_COMPARISON_PASSWORD
export WAS_REPORT_COMPARISON_PASSWORD
was-compare-reports /path/to/approved-baseline.pdf /path/to/generated.pdf
unset WAS_REPORT_COMPARISON_PASSWORD
```

The command compares encryption state, page count, page dimensions, normalized
page text hashes, selected metadata, and embedded attachment names and hashes.
It recognizes both document names-tree attachments and page-level attachment
annotations produced by XeLaTeX `attachfile2`. It never writes a decrypted
report to disk or prints the password.

Follow `docs/live_qualys_equivalence_runbook.md` for the complete approved
nonproduction production-validation sequence and cleanup checks.

Generate a report and create a stakeholder password if one does not exist:

```bash
docker run --rm \
  --env-file .env \
  -v /local/output:/output \
  was-reporting \
  was-reports \
  --tag "CUSTOMER_TAG" \
  --create-missing-password
```

### Manage Report Passwords

`CUSTOMER_TAG` is a placeholder. Replace it with the exact stakeholder tag
stored in `was_stakeholders.tag`. Quotes are recommended because they are safe
for tags that contain spaces or shell-sensitive characters.

Create a missing password for a stakeholder during report generation:

```bash
docker run --rm \
  --env-file .env \
  -v /local/output:/output \
  was-reporting \
  was-reports \
  --tag "CUSTOMER_TAG" --create-missing-password
```

Change an existing stakeholder password by generating a new password:

```bash
docker run --rm \
  --env-file .env \
  was-reporting \
  was-reports \
  --tag "CUSTOMER_TAG" --change-password
```

If a WAS container is already running, execute the command inside that
container:

```bash
docker exec -it WAS_CONTAINER_NAME \
  was-reports --tag "CUSTOMER_TAG" --change-password
```

The password remains the stakeholder password until a change request updates it.
The production pipeline uses the password in-process. The report comparator
reads its password from `WAS_REPORT_COMPARISON_PASSWORD`, so the value does not
need to appear in process arguments.

In the interactive menu, Stakeholder Management option 8 rotates the password
and displays `Operation completed successfully. The new password is
<new_password>`. Option 7 retrieves the currently stored password by exact
stakeholder tag after confirmation. Option 9 securely adds or replaces a
customer-provided report password using hidden double-entry and explicit
confirmation. Customer-provided passwords must contain at least 16 characters,
including an uppercase letter, lowercase letter, number, and special character.
Spaces, commas, and hyphens are not allowed. The menu displays these rules and
explains a validation failure without printing or logging the submitted value.
Generated or retrieved password
values are written only to the interactive terminal output, not to the WAS
application log. Treat the terminal output as sensitive and clear it after
recording the password through the approved process.

### Manage Stakeholder Contacts

Update one or more stakeholder POC fields with explicit confirmation:

```bash
docker run --rm \
  --env-file .env \
  was-reporting \
  was-stakeholders update-contacts \
  --tag "CUSTOMER_TAG" \
  --was-report-poc "POC NAME" \
  --tech-poc-email "technical.poc@example.gov" \
  --distro-email "distribution@example.gov" \
  --confirm
```

Omit unchanged options. Clear a value with `--clear-was-report-poc`,
`--clear-tech-poc-email`, or `--clear-distro-email`. The command never prints
the contact values and does not modify report passwords or scheduling fields.

### View And Update Stakeholder Rows

Display the current database values for one exact stakeholder tag. The report
password is shown only as configured or missing:

```bash
docker run --rm \
  --env-file .env \
  was-reporting \
  was-stakeholders show \
  --tag "CUSTOMER_TAG"
```

Update only selected business fields and use `--clear` to store SQL `NULL`:

```bash
docker run --rm \
  --env-file .env \
  was-reporting \
  was-stakeholders update \
  --tag "CUSTOMER_TAG" \
  --set "customer_name=Updated Customer Name" \
  --set "retired=false" \
  --clear comments \
  --confirm
```

The Stakeholder Management menu provides separate read-only View and
write-enabled Update workflows. View displays the matching row and allows any
displayed field name to be entered to print its complete untruncated value for
copying. Update displays the matching row first, then cycles through every
editable column in database order.
Each interactive edit prompt is prefilled with the current stored value.
Press Enter to retain it, edit the value before pressing Enter to replace it,
enter `CLEAR` to store SQL `NULL`, or enter `CANCEL` to stop without saving.
The workflow validates integer, Boolean, and email values and displays the
updated row afterward.
Stakeholder state values must use an exact uppercase two-letter USPS state or
territory code, such as `WY`. Values such as `wy` or `Wz` are rejected during
single-stakeholder creation, stakeholder updates, and CSV imports. State is
required; use `INTERNATIONAL` for an international stakeholder.
The primary `tag`, `report_password`, `created_at`, and `updated_at` fields are
protected. Use the dedicated password-rotation command for password changes.

The Qualys-integrated stakeholder date fields remain Unix epoch `BIGINT` values
in PostgreSQL. Stakeholder table and full-field displays convert them to
`YYYY-MM-DD HH:MM:SS UTC` and include the original epoch value in parentheses.
This keeps the Qualys and scheduling interfaces stable while making dates
readable to operators.

### Export Stakeholders

Export all non-secret stakeholder columns to an owner-readable CSV:

```bash
make stakeholder-export
```

This writes `local-output/was-stakeholders.csv` with file mode `0600` and
neutralizes spreadsheet formulas in non-password text fields. Report passwords
are excluded by default. Non-secret exports can also be saved directly to the
configured S3 bucket or emailed only to addresses registered as active,
email-enabled WAS assignees. Choose the export destination from the Stakeholder
Management menu, or use one of these commands:

Epoch values in `web_apps_last_updated`, `last_scanned`, `next_scheduled`, and
`onboarding_date` are exported as `YYYY-MM-DD HH:MM:SS UTC` timestamps.

```bash
docker run --rm --env-file .env was-reporting \
  was-stakeholders export-csv --s3

docker run --rm --env-file .env was-reporting \
  was-stakeholders export-csv \
  --email-assignee "analyst@example.gov"
```

S3 exports are encrypted with S3-managed encryption and stored below
`<WAS_REPORTS_PREFIX>/stakeholder_exports/<YYYY-MM-DD>/`. Email export recipients
must exist as active, email-enabled entries in `was_assignees`. The existing
typed confirmation remains required before any destination can include report
passwords. Password-containing exports cannot be emailed.

A complete sensitive export requires two explicit flags and should be moved to
approved encrypted storage immediately after use:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  --env-file .env \
  -v "$(pwd)/local-output:/output" \
  was-reporting \
  was-stakeholders export-csv \
  --output /output/was-stakeholders-sensitive.csv \
  --include-report-passwords \
  --confirm-sensitive-export
```

Do not email, commit, or place the sensitive CSV in shared storage.

### Import Stakeholders

Stakeholder Management can prepare and atomically import new stakeholder rows
from a DynamoDB CSV export. Existing tags are skipped. Blank values, Boolean
values, state codes, hierarchy order, and database column order are normalized
before insertion. The importer removes one legacy outer quote wrapper and
converts doubled quote sequences (`""`) back to the intended single quote
character (`"`) for wrapped or legacy-length report passwords. All other
password characters, including intentional leading or trailing whitespace, are
preserved exactly. Edge whitespace produces a warning containing the
stakeholder tag but never the password.

### Interactive Operator Menu

Launch the numbered WAS operator menu from `backend/was`:

```bash
make menu
```

The menu groups existing commands into Report Generation, Report Tracker,
and Stakeholder Management. API tracker refresh is in Report Tracker; the slow
inventory operation is no longer a menu option. It supports guided prompts,
confirmation before write or delivery operations, `CLEAR` for removing contact
values, typed confirmation before exporting report passwords, and confirmed
display of a stakeholder report password. Files are written under the mounted
`local-output` directory.

Quit and Back to main menu are always option `0`, displayed first. Enter `b`
at a submenu selection as an alternate way to return to the main menu.
See [operator menu workflows](docs/operator-menu.md) for the updated options.

Pressing `Ctrl+C` while answering an operation prompt, such as a stakeholder
tag, recipient, password, date, or confirmation, cancels that input workflow
and redraws the same submenu. Pressing `Ctrl+C` at a submenu selection or the
main menu exits `was-menu`.

While a long-running report, batch, or tracker refresh
operation is active, enter `b` and press Enter or press `Ctrl+C` to request
cancellation. The operation stops at its next safe API, polling, lease, upload,
or delivery boundary and then returns to the immediately previous menu. An
active external request is allowed to finish or reach its configured timeout
rather than being terminated during an uncertain side effect. Any created
report run is recorded as failed when cancellation occurs before completion; a
report already archived before the cancellation boundary remains completed.
Review the displayed status and the timestamped application log before
retrying.

Report Generation option 1 asks the operator to choose a delivery mode. Test
mode requires one or more email-enabled functional-test recipient addresses and
delivers all customer report messages and assignee digests only to those
override addresses. One-off email recipients and batch test overrides must
exactly match an email-enabled `was_assignees` row. The row does not need to be
active, allowing development testers to remain excluded from daily assignment
and digest processing. Unknown or email-disabled addresses are rejected before
report processing, and the operator receives a specific correction message.
A successful test delivery still marks its report run and linked tracker row as
sent, so operators must use it only for approved test data. Production mode uses
the customer technical and distribution addresses and requires the operator to
type `SEND CUSTOMER REPORTS` before the batch starts. The operator can also
enter a positive maximum report count, such as `25`, or accept `all` to process
every eligible report. The limit applies after eligibility and duplicate checks.

The menu is a thin interface over the same Python command and data-service
functions used by direct CLI commands. Operators can therefore use either the
menu or commands such as `was-tracker`, `was-stakeholders`, and
`was-report-batch` without changing application behavior. Future customer
onboarding prompts should be added under Stakeholder Management and reuse the
same validation and database service layer.

## Container Usage

Build the image from `backend/was`:

```bash
make build
```

Run `make build` after pulling application changes or modifying Python code,
dependencies, the `Dockerfile`, packaged resources, or worker scripts. Commands
such as `make menu` use the existing `was-reporting` image and do not rebuild it
automatically. A rebuild is not required when only `.env` values change because
Docker loads that file when each container starts.

The image normalizes packaged source and resource permissions during the build
so operators can run commands with the host user's UID instead of container
root, even when the checkout was created with a restrictive host `umask`.

Smoke test the container command routing without database or Qualys access:

```bash
docker run --rm was-reporting --help
docker run --rm was-reporting was-reports --help
```

Run the scheduled report batch container:

```bash
docker run --rm \
  --env-file .env \
  was-reporting \
  --create-missing-password
```

The batch uses private temporary storage while generating each PDF, uploads the
encrypted report to S3, and removes the temporary local copy.

### Run The Recent-Scan Batch

The operational batch first updates `was_daily_report_tracker` from recently
completed Qualys scan schedules. It then selects finished automated rows where
`report_sent_date` is empty and no `was_report_runs` record is already linked.
Each tracker row is claimed once, generated, uploaded, emailed, and stamped with
the report sent date. Metadata or generation failures are marked `MANUAL` for
the assigned analyst.

Qualys schedules without an actual launch timestamp are skipped. If an ad hoc
schedule has no next launch date and its primary schedule also has no next
launch date, that schedule is logged with its ID, name, and tag and skipped so
the remaining batch can continue.

Existing databases require a DBA-reviewed additive change for the tracker link
before using this mode. The canonical final-state definition is in
`schema/stakeholders_table_creation.sql`.

Run the complete recent-scan batch and send reports plus analyst digests:

```bash
docker run --rm \
  --env-file .env \
  was-reporting \
  --recent-scans \
  --create-missing-password \
  --continue-on-error \
  --send-email \
  --send-assignee-digests
```

The direct `docker run` command above uses one report-generation process. For
the production EC2 batch, use the Make target to refresh the tracker once and
run disjoint report partitions in multiple containers:

```bash
make recent-scan-batch
```

`BATCH_WORKERS` defaults to `30` and must be between `1` and `30`. Each worker
container receives a non-overlapping stakeholder partition so two reports for
the same stakeholder cannot run concurrently. Existing database claims prevent
duplicate tracker-row report runs. A worker emails each report after successful
S3 archival. After all workers exit, one mailer container retries any remaining
completed deliveries and one mailer container sends the shared final analyst
summary. A separate shared summary is sent after tracker refresh and preflight.
Reduce the worker count if Qualys throttling or account-level capacity becomes
visible. The documented 2,000-request-per-hour Qualys limit still applies to the
combined worker pool.

The production Make target searches Qualys from three days before the latest
tracker update and limits automated report work to exactly seven calendar dates,
including today. Override these independent windows when necessary:

Daily discovery selects only the latest execution per schedule, combining its
scan slices across all response pages before deciding whether it is complete.
Before requesting scan slices, discovery checks tracker evidence for each
schedule's latest execution and excludes already-handled matches. This follows
the legacy ordering without treating a recurring schedule ID as permanently
processed. Unresolved or ambiguous matches remain available for further checks.
The read-only preview reports the number excluded before the scan search.
The schedule's latest numbered run name identifies its slices. Schedule-level
and slice-level launch timestamps need not match, so timestamp ordering does not
override an exact latest-run-name match.
It does not fall back to older executions when the latest is incomplete or
already handled. Missing evidence for the schedule's latest execution is held
instead of substituting an older run. Manual report generation is unchanged.
Increasing the discovery lookback does not enable older-run recovery.

Tracker execution identity must come from the schedule's latest launch, not
from individual slice launch timestamps. Earlier discovery code used each
slice timestamp in its execution key, so slices of one numbered run could
produce different keys and pass the unique-key constraint. Grouping slices by
numbered run reduced that problem, but choosing the earliest returned slice
still made identity depend on which slices were visible. The current guard
anchors the key to the schedule launch and holds conflicting existing numbered
run identities for manual reconciliation. It does not delete or merge existing
rows. Apply this behavior to every running worker before resuming refreshes;
an older process does not acquire the new safeguards merely because files have
been updated.

Explicit MULTI parents are excluded from per-target aggregation. A visible
parent or schedule parent with a known status other than Finished holds the
run for review or a later refresh; a parent-only response cannot create a
successful tracker result. This does not independently prove that Qualys
returned every expected child. Parent-child grouping still uses the normalized
numbered scan name, not a newly verified API parent-ID relationship. Missing or
renamed numbered-run identities also limit historical overlap detection.
Validate representative live MULTI and SINGLE responses before treating these
unit-tested safeguards as full API parity.

Slice result aggregation uses the operator-approved priority: Scan Results
Invalid, Scan Internal Error, No Web Service, No Host Alive, Service Error,
Time Limit Reached, Successful. No Host Alive remains an inaccessible-target
result. Empty, unknown, or incomplete inputs cannot become Successful. This
priority is an explicit correction to the archived legacy behavior, which
placed Service Error ahead of No Web Service.

If the sensitive-finding API explicitly returns `OTHER_ERROR`, Attachment 7
contains its CSV headings with no data rows. Partial findings from earlier
pages or the other sensitive-finding query are discarded, and the rest of the
report continues. A warning identifies the unavailable attachment without
logging finding contents. Authentication failures, network failures, malformed
responses, and unrelated API errors are not suppressed. A blank attachment in
this case does not mean that the scan found no sensitive data.

Historical recovery is separate from daily discovery. An automated recovery
command is not provided by this latest-only change; use an explicitly reviewed
reconciliation plan and counts-only preview before generating historical work.

### Customer email dates and attachment names

Customer email corrections approved September 23 retain the source questions
address `vulnerability@cisa.dhs.gov`; the signature remains
`reports@cyber.dhs.gov`. Customer PDF attachments use
`<TAG>_WAS_report_<YYYY-MM-DD>.pdf`. The date remains the existing report artifact
date. Unique internal artifact paths and S3 keys are retained to avoid overwrites.

Email scan-start text uses the execution's separate `scan_started_at` timestamp,
recorded from the actual MULTI parent or SINGLE scan launch, falling back to
complete target launch data when necessary. It does not use the shared
stakeholder timestamp or reinterpret the duplicate-prevention execution key.
Both `scan_started_at` and `scan_ended_at` preserve timezone-aware timestamps.
When Qualys omits an explicit end, completed scan details provide the duration
used to calculate the end from the launch timestamp. This requires at most one
details lookup per selected customer execution, not one per target slice.
Missing timing data remains unknown. Customer emails display the start in
Eastern Time, including daylight-saving adjustment; the approved template does
not gain a new end-time sentence.
The tracker requires nullable `scan_started_at TIMESTAMPTZ` and
`scan_ended_at TIMESTAMPTZ` columns before
deploying this code; existing rows remain unknown rather than being backfilled
from completion dates or date-only imports. The comprehensive creation schema
includes both columns. Incremental SQL stays local under `schema/updates/`;
apply `016_store_tracker_scan_timestamps.sql` before deployment.

The additive migration, which does not change existing row values, is:

```sql
ALTER TABLE was_daily_report_tracker
    ADD COLUMN IF NOT EXISTS scan_started_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS scan_ended_at TIMESTAMPTZ;
```

Verify column types and remaining missing timestamps after migration/backfill:

```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = current_schema()
  AND table_name = 'was_daily_report_tracker'
  AND column_name IN ('scan_started_at', 'scan_ended_at');

SELECT COUNT(*) AS total_rows,
       COUNT(*) FILTER (WHERE scan_started_at IS NULL) AS missing_starts,
       COUNT(*) FILTER (WHERE scan_ended_at IS NULL) AS missing_ends
FROM was_daily_report_tracker;
```

Normal tracker refresh persists these values for newly processed executions.
Date-only CSV/XLSX imports do not invent timestamps, and existing completed rows
are not automatically revisited for historical timestamp enrichment. Missing
Qualys timing information remains NULL. The columns must remain in place while
timestamp-aware code is deployed; rolling back the code does not require dropping
these additive columns.

For historical rows, use the bounded timestamp backfill from the repository root
with the existing WAS database and Qualys environment configuration. The database
tunnel must be available when the configured host is a forwarded local port.
Start with a small read-only preview (the dates and tag below are an example):

```bash
PYTHONPATH=backend/was/src ./cd_WAS_update/bin/python \
  backend/was/scripts/backfill_tracker_timestamps.py \
  --since 2026-09-01 --until 2026-09-23 --tag RSDOR --limit 100
```

Review the proposed timestamps and Qualys scan IDs, then repeat with
`--apply --confirm-name-date-matches` to write them. Omit
`--tag RSDOR` for all tags within the chosen window. `--after-id` allows paging
past reviewed tracker IDs. Dates use the tracker's Eastern calendar convention.
The backfill requires an unambiguous exact normalized numbered scan name, tag,
and calendar-date match to a Qualys customer scan. It does not infer a launch
time from an execution key. Unmatched or ambiguous rows remain unchanged.
This match does not independently prove that the returned scan belongs to the
stored schedule ID. A recreated schedule could reuse a name and numbered run.
The confirmation flag explicitly acknowledges operator review of that mapping;
do not apply when the displayed scan identity cannot be confirmed.

The apply operation only fills missing timestamp fields. It guards the row's
identity and previously observed timestamps against concurrent changes, and
rolls the batch transaction back on failure. It does not generate reports, send
emails, modify report status, or delete rows. Take a database backup before
applying historical changes and retain the command output for the affected IDs
and timestamps. A committed correction should be reversed only for those exact
IDs after checking that no subsequent update has changed the values.

### Read-only legacy alignment diagnostic

After importing tracker data, or before approving selection changes, run from
`backend/was` in a checkout with the original `../WAS Automation Export 2026-05-06.zip`:

```bash
make report-alignment-diagnostic-local
```

This local command needs the project Python environment and working read-only
database/Qualys connectivity. It does not start Docker. It writes timestamped,
owner-readable JSON and replay snapshots under `local-output/`. It uses a
database-enforced read-only repeatable-read transaction and only Qualys schedule
searches. It does not refresh the tracker, retrieve scan slices, generate or
delete reports, assign analysts, send emails, or recover stale operations.

The diagnostic compares the hash-pinned original ZIP's schedule selector against
current selection using the same captured schedule pages. It shows the original
48-hour baseline, an equal-window rule comparison, the configured modern window
(three days by default), and the actual modern early tracker exclusion stage.
Final stored report eligibility is queried with the production selector on the
same database snapshot, defaulting to seven calendar dates. Output includes
tracker IDs, tags, templates, scan dates, PDF versus notification counts, Qualys
error overlays, exclusions, and source-code hashes, including uncommitted edits.

These are separate stages, not a claim that discovery counts equal PDF counts.
Legacy AM tag lookups use the included schedule tag ID and missing next-launch
dates receive a neutral placeholder; adaptations are recorded. Report linkage
to discovery is at tag/schedule level only, not proof of the same execution.
This command does not predict reports after a future tracker refresh or verify
slice completeness, NWS history, generated PDF content, or delivered mail.
Differences require explanation and approval, not automatic acceptance as parity.

For an offline discovery regression check, keep the original snapshot and choose
a new output filename:

```bash
make report-alignment-diagnostic-local \
  DIAGNOSTIC_SNAPSHOT=/absolute/path/report-alignment-previous.snapshot.json \
  DIAGNOSTIC_OUTPUT=/absolute/path/report-alignment-replay.json
```

Offline replay makes no database or Qualys calls. It reruns discovery/early-filter
logic against frozen inputs; stored report eligibility remains the captured SQL
result, explicitly not a fresh evaluation of changed eligibility SQL. Window
arguments apply to live capture; offline replay uses the snapshot's windows.
For eligibility SQL changes, run the diagnostic live again and review database
timestamp/source hashes before attributing differences to code. Files are never
overwritten. Snapshots exclude passwords, POC addresses, findings, and full notes;
they still contain customer tags and scan names and should remain private.

```bash
make recent-scan-batch TRACKER_LOOKBACK_DAYS=5 BATCH_DAYS_BACK=14
make recent-scan-batch BATCH_DAYS_BACK=all
```

`BATCH_DAYS_BACK=all` removes the report-generation and delivery date guardrail
for existing tracker data; it does not discover every historical execution or
override newest-row selection. Use it only for an intentional historical
reconciliation. After refreshing
the tracker and before starting any report worker, the Make target runs a
read-only preflight. It prints the eligible candidate total, counts by template,
and the number of Qualys-error overlays. The five phase messages identify tracker
refresh, preflight, generation, report delivery, and assignee digest delivery.
Each worker also reports its candidate fraction, such as `3/8`.

Run a read-only preflight directly without claiming reports or sending email:

```bash
docker run --rm \
  --env-file .env \
  was-reporting \
  --recent-scans \
  --skip-tracker-refresh \
  --preflight-only \
  --days-back 7
```

Run a real parallel end-to-end batch while redirecting every report, retry, and
assignee digest to one or more email-enabled functional-test recipients:

Customer report emails redirected with `--test-recipients` include a
`TEST DELIVERY ONLY` block showing the original technical POC and distribution
addresses in both plain text and HTML. These addresses are informational only;
they are not added to To, CC, or BCC. Normal customer deliveries keep the approved
template unchanged. Manual analyst-only report copies do not receive this block.

```bash
make recent-scan-batch-assignee-test \
  TEST_RECIPIENTS="analyst@example.gov"
```

This command uses the same 30-container default as the production batch. It
does not use customer email addresses. Recipient validation requires every
submitted address to belong to an email-enabled `was_assignees` row. The row may
be inactive so development testers remain outside daily operations. This is a
live test that generates reports, archives them to S3, sends SES email, and
updates successful tracker rows as sent. As a safety guardrail, report
generation and completed-report retries are limited to
tracker rows within `BATCH_DAYS_BACK`, defaulting to the same seven calendar dates
as the production batch and counts-only preview. Set `BATCH_DAYS_BACK=30` for an
explicit longer test, or `BATCH_DAYS_BACK=all` to remove the date limit.
The shared analyst summary includes this batch's attempts plus all open manuals,
including older manual work outside the generation window. Both summary emails
use the test-recipient override during functional tests.
Automated report generation
selects only the newest non-legacy tracker row for each stakeholder tag, so an
older unsent row cannot trigger another current tag-level report.

For a controlled end-to-end batch test, redirect every report and digest to one
or more email-enabled functional-test recipients. Customer addresses are not
used, but successful tracker rows are recorded as sent:

```bash
docker run --rm \
  --env-file .env \
  was-reporting \
  --recent-scans \
  --create-missing-password \
  --continue-on-error \
  --send-email \
  --send-assignee-digests \
  --test-recipients "operator@example.gov"
```

Test one candidate without sending SES email. This still performs Qualys report
generation and S3 upload:

```bash
docker run --rm \
  --env-file .env \
  was-reporting \
  --recent-scans \
  --create-missing-password \
  --continue-on-error \
  --send-email \
  --send-assignee-digests \
  --test-recipients "operator@example.gov" \
  --dry-run-email \
  --limit 1
```

Use `--skip-tracker-refresh` to process existing tracker gaps without querying
Qualys schedule and scan metadata again. Use `--tag "CUSTOMER_TAG"` to scope
both tracker refresh and report generation to one stakeholder.

### Run One Manual Report

Generate, upload, email, and track one manual report for an existing unsent
tracker row:

```bash
make manual-report TAG="CUSTOMER_TAG"
```

This command does not refresh Qualys tracker schedules. It processes the oldest
eligible manual tracker row for the exact tag, retries a previous failed
generation claim when present, uploads the encrypted PDF to S3, sends it through
SES, and sets `report_sent_date` only after SES accepts the message. Previously
failed email delivery is retried without regenerating an already completed PDF.
The tag requirement prevents an accidental manual run across all stakeholders.

Run the WAS mailer for all completed report runs that have not been emailed:

```bash
docker run --rm \
  --env-file .env \
  --entrypoint ./worker/was-mailer-start.sh \
  was-reporting \
  --all-ready
```

Smoke test the mailer without sending an email:

```bash
docker run --rm \
  --env-file .env \
  --entrypoint ./worker/was-mailer-start.sh \
  was-reporting \
  --all-ready \
  --test-recipients "operator@example.gov" \
  --dry-run \
  --limit 1
```

`--test-recipients` overrides stakeholder recipients and should be used for
non-production validation. The mailer does not include the report password in
the email body.

For operational tracker-driven delivery, the mailer always combines
`tech_poc_email` and `distro_email`, removes duplicate addresses, and signs the
customer message with one assigned analyst followed by the WAS team identity
and `reports@cyber.dhs.gov`. Password delivery is an onboarding or
analyst-managed process and is not performed by report automation.

Tracker templates control delivery behavior:

- `Results`, `Action Required`, `FCEB Action Required`, and `Targets Removed`
  include the generated PDF.
- `All NWS` and `FCEB All NWS` send a notification without generating or
  attaching a PDF.
- FCEB web applications are never automatically removed for NWS results.
- Non-FCEB removal candidates require an explicitly destructive tracker refresh.
  If deletion is disabled, the row is marked for analyst action and no email
  claims that a target was removed.
- A `Targets Removed` row is stored only after the Qualys deletion calls return
  successfully. A separate destructive-action audit record remains deferred to
  its approved future sprint.
- Opt-in deletion first commits a `MANUAL QUALYS DELETION PENDING` tracker
  claim. Interrupted or failed deletions require reconciliation, not automatic
  replay. A non-destructive `QUALYS DELETION REQUIRED` row can be processed by
  a subsequent explicit deletion refresh before reporting has started.
- Historical date-only rows with the same schedule and Eastern scan date
  require reconciliation instead of guessing an execution timestamp and
  generating a duplicate report. Already-finished keyed rows are not reinserted.
- Qualys error application URLs are listed in the customer message to identify
  applications without updated results. Report-generation and delivery failures
  remain in the assignee digest instead of producing immediate customer mail.

Customer messages display the available next-scan date in Eastern Time, include
the approved Cyber Hygiene and scanner allowlist links, and retain the temporary
sensitive-data attachment notice until Qualys restores that capability. Removal
eligibility uses two consecutive inaccessible scans.

The supplied Outlook `.msg` files are the source for customer-facing email
wording. Their reusable sections are maintained in
`src/was_mailer/customer_email_templates.py` and composed by
`src/was_mailer/message.py` according to the tracker outcome. Report-only
sections are omitted for notification runs without a PDF, and NWS, FCEB,
removed-target, and Qualys-error sections are included only when applicable.
The production workflow does not send Microsoft Teams notifications.

Run the WAS mailer for one completed report run:

```bash
docker run --rm \
  --env-file .env \
  --entrypoint ./worker/was-mailer-start.sh \
  was-reporting \
  --report-run-id 123
```

Use `--include-previous-failures` with `--all-ready` when retrying report runs
that already have `email_error` populated.
The mailer downloads each S3 report into a private temporary directory, builds
the SES message, and removes the local copy before sending. Existing local paths
are accepted only when `WAS_REPORT_STORAGE=local`, must reference a PDF, and must
resolve beneath `WAS_OUTPUT_DIRECTORY`.

### Shared Analyst Batch Summaries

The reporting batch sends two shared SES emails, not individual assignment
emails. Both include all analysts with `was_assignees.email_enabled IS TRUE`,
including inactive analysts. This does not change eligibility for assignments.
Test-recipient overrides apply to both emails and must resolve to email-enabled
analysts. Customer reports retain their existing delivery behavior.

The tracker-completion email summarizes the planned workload before generation:
report counts, NWS/error report and affected-webapp counts, tracker duration, and
refresh errors. NWS and error categories can overlap. Unavailable counts are not
presented as zero.

The final email reports generation counts, timing, and errors. Its body lists only
open manuals, sorted by assignee and identifying the assignee for each item.
The CSV includes attempted tracker rows, including failures and unsent reports,
plus open manuals, deduplicated by tracker ID. Password fields are excluded.

Batch IDs and per-report attempt records preserve scope across parallel workers.
Each email phase is claimed once; an uncertain send is held for review, not
automatically resent. Check SES before resetting any sending/held phase.
Existing databases require the local additive migration
`schema/updates/017_shared_analyst_batch_summaries.sql` before deployment.
The comprehensive schema includes `was_batch_runs` and
`was_batch_report_attempts`. Incremental SQL remains local and untracked.

To send the final summary for an existing batch, replace `BATCH_ID` with the
identifier printed by that batch:

```bash
docker run --rm \
  --env-file .env \
  --entrypoint ./worker/was-mailer-start.sh \
  was-reporting \
  --assignee-digests --batch-id BATCH_ID
```

Preview a batch summary without sending:

```bash
docker run --rm \
  --env-file .env \
  --entrypoint ./worker/was-mailer-start.sh \
  was-reporting \
  --assignee-digests \
  --batch-id BATCH_ID \
  --test-recipients "operator@example.gov" \
  --dry-run
```

### Temporary Sensitive-Findings Suspension

SSN and credit-card findings requests are temporarily commented out in
`write_sensitive_data_attachment`. Attachment 7 remains header-only, and logs
explicitly identify the data as unavailable, not an absence of findings.
The TODO records the operator-reported Qualys fix date of October 9, 2026.
Re-enabling requires validation and explicit approval; there is no automatic
date-based switch. Critical/urgent vulnerability-age queries remain active.

### Manage Special Cases

`was_special_cases` stores active tag values that should bypass automatic NWS
deletion logic. The initial seeded values are `CROSSFEED`, `CBOE`, and `SCCCS`.

Existing databases require a DBA-reviewed additive change for the special-case
table before using this command. The canonical final-state definition is in
`schema/stakeholders_table_creation.sql`.

List active special cases:

```bash
docker run --rm \
  --env-file .env \
  was-reporting \
  was-special-cases list
```

Add or reactivate a special case:

```bash
docker run --rm \
  --env-file .env \
  was-reporting \
  was-special-cases add "CUSTOMER_TAG"
```

Deactivate a special case without deleting history:

```bash
docker run --rm \
  --env-file .env \
  was-reporting \
  was-special-cases remove "CUSTOMER_TAG"
```

### Export Tracker CSV

Export tracker rows from Postgres to CSV:

```bash
docker run --rm \
  --env-file .env \
  -v "$(pwd)/local-output:/output" \
  was-reporting \
  was-tracker export-csv \
  --output /output/was-daily-tracker.csv
```

Export one pull date:

```bash
docker run --rm \
  --env-file .env \
  -v "$(pwd)/local-output:/output" \
  was-reporting \
  was-tracker export-csv \
  --data-pull-date "2026-08-26" \
  --output /output/was-daily-tracker-2026-08-26.csv
```

Export the recent tracker rows for one assignee:

```bash
make tracker-csv ASSIGNEE="Mina Salehi" DAYS_BACK=7
```

This writes the filtered CSV to
`local-output/was-daily-tracker.csv`. When `ASSIGNEE` is omitted,
`make tracker-csv` preserves the existing behavior and exports all tracker
rows. The equivalent Docker filters are `--assignee "ASSIGNEE NAME"` and
`--days-back 7`.

### View The Live Tracker Table

Display current tracker rows directly from Postgres without waiting for a CSV
export or assignee digest email:

```bash
make tracker-table ASSIGNEE="ASSIGNEE NAME" DAYS_BACK=7
```

`DAYS_BACK=7` includes today and the previous seven calendar days. The
assignee match is case-insensitive and must otherwise match the stored name.
Enter the assignee's stored name, not an email address, stakeholder tag, or user
ID. Leave the assignee prompt blank to include all assignees. The CLI reports
whether a supplied name is absent from `was_assignees`, inactive, or valid but
has no tracker rows matching the selected date and status filters.
The terminal output excludes report passwords, POC email addresses, and
customer notes. In the operator menu, `View tracker table` prompts for the
number of rows to display. Press Enter to use the 200-row default, enter a
positive whole number for a custom limit, or enter `all` to display every row
matching the selected filters.

Use `Report Tracker`, then `View one tracker row`, to inspect every safe field
for a tracker ID shown in the table. The compact field table truncates long
values for readability and then repeatedly prompts for a field name whose
complete value should be printed for copying. Report passwords and active
email claim tokens are excluded from this view. The equivalent direct command
is:

```bash
docker run --rm \
  --env-file .env \
  was-reporting \
  was-tracker show-row \
  --tracker-id 123
```

Add `--field customer_notes` to print one complete field value without table
truncation.

Display only manual tracker rows across all assignees:

```bash
make tracker-table REPORT_STATUS=manual DAYS_BACK=7
```

Combine `ASSIGNEE` and `REPORT_STATUS=manual` to restrict the manual queue to
one analyst. Valid report status filters are `manual`, `pending`, and `sent`.
The first table column is the tracker row ID used for manual reconciliation.

Equivalent Docker command with a custom row limit:

```bash
docker run --rm \
  --env-file .env \
  was-reporting \
  was-tracker show \
  --assignee "ASSIGNEE NAME" \
  --days-back 7 \
  --limit 100
```

Use `--limit all` to remove the row limit. Large result sets may take longer to
display and can produce substantial terminal output.

### Import A Legacy Daily Tracker Workbook

Convert and import rows from an existing WAS daily tracker workbook:

```bash
make tracker-import INPUT_XLSX="/path/to/WAS_TRACKER_DailyReports_UpdatedDaily.xlsx"
```

The importer validates the expected 20 workbook columns, converts Excel and
`MM/DD/YYYY` dates to PostgreSQL dates, and preserves non-date values from the
legacy `Report Sent Date` column in `report_scan_notes`. It resolves known
assignee names to `was_assignees`, preserves unknown assignee names as text,
and reports them to the operator.

Each converted row receives a deterministic `legacy-import` execution key.
When the schedule ID and scan start date are present, that pair identifies the
legacy scan execution. A later row for the same execution overwrites the
XLSX-owned fields on the existing legacy row without changing its database ID,
delivery state, digest state, report-run linkage, or creation metadata. A blank
imported report-sent date does not clear a stored sent date. Rows on different
scan dates remain separate history even when they share a recurring schedule ID.
Rows missing either key component retain fingerprint-based insert behavior.

Within one workbook, the last row for a repeated legacy execution is
authoritative. The importer stops before making changes when the database still
contains multiple legacy rows for one schedule ID and scan date; reconcile those
rows first so the overwrite target is unambiguous. Imported historical rows are
held from assignee digest delivery and excluded from report-generation
eligibility. The complete import is committed atomically, and any conversion or
database failure rolls it back.

The same operation is available under `Report Tracker`, then `Import tracker
rows from XLSX`. Before starting `make menu`, copy the workbook into
the EC2 checkout's `backend/was` directory. From a workstation using the WAS
SSH tunnel, run:

```bash
scp -P 7777 -i ~/.ssh/accessor_rsa \
  "/local/path/WAS_TRACKER_DailyReports_UpdatedDaily.xlsx" \
  ubuntu@127.0.0.1:~/code/cd_WAS_update/backend/was/
```

The menu mounts that EC2 directory read-only at `/backend/was` inside the
container. Press Enter to use the default
`/backend/was/WAS_TRACKER_DailyReports_UpdatedDaily.xlsx`, or enter
`/backend/was/FILE_NAME.xlsx` when the uploaded filename differs. Spaces in a
filename do not require escaping when entered at the menu prompt. Do not enter
`~` or the EC2 host's `/home/ubuntu/...` path because those paths do not exist
inside the container.

During import, the operator sees status messages for workbook validation,
database connection, duplicate-check loading, assignee loading, conversion,
5,000-row progress intervals, database staging, and the final commit. The final
summary distinguishes inserted rows, overwritten rows, duplicate workbook rows,
database conflict rows, blank rows, and unknown assignee names. A successful
zero-row import explicitly states that no data was added or overwritten.

Invalid headers, unsupported dates, and invalid schedule IDs identify the
workbook row that failed. A conversion or database failure rolls back the full
transaction and tells the operator that no rows were committed. Detailed
exception origin and database diagnostics remain in the timestamped WAS
application log under `local-output/logs`.

Record the sent date when a manual report was delivered outside the automated
SES workflow:

```bash
make tracker-mark-sent TRACKER_ID=123 SENT_DATE=2026-09-02
```

The command only updates an unsent row already classified for manual handling.
It requires explicit confirmation internally and will not overwrite an existing
sent date. In the interactive menu, this operation displays manual tracker rows
first, with optional assignee, date-window, and row-limit filters, so the
operator can select the correct tracker row ID without leaving the workflow.

### View Persisted Report Errors

Display report generation and SES delivery failures recorded in Postgres:

```bash
make report-errors DAYS_BACK=7
```

Restrict the error history to one stakeholder:

```bash
make report-errors TAG="CUSTOMER_TAG" DAYS_BACK=30
```

The error table excludes report passwords and recipient addresses. Container
stdout and platform logs remain useful for detailed diagnostics, while this
command provides durable operator-visible failure summaries from
`was_report_runs`.

### Update Daily Tracker

Run the Qualys daily tracker update and write tracker rows to Postgres. This
default command is non-destructive and does not delete Qualys web applications:

```bash
docker run --rm \
  --env-file .env \
  was-reporting \
  was-update-tracker
```

Scope a non-destructive validation run to one exact stakeholder tag:

```bash
docker run --rm \
  --env-file .env \
  was-reporting \
  was-update-tracker --tag "CUSTOMER_TAG"
```

Run the same workflow and allow Qualys web application deletions identified by
the NWS removal workflow:

```bash
docker run --rm \
  --env-file .env \
  was-reporting \
  was-update-tracker --delete-apps
```

## Developer Usage

Developers can run `was-reports` directly after installing the package locally.
This is for development and testing only. Operator documentation should use
container commands.

```bash
was-reports --tag "CUSTOMER_TAG" --change-password
```

## Export Sanitized XML

Export a sanitized XML-only report for one stakeholder from the container. The
command removes Qualys company and user metadata before writing the file.

```bash
mkdir -p local-output
docker run --rm \
  --env-file .env \
  -v "$(pwd)/local-output:/output" \
  was-reporting \
  was-export-xml \
  --tag "REPLACE_WITH_CUSTOMER_TAG" \
  --filename "customer-report.xml" \
  --output-directory /output
```

The tag value should be quoted. Replace `REPLACE_WITH_CUSTOMER_TAG` with the
stakeholder tag stored in Qualys.

## List WAS Stakeholders

List the child tags under `WAS_CUSTOMERS` with each tag's Qualys web
application count:

```bash
docker run --rm \
  --env-file .env \
  was-reporting \
  was-inventory
```

The command is read-only and prints stable tab-separated output with tag,
description, and web application count columns.

The full Qualys stakeholder inventory may take a long time to finish. It is no
longer offered in the interactive menu; use the Qualys web UI or invoke this
read-only CLI explicitly when needed.

## Qualys Administration

The original tag, false-positive, reactivation, and deletion workflows are
available through the guarded `was-admin` command. These commands modify
Qualys state, are not part of scheduled report generation, and require an
explicit confirmation argument. They accept validated values directly instead
of reading operator-managed CSV files.

Add or remove a stakeholder tag from one exact web application URL:

```bash
docker run --rm --env-file .env was-reporting was-admin \
  add-tag \
  --url "https://REPLACE_WITH_WEB_APPLICATION_URL" \
  --tag "REPLACE_WITH_QUALYS_TAG" \
  --confirm

docker run --rm --env-file .env was-reporting was-admin \
  remove-tag \
  --url "https://REPLACE_WITH_WEB_APPLICATION_URL" \
  --tag "REPLACE_WITH_QUALYS_TAG" \
  --confirm
```

Mark one finding as a false positive. Do not place sensitive data in the
comment because the comment is stored by Qualys:

```bash
docker run --rm --env-file .env was-reporting was-admin \
  false-positive \
  --finding-id "REPLACE_WITH_FINDING_ID" \
  --comment "REPLACE_WITH_APPROVED_JUSTIFICATION" \
  --confirm
```

Reactivate one web application and set one or more tags. Repeat `--tag` for
each tag that must be present:

```bash
docker run --rm --env-file .env was-reporting was-admin \
  reactivate \
  --url "https://REPLACE_WITH_WEB_APPLICATION_URL" \
  --tag "REPLACE_WITH_QUALYS_TAG" \
  --tag "REPLACE_WITH_ADDITIONAL_QUALYS_TAG" \
  --confirm
```

Deleting a web application also removes it from the Qualys subscription. The
operator must repeat the exact URL in `--confirm-url`:

```bash
docker run --rm --env-file .env was-reporting was-admin \
  delete-webapp \
  --url "https://REPLACE_WITH_WEB_APPLICATION_URL" \
  --confirm-url "https://REPLACE_WITH_WEB_APPLICATION_URL"
```

Use only approved nonproduction targets until the commands have completed live
Qualys validation. Container output records whether the requested operation
completed. On EC2, configure approved persistent log collection and retention;
transient container output alone is not a durable centralized audit log.

## Makefile Shortcuts

Run these from `backend/was`:

```bash
make build
make menu
make test
make lint
make xml-help
make inventory
make admin-help
make stakeholders-help
make special-cases
make stakeholder-export
make tracker-csv
make tracker-csv ASSIGNEE="ASSIGNEE NAME" DAYS_BACK=7
make tracker-table ASSIGNEE="ASSIGNEE NAME" DAYS_BACK=7
make tracker-table REPORT_STATUS=manual DAYS_BACK=7
make report-errors DAYS_BACK=7
make tracker-mark-sent TRACKER_ID=123 SENT_DATE=2026-09-02
make update-tracker
make update-tracker-delete-apps
make assignee-digests
make recent-scan-batch
make recent-scan-batch BATCH_WORKERS=30
make recent-scan-batch-assignee-test TEST_RECIPIENTS="analyst@example.gov"
make recent-scan-batch-test TEST_RECIPIENTS="operator@example.gov"
make single-report TAG="CUSTOMER_TAG"
make manual-report TAG="CUSTOMER_TAG"
```

## Test-Only Report Resends And Manual Retries

Use `make test-report-replay` to test existing PDFs and explicitly approved
manual retries without resetting tracker status, sent dates, or original report
runs. Run the test while normal batches are idle to avoid overlapping work for
different tracker rows belonging to the same tag. Apply local migration
`schema/updates/018_test_report_replay.sql` before
using the updated mailer. The same definitions are included in the comprehensive
`schema/stakeholders_table_creation.sql`; do not run that full creation script
against an existing database. Incremental update files remain local and ignored.

From `backend/was`, preview the last seven calendar dates, including today:

```bash
make test-report-replay DAYS_BACK=7 \
  TEST_RECIPIENTS="zachary.cogswell@associates.cisa.dhs.gov"
```

Preview does not update the database, call Qualys, or send email. The window uses
the tracker scan date, falling back to pull date, against the Eastern calendar.
Review the listed IDs. All recipients must be email-enabled assignees; inactive
assignees are allowed. There is no fallback to customer POCs.

For example, resend the existing PDF from report run `3081` to the test recipient:

```bash
make test-report-replay DAYS_BACK=7 REPORT_RUN_IDS=3081 \
  TEST_RECIPIENTS="zachary.cogswell@associates.cisa.dhs.gov" \
  REPLAY_ID="$(uuidgen)" APPLY=1
```

Save the replay ID printed by the command. If interrupted, reuse that exact ID;
do not generate another UUID blindly. Already reserved items are skipped even if
failed or interrupted, so inspect the child report-run status before considering
another replay. This deliberately favors avoiding duplicate sends over automatic
retry of uncertain delivery outcomes. The replay ID is bound to its recipient.

To generate a report for an incorrectly marked manual, explicitly select its
tracker ID with `MANUAL_TRACKER_IDS=123` (replace `123` with a reviewed eligible
ID). Omit `APPLY=1` first to preview that selection. Multiple IDs use commas.
`REPORT_RUN_IDS` selects archived PDFs; `MANUAL_TRACKER_IDS` selects generation.
No command automatically retries every manual row.

Resends reuse the archived PDF; manual generation queries current Qualys data,
not a guaranteed historical scan snapshot. Email bodies are rendered using the
current template code and tracker/customer context, with the original POC
addresses shown as test information, not recipients. This is not a byte-identical
replay of an archived email. New test runs have analyst delivery purpose and do
not alter the original tracker or delivery history, including its manual notes.
No shared analyst digest is sent by this command.

## On-Demand Generation, S3 Archive, And Email

Use this workflow when you need a new report regardless of recent-scan tracker
eligibility. It uses the existing production PDF generator, S3 storage, and SES
mailer. It does not rerun Qualys scans or overwrite an earlier report run.

After pulling these changes on EC2, run `make build`. Generate and archive a
new report without emailing:

```bash
make on-demand-report TAG="CROSSFEED"
```

Generate, archive, and send one approved functional-test report:

```bash
make on-demand-report TAG="CROSSFEED" SEND_EMAIL=1 \
  TEST_RECIPIENTS="craig.duhn@associates.cisa.dhs.gov"
```

The command prints the new run ID, S3 reference, and SES message ID. It uses
the stakeholder's stored encryption password, generating and storing one only
if missing. It sends no assignee digest. Successful SES acceptance is not
proof of inbox delivery. Every supplied recipient must match an active,
email-enabled address in `was_assignees`; customer contacts are rejected for
on-demand delivery.

In `make menu`, select **Report generation**, then **4, Generate an on-demand
report to S3 (optional email)**. Enter the enrolled stakeholder tag, choose whether
to email, enter email-enabled analyst addresses if sending, and confirm the operation.
Leave the tracker ID blank for an unlinked report run. Options 2 and 3 remain eligibility
driven and are not force-generation commands.

For a real, unsent tracker row belonging to this tag, add `TRACKER_ID=123` to
the Make command or supply it at the menu prompt. Replace `123` with the actual
tracker ID, not a report-run ID. The row must not already have a linked run.
Analyst delivery does not mark that tracker row as sent to the customer.
Without an explicit tracker ID, only `was_report_runs` is updated; no scan
records or scan dates are fabricated. An override recipient still marks an
explicitly linked tracker row sent, so use a designated test row for testing.

On-demand reports start with `email_status=held`. Scheduled/bulk mailers do
not pick them up, including when an explicit email attempt fails. This prevents
test reports from being sent accidentally to the customer's stored recipients.
Use the explicit mailer command to send or retry an already archived report:

```bash
docker run --rm --env-file .env --entrypoint was-mailer was-reporting \
  --report-run-id NEW_RUN_ID \
  --test-recipients "craig.duhn@associates.cisa.dhs.gov" \
  --delivery-purpose analyst \
  --include-previous-failures
```

Replace `NEW_RUN_ID` with the printed numeric run ID. Already-sent or actively
claimed email runs cannot be sent again by this command. Re-running generation
after completion intentionally creates a different run and can send another
email; it is not an email-retry operation. Concurrent on-demand claims for the
same tag serialize through a stakeholder-row lock and reject an existing active
run. Existing scheduled batch eligibility is unchanged. A crashed run left in
`running` or an uncertain email left in `sending` needs operator reconciliation,
not blind regeneration or database status resets.

The lower-level `was-report-on-demand` CLI defaults to archive-only and requires
`--send-email` plus `--test-recipients` containing only email-enabled
functional-test addresses to send. `was-reports` remains local-PDF-only. The on-demand command explicitly uses
S3 even if `WAS_REPORT_STORAGE=local`; the bucket and IAM permissions must be
configured. The updated container enables unbuffered output and a writable
Matplotlib cache. Persisted `delivery_purpose=analyst` enforces analyst-only
recipients in the direct mailer as well as the menu. The internal `allow_held`
claim option changes eligibility only; it does not override the stored purpose or select a different
customer template. The operator-confirmed database changes are complete; deploy
against the comprehensive schema documented above. Verify schema readiness
separately for any other environment.

Follow `docs/live_qualys_equivalence_runbook.md` for S3, database, inbox, and
failure verification. Do not declare the live test passed solely because a
container exits successfully.

## Validate

Run focused tests from the repository root:

```bash
PYTHONPATH=backend/was/src ./cd_WAS_update/bin/python -m unittest \
  backend/was/tests/test_report_generator.py \
  backend/was/tests/test_passwords.py
```

Run syntax checks:

```bash
./cd_WAS_update/bin/python -m py_compile \
  backend/was/src/was_reports/commands/report_generator.py \
  backend/was/src/was_reports/data/stakeholders.py \
  backend/was/src/was_reports/utils/passwords.py \
  backend/was/src/was_reports/utils/database.py \
  backend/was/setup.py \
  backend/was/schema/stakeholders.py

bash -n backend/was/worker/was-report-start.sh
```

## Migration Notes

- DynamoDB stakeholder lookups in the active report and daily tracker paths are
  replaced by Postgres `was_stakeholders`.
- The daily tracker XLSX output path is replaced by Postgres
  `was_daily_report_tracker`.
- The legacy `No NWS Deletions` special-cases workbook is replaced by Postgres
  `was_special_cases`.
- The current password model is stakeholder-level, not per-report.
- The production PDF generator preserves the approved Mustache and XeLaTeX
  report format. A future ReportLab rewrite remains a separate project phase.
- Qualys retrieval, report transformation, PDF generation, encryption,
  storage, and delivery are separated into WAS-owned modules under `src`.
