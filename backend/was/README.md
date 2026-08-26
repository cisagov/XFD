# WAS Reporting

WAS Reporting generates Web Application Scanning PDF reports from Qualys data.
The current implementation keeps the legacy PDF generator intact and adds a
WAS-owned command line boundary for containerized execution, Postgres
stakeholder lookup, and report password management.

## Current Architecture

- `was-report-batch` is the default container command for scheduled reports.
- `was-reports` generates or manages one stakeholder report.
- `src/was_reports/report_generator.py` validates CLI input and calls the
  legacy report creator.
- `was_report/WAS_report_creator.py` still performs Qualys data retrieval,
  transformation, PDF creation, and PDF encryption.
- `src/was_reports/data/stakeholders.py` reads and updates stakeholder report
  passwords in Postgres.
- `src/was_reports/data/report_runs.py` records scheduled report execution
  status in Postgres.
- `src/was_reports/utils/database.py` creates Postgres connections from
  environment variables.
- `src/was_reports/utils/passwords.py` generates and validates WAS report
  passwords.
- `worker/was-report-start.sh` runs the scheduled report batch command.

## Required Environment Variables

Set these values before running report generation or password management:

```bash
export WAS_DB_HOST="your-rds-endpoint"
export WAS_DB_NAME="was"
export WAS_DB_USERNAME="was_app"
export WAS_DB_PASSWORD="your-password"
export WAS_DB_PORT="5432"
export WAS_DB_SSLMODE="require"
export WAS_PASSWORD_LENGTH="24"
export WAS_CONFIG_PATH="/app/was_config.txt"
export WAS_LEGACY_ROOT="/WAS_REPORT_GENERATION"
export WAS_OUTPUT_DIRECTORY="/WAS_REPORT_GENERATION/docs"
export WAS_EMAIL_SOURCE="verified-sender@example.gov"
```

Do not commit `.env`, `was_config.txt`, database passwords, Qualys credentials,
or generated reports.

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
  -v /local/path/was_config.txt:/app/was_config.txt:ro \
  -v /local/output:/WAS_REPORT_GENERATION/docs \
  was-reporting \
  --create-missing-password
```

Limit a test run to one due stakeholder:

```bash
docker run --rm \
  --env-file .env \
  -v /local/path/was_config.txt:/app/was_config.txt:ro \
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
  -v /local/path/was_config.txt:/app/was_config.txt:ro \
  -v /local/output:/WAS_REPORT_GENERATION/docs \
  was-reporting \
  was-reports \
  --tag "CUSTOMER_TAG" \
  --config-path /app/was_config.txt \
  --legacy-root /WAS_REPORT_GENERATION
```

Generate a report and create a stakeholder password if one does not exist:

```bash
docker run --rm \
  --env-file .env \
  -v /local/path/was_config.txt:/app/was_config.txt:ro \
  -v /local/output:/WAS_REPORT_GENERATION/docs \
  was-reporting \
  was-reports \
  --tag "CUSTOMER_TAG" \
  --create-missing-password \
  --config-path /app/was_config.txt \
  --legacy-root /WAS_REPORT_GENERATION
```

Allow an unencrypted output only when intentionally approved:

```bash
docker run --rm \
  --env-file .env \
  -v /local/path/was_config.txt:/app/was_config.txt:ro \
  -v /local/output:/WAS_REPORT_GENERATION/docs \
  was-reporting \
  was-reports \
  --tag "CUSTOMER_TAG" \
  --allow-unencrypted \
  --config-path /app/was_config.txt \
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
  -v /local/path/was_config.txt:/app/was_config.txt:ro \
  -v /local/output:/WAS_REPORT_GENERATION/docs \
  was-reporting \
  was-reports \
  --tag "CUSTOMER_TAG" --create-missing-password
```

Change an existing stakeholder password by generating a new password:

```bash
docker run --rm \
  --env-file .env \
  -v /local/path/was_config.txt:/app/was_config.txt:ro \
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
  -v /local/path/was_config.txt:/app/was_config.txt:ro \
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

## Developer Usage

Developers can run `was-reports` directly after installing the package locally.
This is for development and testing only. Operator documentation should use
container commands.

```bash
was-reports --tag "CUSTOMER_TAG" --change-password
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
  backend/was/src/was_reports/report_generator.py \
  backend/was/src/was_reports/data/stakeholders.py \
  backend/was/src/was_reports/utils/passwords.py \
  backend/was/src/was_reports/utils/database.py \
  backend/was/setup.py \
  backend/was/schema/stakeholders.py

bash -n backend/was/worker/was-report-start.sh
```

## Migration Notes

- DynamoDB stakeholder password lookup is being replaced by Postgres
  `was_stakeholders.report_password`.
- The current password model is stakeholder-level, not per-report.
- The legacy PDF generator has not yet been rewritten to ReportLab.
- The next refactor should split Qualys retrieval, report transformation, PDF
  generation, encryption, and delivery into separate WAS-owned modules.
