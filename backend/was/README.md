# WAS Reporting

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
**5, Generate a new on-demand report**. Enter the approved stakeholder tag and
recipient, and leave the tracker ID blank unless intentionally linking an
existing test tracker row. This generates a PDF, archives it to S3, and
optionally emails it. It does not require recent-scan eligibility.

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

Changes only to `.env` do not require a build; start a new container to load
them. Compare updated `dev.env` with your local configuration after pulls and
add required keys without replacing secrets. Documentation-only changes do not
require rebuilding. After an approved live test, verify the S3 object, database
run status, inbox delivery, and PDF content, not just the exit code.

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
WAS_QUALYS_REQUEST_TIMEOUT_SECONDS=60
WAS_QUALYS_RETRY_BASE_DELAY_SECONDS=1
WAS_QUALYS_RETRY_MAX_DELAY_SECONDS=30
WAS_QUALYS_RETRY_JITTER_RATIO=0.25
WAS_QUALYS_REPORT_POLL_TIMEOUT_SECONDS=1800
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
Create, update, ignore, and delete operations are never automatically retried
because repeating them could duplicate or alter Qualys state. Report-status
polling stops after `WAS_QUALYS_REPORT_POLL_TIMEOUT_SECONDS` instead of waiting
indefinitely.

### Qualys API Rate Limit

The operator-reported Qualys API rate limit for this WAS environment is
**2,000 requests per hour**. Confirm the applicable subscription limit and
its scope with the Qualys administrator before increasing workload concurrency;
this value should not be assumed to apply to every Qualys subscription or API.

Plan concurrent report generation, tracker refreshes, and inventory queries
within that limit, accounting for other clients sharing the same quota. The
retry behavior described above handles throttling responses; it is not a
guarantee that combined workloads stay below 2,000 requests per hour.

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

Apply the report-run claim update to an existing WAS database before deploying
this code:

```bash
PGPASSWORD="$WAS_DB_PASSWORD" psql \
  --host "$WAS_DB_HOST" \
  --port "$WAS_DB_PORT" \
  --username "$WAS_DB_USERNAME" \
  --dbname "$WAS_DB_NAME" \
  -f schema/updates/008_add_report_run_delivery_claims.sql
```

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

### Export Stakeholders

Export all non-secret stakeholder columns to an owner-readable CSV:

```bash
make stakeholder-export
```

This writes `local-output/was-stakeholders.csv` with file mode `0600` and
neutralizes spreadsheet formulas in non-password text fields. Report passwords
are excluded by default.

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

### Interactive Operator Menu

Launch the numbered WAS operator menu from `backend/was`:

```bash
make menu
```

The menu groups existing commands into Report Generation, Daily Tracker,
Stakeholder Management, and Qualys Operations. It supports guided prompts,
confirmation before write or delivery operations, `CLEAR` for removing contact
values, and typed confirmation before exporting report passwords. Files are
written under the mounted `local-output` directory.

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

Apply the tracker link once to an existing WAS database before using this mode:

```bash
psql \
  --host "$WAS_DB_HOST" \
  --port "$WAS_DB_PORT" \
  --username "$WAS_DB_USERNAME" \
  --dbname "$WAS_DB_NAME" \
  --file schema/updates/008_link_report_runs_to_daily_tracker.sql
```

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

### Send Assignee Tracker Digests

Assignee tracker digest emails use `was_assignees.email`. Populate that field
before enabling production delivery. `--test-recipients` should be used for
validation because it overrides the assignee email recipients.
Each digest includes a CSV attachment containing that assignee's tracker rows.

Apply the existing database update script before using this command against an
already-created WAS database:

```bash
PGPASSWORD="$WAS_DB_PASSWORD" psql \
  --host "$WAS_DB_HOST" \
  --port "$WAS_DB_PORT" \
  --username "$WAS_DB_USERNAME" \
  --dbname "$WAS_DB_NAME" \
  -f schema/updates/006_add_assignee_email_fields.sql
```

Send unsent tracker rows grouped by assignee:

```bash
docker run --rm \
  --env-file .env \
  --entrypoint ./worker/was-mailer-start.sh \
  was-reporting \
  --assignee-digests
```

Dry run assignee digests for one pull date:

```bash
docker run --rm \
  --env-file .env \
  --entrypoint ./worker/was-mailer-start.sh \
  was-reporting \
  --assignee-digests \
  --data-pull-date "2026-08-26" \
  --test-recipients "operator@example.gov" \
  --dry-run
```

### Manage Special Cases

`was_special_cases` stores active tag values that should bypass automatic NWS
deletion logic. The initial seeded values are `CROSSFEED`, `CBOE`, and `SCCCS`.

Apply the special-case table update against an already-created WAS database:

```bash
PGPASSWORD="$WAS_DB_PASSWORD" psql \
  --host "$WAS_DB_HOST" \
  --port "$WAS_DB_PORT" \
  --username "$WAS_DB_USERNAME" \
  --dbname "$WAS_DB_NAME" \
  -f schema/updates/007_create_was_special_cases.sql
```

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
The terminal output is limited to 200 rows by default and excludes report
passwords, POC email addresses, and customer notes.

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

Record the sent date when a manual report was delivered outside the automated
SES workflow:

```bash
make tracker-mark-sent TRACKER_ID=123 SENT_DATE=2026-09-02
```

The command only updates an unsent row already classified for manual handling.
It requires explicit confirmation internally and will not overwrite an existing
sent date.

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
make recent-scan-batch-test TEST_RECIPIENTS="operator@example.gov"
make single-report TAG="CUSTOMER_TAG"
make manual-report TAG="CUSTOMER_TAG"
```

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
proof of inbox delivery.

In `make menu`, select **Report generation**, then **5, Generate a new
on-demand report**. Enter the tag, choose whether to email, enter the explicit
recipient addresses if sending, and confirm the displayed operation. Leave
the tracker ID blank for a standalone run. Options 2 and 3 remain eligibility
driven and are not force-generation commands.

For a real, unsent tracker row belonging to this tag, add `TRACKER_ID=123` to
the Make command or supply it at the menu prompt. Replace `123` with the actual
tracker ID, not a report-run ID. The row must not already have a linked run.
SES acceptance updates that row's sent date through the existing atomic mailer.
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
`--send-email` plus either `--test-recipients` or `--stakeholder-recipients` to
send. `was-reports` remains local-PDF-only. The on-demand command explicitly uses
S3 even if `WAS_REPORT_STORAGE=local`; the bucket and IAM permissions must be
configured. The updated container enables unbuffered output and a writable
Matplotlib cache. No schema migration is required for the `held` status because
the existing `email_status` column is text without an enumerated constraint.

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
