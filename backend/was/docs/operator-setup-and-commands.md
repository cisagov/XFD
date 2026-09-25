# WAS operator setup and command runbook

## Purpose

Use this runbook to create or update the supported EC2 checkout, build and
verify the WAS image, start the operator menu, run production and controlled
test workflows, and collect troubleshooting evidence. Run commands from
`backend/was` unless a step says otherwise.

This runbook does not authorize a production batch, database migration,
customer email, Qualys mutation, or capacity test. Obtain the required
operational approval before any command that changes external state.

## Supported operating model

- One Git checkout supplies the host coordinator and Docker build context.
- One private `.env` supplies database, Qualys, S3, SES, and logging settings.
- One local Python environment supports host-side production and capacity
  coordinators and the read-only log tools.
- Docker runs the operator menu and application workers.
- `schema/stakeholders_table_creation.sql` is the comprehensive schema for a
  new database. The application does not apply database migrations.
- Production and capacity batches use the same coordinator and separate Docker
  worker topology. Capacity runs select the isolated `TEST_WAS_DB_*` database
  and require an explicit test-recipient override.

## Prerequisites

Confirm the host has:

- approved GitHub SSH access to `cisagov/XFD`;
- Git, GNU Make, Python 3.12 or a compatible project-approved version, and
  Docker;
- network access to the configured PostgreSQL and Qualys endpoints;
- an EC2 instance role with the approved S3 access and permission to assume
  `WAS_SES_ROLE_ARN`;
- enough private disk space for the image, temporary workspaces, retained logs,
  capacity evidence, and approved database-reset backups;
- the database schema required by the checked-out code.

Do not put passwords, tokens, reports, database dumps, or `.env` in Git. Do not
enable shell tracing while handling credentials.

## First checkout

From the EC2 user's home directory:

```bash
mkdir -p "$HOME/code"
cd "$HOME/code"
git clone --branch cd_WAS_update --single-branch \
  git@github.com:cisagov/XFD.git cd_WAS_update
cd cd_WAS_update
python3 -m venv cd_WAS_update
cd backend/was
make install
./scripts/create-local-env.sh
chmod 600 .env
```

If the host uses an approved pre-existing Python environment, pass its Python
path to Make instead of creating the expected local environment:

```bash
make install PYTHON="/absolute/path/to/python"
```

`make install` must complete before using host-side batch, capacity, alignment,
or structured-log commands. If Python reports that `pip` is unavailable, repair
or recreate the environment before continuing. Do not bypass dependency
installation by invoking internal modules from an incomplete environment.

