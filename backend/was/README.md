# WAS Reporting

WAS Reporting generates Web Application Scanning PDF reports from Qualys data.
The current implementation keeps the legacy PDF generator intact and adds a
WAS-owned command line boundary for containerized execution, Postgres
stakeholder lookup, and report password management.

## Current Architecture

- `was-report-batch` is the default container command for scheduled reports.
- `was-reports` generates or manages one stakeholder report.
- `src/was_reports/commands` contains container command implementations. The
  report generator validates CLI input and calls the
  legacy report creator by default. An explicit migration-test flag can call
  the extracted pipeline without changing production routing.
- `src/was_reports/qualys` provides the WAS-owned Qualys API boundary and
  migrated report-data helpers
  for tag lookup, app counts, report creation, XML download, status checks, and
  temporary report cleanup.
- `src/was_reports/reporting` contains report retrieval, transformation,
  metrics, artifacts, charts, LaTeX rendering, PDF security, and comparison.
- `src/was_reports/resources` contains the packaged report template, Qualys XML
  templates, images, fonts, PDF backgrounds, watermark, and redaction helpers
  required for the future legacy-directory cutover.
- `src/was_reports/tracker` contains assignee allocation and CSV export logic.
- `was_report/WAS_report_creator.py` still performs Qualys data retrieval,
  transformation, PDF creation, and PDF encryption.
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
- `update_tracker/update_tracker` now writes daily tracker output to
  `was_daily_report_tracker` instead of saving the daily tracker XLSX file.
- `src/was_reports/utils/database.py` creates Postgres connections from
  environment variables.
- `src/was_reports/utils/passwords.py` generates and validates WAS report
  passwords.
- `worker/was-report-start.sh` runs the scheduled report batch command.
- `reporting.py` is a compatibility wrapper for `was-report-batch`; it no
  longer owns XLSX tracker orchestration, nested Docker execution, or DynamoDB
  password lookup.

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
WAS_SHARE_DRIVE=/WAS_REPORT_GENERATION
WAS_CONFIG_PATH=/WAS_REPORT_GENERATION/docs/was_config.txt
WAS_LEGACY_ROOT=/WAS_REPORT_GENERATION
WAS_OUTPUT_DIRECTORY=/WAS_REPORT_GENERATION/docs
WAS_WORKSPACE_ROOT=/tmp/was-report-workspaces
WAS_DAILY_WAS_LOG=/WAS_REPORT_GENERATION/WAS_Tools/update_tracker/dailywas.log
WAS_PASSWORD_LENGTH=24
WAS_EMAIL_SOURCE=verified-sender@example.gov
```

Do not commit `.env`, `was_config.txt`, database passwords, Qualys credentials,
or generated reports.

The modern WAS code reads constants from `backend/was/.env` during local
execution. In a container, pass the same file with `docker run --env-file .env`.
For legacy compatibility, WAS generates `was_config.txt` at `WAS_CONFIG_PATH`
from `WAS_QUALYS_USERNAME`, `WAS_QUALYS_PASSWORD`, and `WAS_QUALYS_HOSTNAME`
when that config file does not already exist.
`WAS_SHARE_DRIVE` represents the original shared-drive root. In the container
it defaults to `/WAS_REPORT_GENERATION`, which is the working directory created
for legacy-compatible WAS files.
When present, `WAS_DAILY_WAS_LOG` is also written into the generated legacy
`[was_files]` section. Daily tracker, customer data, and special-case XLSX paths
are no longer required by the active tracker workflow.

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

The WAS software is intended to run inside a container. Operators should use
Docker commands locally, or ECS task commands after the workload is deployed to
AWS.

Use `docker run` when starting a new one-off WAS report container. Use
`docker exec -it` only when a WAS container is already running.

### Generate Due Reports

Generate all due stakeholder reports from `was_stakeholders.next_scheduled`:

```bash
docker run --rm \
  --env-file .env \
  -v /local/output:/WAS_REPORT_GENERATION/docs \
  was-reporting \
  --create-missing-password
```

Limit a test run to one due stakeholder:

```bash
docker run --rm \
  --env-file .env \
  -v /local/output:/WAS_REPORT_GENERATION/docs \
  was-reporting \
  --create-missing-password \
  --limit 1
```

Each scheduled batch report creates a `was_report_runs` record. Successful
reports are marked `completed` with the expected PDF output path and artifact
type after the expected PDF file is present. Failed reports are marked `failed`.

### Generate One Report

Generate a report using an existing stakeholder password from Postgres:

```bash
docker run --rm \
  --env-file .env \
  -v /local/output:/WAS_REPORT_GENERATION/docs \
  was-reporting \
  was-reports \
  --tag "CUSTOMER_TAG" \
  --legacy-root /WAS_REPORT_GENERATION