Populate `.env` from the approved secret source. `dev.env` documents names and
safe defaults only. Replace every placeholder and keep the file private. See
the [main README environment section](../README.md#local-environment-file) for
the current variable inventory.

## Build and verify

Run local validation before building when the host has the development
dependencies:

```bash
make test
make lint
make build
```

Verify that Docker can start the image and expose the supported commands:

```bash
docker image inspect was-reporting >/dev/null
make help
make report-help
make mailer-help
```

A successful build proves only that the image was created. It does not verify
database identity, Qualys retrieval, S3 archival, SES acceptance, PDF content,
or inbox delivery. Use the
[live validation runbook](live_qualys_equivalence_runbook.md) for controlled
end-to-end evidence.

## Start the operator menu

```bash
make menu
```

The menu exposes Report Generation, Report Tracker, and Stakeholder Management.
Option `0` is Quit or Back, depending on the current level. Capacity testing and
batch-log diagnostics intentionally remain host Make commands. The menu's
complete recent-scan action runs in the menu container; the supported parallel
production topology is `make recent-scan-batch` on the host. See [operator menu
workflows](operator-menu.md) before performing a write or email operation.

## Production batch workflow

Preview the currently stored eligible workload without refreshing, generating,
or sending:

```bash
make recent-scan-batch-preflight
```

Run the production coordinator only after reviewing the window, active/held
operations, destination policy, and change approval:

```bash
make recent-scan-batch BATCH_WORKERS=30 \
  TRACKER_LOOKBACK_DAYS=3 BATCH_DAYS_BACK=7
```

The coordinator refreshes the tracker once, records a workload snapshot, sends
the tracker summary, launches separate worker containers, performs the final
delivery pass, and sends the final analyst summary. Customer delivery uses the
normal stakeholder recipients.

For a controlled functional batch that overrides every report and summary
recipient with an approved email-enabled analyst:

```bash
make recent-scan-batch-assignee-test BATCH_WORKERS=30 \
  BATCH_DAYS_BACK=7 \
  TEST_RECIPIENTS="approved.analyst@example.gov"
```

Do not treat the recipient override as database isolation. This command still
uses the production database and production coordinator rules.

## Common operational Make commands

The following table is an index, not authorization to run a mutating command.

| Purpose | Command | State impact |
| --- | --- | --- |
| Menu | `make menu` | Depends on the selected menu action |
| Tracker preflight | `make recent-scan-batch-preflight` | Read-only database selection |
| Production batch | `make recent-scan-batch` | Qualys, database, S3, and SES writes |
| Controlled recipient batch | `make recent-scan-batch-assignee-test TEST_RECIPIENTS="..."` | Production workflow with recipient override |
| Refresh report tracker | `make update-tracker` | Qualys reads and tracker writes |
| Preview tracker rows | `make tracker-table DAYS_BACK=7` | Read-only |
| Preview manual queue | `make tracker-table REPORT_STATUS=manual DAYS_BACK=7` | Read-only |
| Review persisted report errors | `make report-errors DAYS_BACK=7` | Read-only |
| Export tracker CSV | `make tracker-csv` | Writes a local export |
| Import tracker workbook | `make tracker-import INPUT_XLSX="/path/file.xlsx"` | Database writes after confirmation |
| Export stakeholders | `make stakeholder-export` | Writes a local export |
| Import stakeholders | `make stakeholder-import INPUT_CSV="/path/file.csv"` | Database writes after confirmation |
| One eligible tracker report | `make single-report TAG="CUSTOMER_TAG"` | Qualys, database, S3, and SES writes |
| One manual tracker report | `make manual-report TAG="CUSTOMER_TAG"` | Qualys, database, S3, and SES writes |
| New on-demand report | `make on-demand-report TAG="CUSTOMER_TAG"` | Qualys, database, and S3 writes |
| Guarded manual recovery preview | `make recover-manual-reports MANUAL_TRACKER_IDS="123" RECOVERY_CAUSE="password-validation"` | Read-only preview |
| Test replay preview | `make test-report-replay DAYS_BACK=7 TEST_RECIPIENTS="..."` | Read-only preview |
| Targets Removed test preview | `make test-targets-removed TARGETS_REMOVED_TRACKER_IDS="123" TEST_RECIPIENTS="..."` | Read-only preview |
| Capacity isolation checks | `make capacity-start TEST_RECIPIENTS="..."` | Read-only checks |
| Capacity test | `make capacity-start APPLY=1 BATCH_WORKERS=30 TEST_RECIPIENTS="..."` | Test database, Qualys, capacity S3 prefix, and SES writes |

Commands with `APPLY=1`, `--confirm`, email delivery, tracker imports, or Qualys
deletion have additional safeguards documented in their focused runbooks. Do
not remove those safeguards from wrapper scripts.

The Targets Removed test requires explicit tracker IDs, an approved
email-enabled assignee recipient, and a stable replay UUID when `APPLY=1` is
used. It generates through the normal Qualys report path but never invokes
Qualys web-application deletion. It writes only isolated replay and analyst-run
records, and it does not change the source tracker row or customer delivery
history. Preview the IDs before applying and reuse the same replay UUID after an
interruption. The checked-out code requires the comprehensive schema's
`targets_removed` replay action and `template_override` column; apply the
approved additive database change before deployment.

Large Qualys XML reports are streamed to private temporary files and processed
without loading the complete document into memory. The checked-in `dev.env`
sets `WAS_QUALYS_REPORT_XML_MAX_BYTES` to 10 GiB and
`WAS_QUALYS_REPORT_XML_MIN_FREE_BYTES` to 5 GiB. Copy both settings to the
deployed `.env`, rebuild after code changes, and verify that the report
workspace can support the configured worker concurrency. A
`ReportXmlSizeLimitError` or `ReportXmlDiskSpaceError` requires review before
changing a limit or retrying the affected tracker row.

## Batch troubleshooting

Every coordinated production or capacity batch prints a batch UUID. Preserve
it with the operational record. Logs are separated by coordinator, tracker,
summary, delivery, and worker role under:

```text
local-output/logs/batches/<batch-uuid>/
```

Use the read-only diagnostic commands instead of manually concatenating worker
logs:

```bash
make logs-latest
make logs-summary LOG_BATCH_ID="<batch-uuid>"
make logs-errors LOG_BATCH_ID="<batch-uuid>"
make logs-tag LOG_BATCH_ID="<batch-uuid>" LOG_TAG="CUSTOMER_TAG"
```

Set `LOG_LIMIT=500` when more than the default 200 matching records are needed.
These commands read local structured logs only. They do not query Qualys or the
database, generate a report, or send email.

Use database-backed commands for persisted state:

```bash
make report-errors DAYS_BACK=7
make tracker-table REPORT_STATUS=manual DAYS_BACK=7
```

Do not retry held SES delivery or uncertain Qualys creation based only on an
error line. Reconcile the external outcome and persisted run first. Use the
[manual recovery runbook](manual-report-recovery.md) only for its supported,
explicitly reviewed failure categories.

## Capacity testing

Capacity testing requires the isolated capacity database, the seven
`TEST_WAS_DB_*` settings, approved test recipients, and a representative
baseline. It still uses real Qualys, S3, and SES services. Follow
[capacity testing](capacity-testing.md). Never point normal reporting commands
at the capacity database and never point the capacity launcher at production.

## Update and rebuild

Finish or reconcile active work before changing the checkout:

```bash
cd "$HOME/code/cd_WAS_update"
git branch --show-current
git status --short
git pull --ff-only origin cd_WAS_update
cd backend/was
make install
make test
make lint
make build
```

Do not use a destructive Git reset to resolve local changes. A Git pull does not
update an existing Docker image. Rebuild after application, template, resource,
dependency, Dockerfile, or worker-script changes. Start a new container to load
updated `.env` values.

After deployment, run the appropriate read-only preflight and one approved
controlled functional test. Record the commit SHA, image identity, batch or run
ID, destination, S3 reference, SES message ID, and result without recording
credentials or report passwords.

## Recovery and rollback

- Stop starting new work when a coordinator, database, Qualys, S3, or SES state
  is uncertain.
- Preserve batch IDs, run IDs, logs, workload manifests, and database evidence.
- Do not delete report runs or reset tracker state to force a retry.
- Held email means SES acceptance may have occurred. Verify before delivery.
- An uncertain Qualys create may have created a remote report. Reconcile by the
  stored stable report name and ID before generation.
- Application rollback means deploying a previously approved image after
  confirming its schema compatibility. Do not drop additive schema or delivery
  evidence merely to make an older image start.

## Documentation maintenance

Any change to command names, menu choices, required environment variables,
database requirements, external side effects, safeguards, output locations, or
recovery behavior must update this runbook and the focused runbook in the same
review. Examples and defaults must be verified against the Makefile and CLI
parser. Documentation must distinguish read-only previews from commands that
write to PostgreSQL, Qualys, S3, SES, or the local filesystem.