```

Run the extracted pipeline only for controlled equivalence testing. This keeps
the same stakeholder tag and encryption-password inputs used by the legacy
workflow, but adds an explicit opt-in flag:

```bash
docker run --rm \
  --env-file .env \
  -v "$(pwd)/local-output:/WAS_REPORT_GENERATION/docs" \
  was-reporting \
  was-reports \
  -t "CUSTOMER_TAG" \
  --encrypt "TEST_PASSWORD" \
  --use-extracted-pipeline
```

Do not place a production password directly in interactive shell history.
Normal operation should continue resolving the stakeholder password from
Postgres by omitting `--encrypt`. The extracted route always requires
encryption and deletes its isolated temporary workspace after completion.
When the compatibility route invokes the legacy creator, it passes the
resolved password through a child-only environment variable rather than a
command-line argument. Operators should not set that internal variable.

Before Qualys credentials are available, run the offline container smoke test.
It uses representative XML with the real Mustache template, static report
assets, chart generators, XeLaTeX compiler, and PikePDF encryption:

```bash
mkdir -p local-output/offline-smoke
docker run --rm \
  -v "$(pwd):/workspace:ro" \
  -v "$(pwd)/local-output/offline-smoke:/offline-output" \
  --entrypoint python \
  was-reporting:extracted-validation \
  /workspace/scripts/offline_pipeline_smoke.py \
  --legacy-root /WAS_REPORT_GENERATION \
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
was-compare-reports /path/to/legacy.pdf /path/to/extracted.pdf
unset WAS_REPORT_COMPARISON_PASSWORD
```

The command compares encryption state, page count, page dimensions, normalized
page text hashes, selected metadata, and embedded attachment names and hashes.
It recognizes both document names-tree attachments and page-level attachment
annotations produced by XeLaTeX `attachfile2`. It never writes a decrypted
report to disk or prints the password.

Follow `docs/live_qualys_equivalence_runbook.md` for the complete approved
nonproduction validation sequence, required test matrix, cleanup checks, and
cutover criteria.

Generate a report and create a stakeholder password if one does not exist:

```bash
docker run --rm \
  --env-file .env \
  -v /local/output:/WAS_REPORT_GENERATION/docs \
  was-reporting \
  was-reports \
  --tag "CUSTOMER_TAG" \
  --create-missing-password \
  --legacy-root /WAS_REPORT_GENERATION
```

Allow an unencrypted output only when intentionally approved:

```bash
docker run --rm \
  --env-file .env \
  -v /local/output:/WAS_REPORT_GENERATION/docs \
  was-reporting \
  was-reports \
  --tag "CUSTOMER_TAG" \
  --allow-unencrypted \
  --legacy-root /WAS_REPORT_GENERATION
```

### Manage Report Passwords

`CUSTOMER_TAG` is a placeholder. Replace it with the exact stakeholder tag
stored in `was_stakeholders.tag`. Quotes are recommended because they are safe
for tags that contain spaces or shell-sensitive characters.

Create a missing password for a stakeholder during report generation:

```bash
docker run --rm \
  --env-file .env \
  -v /local/output:/WAS_REPORT_GENERATION/docs \
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
Current legacy compatibility still passes the password to the legacy generator
as a command argument. A future improvement should add password input through
standard input or an internal function call so the password is not visible in
process arguments.

## Container Usage

Build the image from `backend/was`:

```bash
docker build -t was-reporting .
```

Smoke test the container command routing without database or Qualys access:

```bash
docker run --rm was-reporting --help
docker run --rm was-reporting was-reports --help
```

Run the scheduled report batch container:

```bash
docker run --rm \
  --env-file .env \
  -v /local/output:/WAS_REPORT_GENERATION/docs \
  was-reporting \
  --create-missing-password
```

The mounted output directory is used by the legacy generator for report files
and supporting artifacts.

Run the WAS mailer for all completed report runs that have not been emailed:

```bash
docker run --rm \
  --env-file .env \
  -v /local/output:/WAS_REPORT_GENERATION/docs:ro \
  --entrypoint ./worker/was-mailer-start.sh \
  was-reporting \
  --all-ready
```

Smoke test the mailer without sending an email:

```bash
docker run --rm \
  --env-file .env \
  -v /local/output:/WAS_REPORT_GENERATION/docs:ro \
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
  -v /local/output:/WAS_REPORT_GENERATION/docs:ro \
  --entrypoint ./worker/was-mailer-start.sh \
  was-reporting \
  --report-run-id 123
```

Use `--include-previous-failures` with `--all-ready` when retrying report runs
that already have `email_error` populated.

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

Export the legacy XML-only report for one stakeholder from the container. The
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
completed, but durable centralized audit-log retention depends on the final ECS
logging configuration.

## Makefile Shortcuts

Run these from `backend/was`:

```bash
make build
make test
make lint
make xml-help
make inventory
make admin-help
make special-cases
make tracker-csv
make update-tracker
make update-tracker-delete-apps
make assignee-digests
```

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
- The legacy PDF generator has not yet been rewritten to ReportLab.
- The next refactor should split Qualys retrieval, report transformation, PDF
  generation, encryption, and delivery into separate WAS-owned modules.
