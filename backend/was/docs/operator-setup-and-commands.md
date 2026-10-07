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
- Git, GNU Make, Python 3.12 or a compatible project-approved version, Docker,
  and `tmux`;
- network access to the configured PostgreSQL and Qualys endpoints;
- an EC2 instance role with the approved S3 access and permission to assume
  `WAS_SES_ROLE_ARN`;
- enough private disk space for the image, temporary workspaces, retained logs,
  capacity evidence, and approved database-reset backups;
- the database schema required by the checked-out code.

Do not put passwords, tokens, reports, database dumps, or `.env` in Git. Do not
enable shell tracing while handling credentials.

### Infrastructure and host rebuild boundary

The repository Terraform creates the WAS EC2 instance, instance profile, SSM
core attachment, exact SES assume-role permission, and object
permissions for `was_reports/*` and `capacity/*` in an existing bucket. It does
not create the database, report bucket, SES sending role or trust policy,
secrets, repository checkout, application image, cleanup timer, central log
forwarding, or `tmux`. Treat each missing prerequisite as a deployment blocker
until an approved separately managed control is verified. The runtime role does
not receive `s3:DeleteObject`; optional KMS permissions are limited to the exact
configured key.
Because the bucket is external to this Terraform, separately verify its public
access block, encryption, transport policy, ownership controls, approved
versioning, lifecycle, retention, and logging configuration before live use.
The runtime defaults to `WAS_REPORTS_S3_ENCRYPTION=bucket-default`, which does
not override the bucket's approved default. Select `AES256` only for an approved
SSE-S3 policy. Select `aws:kms` only when `WAS_REPORTS_KMS_KEY_ID` and the
Terraform `was_reporting_reports_kms_key_arn` identify the same exact key and
the bucket policy accepts that key.

Terraform first boot runs the dedicated
`infrastructure/was-reporting-bootstrap.sh`. It installs only the prerequisites
needed to clone the approved repository and run Make. It deliberately does not
reuse the OpenCTI dependency installer and does not install Docker, AWS CLI,
`uv`, or application dependencies. Those are installed from the reviewed WAS
host manifest after checkout.

The Terraform WAS reporting host currently targets Canonical Ubuntu 24.04 LTS
x86-64 in `us-east-1`. AMI IDs are Region-specific; before approving a
replacement, verify that `var.was_reporting_ami_id` resolves to an available
Ubuntu 24.04 x86-64 image owned by Canonical (`099720109477`) and review the
exact Terraform plan.

The tracked `scripts/capture_host_packages.py` script records a private host
software inventory. Run a fresh inventory on the current host and move the
result to approved off-host storage before replacement. The tracked
`scripts/rebuild_was_host_ubuntu24.py` helper is tailored to the recorded
September 4, 2026 host inventory and restores the reviewed software on Ubuntu
24.04 x86-64. It previews by default, requires
`--apply --acknowledge-manual-items` for writes, uses Docker's signed Noble
repository, and reads the reviewed `host-software-manifest.json` source of
truth. It installs the checksum-pinned AWS CLI v2 release and grants the
invoking operator root-equivalent Docker group access. A successful `--verify`
confirms the exact AWS CLI version and normal-operator Docker daemon access in
addition to the other declared software, then returns exit code `0`; manual
rebuild items remain a separate deployment gate. Run its tests and complete a
disposable-host bootstrap verification before production cutover. See the
[repeatable host rebuild cycle](host-rebuild-cycle.md) for the complete
capture, review, rebuild, validation, and rollback sequence.

The inventory is evidence, not a complete backup or production bootstrap. It
does not restore secrets, IAM, data, custom script contents, cron or service
definitions, the checkout, the application image, or operator configuration.
Preserve and restore those items through approved mechanisms, retain inventory
and validation evidence privately, and complete this runbook's prerequisites
before decommissioning the existing host.

## First checkout

From the EC2 user's home directory:

```bash
mkdir -p "$HOME/code"
cd "$HOME/code"
git clone --branch develop --single-branch \
  git@github.com:cisagov/XFD.git was_reporting
cd was_reporting
cd backend/was
make host-software-preview
make host-software-apply APPLY=1
```

If apply added Docker group membership, end the login session and reconnect.
Then continue from the repository root:

```bash
cd "$HOME/code/was_reporting"
cd backend/was
make host-software-verify
cd ../..
"$HOME/.local/bin/uv" venv \
  --python 3.12.14 \
  --seed \
  was_reporting
cd backend/was
../../was_reporting/bin/python --version
../../was_reporting/bin/python -m pip --version
make install
make host-shell-preview
make host-shell-install APPLY=1
./scripts/create-local-env.sh
chmod 600 .env
```

The rebuild helper installs checksum-verified `uv`, installs its managed Python
3.12.14, and verifies that managed interpreter before this step. The `uv venv`
command above creates the named `was_reporting` environment expected by the
Makefile and seeds it with `pip` so `make install` can install the project
requirements.

`host-shell-install` validates the tracked
`config/was-operator-shell.sh`, creates a private timestamped backup under
`~/.local/state/was-host-rebuild/bashrc-backups`, and appends exactly one
managed loader at the end of `~/.bashrc`. It refuses partial or duplicate
managed state. Open a new login shell after installation to load the aliases,
prompt, PATH, and named environment activation. The tracked fragment contains
no secrets and never reads `.env`.

If the host uses an approved pre-existing Python environment, pass its Python
path to Make instead of creating the expected local environment:

```bash
make install PYTHON="/absolute/path/to/python"
```

`make install` must complete before using host-side batch, capacity, or
structured-log commands. If Python reports that `pip` is unavailable, repair
or recreate the environment before continuing. Do not bypass dependency
installation by invoking internal modules from an incomplete environment.

Populate `.env` from the approved secret source. `dev.env` documents names and
safe defaults only. Replace every placeholder and keep the file private. See
the [main README environment section](../README.md#local-environment-file) for
the current variable inventory.

Before every live use, verify the EC2 file is owned by the operator and has mode
`0600`:

```bash
stat -c '%U %G %a %n' .env
```

Stop if the output is not the expected operator identity and permission mode.
Do not print the file contents while troubleshooting permissions.

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
command -v tmux
tmux -V
make help
make report-help
make mailer-help
```

A successful build proves only that the image was created. It does not verify
database identity, Qualys retrieval, S3 archival, SES acceptance, PDF content,
or inbox delivery. Use the
[live validation runbook](live_qualys_equivalence_runbook.md) for controlled
end-to-end evidence.

The current `Dockerfile` pins its Python base by version and digest, pins runtime
Python dependencies, and declares the unprivileged `was-reporting` user.
Supported Make targets that write mounted host output continue to use the
operator's UID and GID. Review, scan, test, and explicitly commit every base or
dependency update.

The default `WAS_DB_SSLMODE=require` encrypts PostgreSQL traffic but does not
verify the database server certificate or hostname. Use an approved CA and
`verify-full` when available, and verify that choice against the deployed RDS
configuration before claiming server-identity-verified TLS.

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

Before starting a production or capacity coordinator, verify that the host has
no unreviewed WAS work still running or retained:

```bash
make recent-scan-batch-status
make capacity-status
docker ps --format '{{.ID}}\t{{.Image}}\t{{.Names}}\t{{.Status}}'
```

`No matching tmux sessions were found.` is the clean tmux result for that
workflow. A dead retained pane is evidence to review and archive through the
cleanup workflow below. A live pane or WAS worker container must be understood
before another coordinator is started. These host checks do not inspect
PostgreSQL claims or prove that Qualys, S3, or SES state is settled. The
coordinator performs its own database and configuration validation after the
tmux submission.

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

`BATCH_DAYS_BACK` must be `all` or an integer of at least `1`. A value of `1`
means today only, `2` means today and yesterday, and `7` means today plus the
previous six calendar days. `0` is invalid.

This command assigns the batch ID before launch and starts the coordinator in a
detached `tmux` session. The command prints the batch ID, exact session name,
manifest path, and status, console, attach, graceful-stop, and structured-log
commands. Returning successfully means that `tmux` accepted the workload. It
does not mean preflight or the batch succeeded. Check the retained session:

```bash
make recent-scan-batch-status TMUX_SESSION="was-production-<batch-UUID>"
make recent-scan-batch-console TMUX_SESSION="was-production-<batch-UUID>"
make recent-scan-batch-attach TMUX_SESSION="was-production-<batch-UUID>"
make logs-summary LOG_BATCH_ID="<batch-UUID>"
```

Configuration, database-identity, coordinator-lock, active-operation, worker
backend, or required-environment validation can fail before the coordinator
creates a batch record or reaches preflight. In that case there is no tracker
summary or final summary to receive. Use the retained console as the primary
evidence, correct the prerequisite, and do not infer success or email delivery
from the absence of summaries.

Detaching from an attached session with `Ctrl-b d` leaves the batch running.
To request a deliberate stop, use the exact printed session name:

```bash
make recent-scan-batch-stop TMUX_SESSION="was-production-<batch-UUID>"
```

Stop sends `Ctrl-c` to the foreground coordinator so its cleanup can run. It
does not kill the session or declare cleanup complete. Check status and console
output afterward. Production does not provide a continuation command. Reconcile
held customer delivery only through the guarded command after external
verification. Preserve and escalate other uncertain Qualys, S3, analyst,
standalone, or active database state before any replacement work.

The coordinator refreshes the tracker once, records a workload snapshot, sends
the tracker summary, launches separate worker containers, performs the final
delivery pass, and sends the final analyst summary. Customer delivery uses the
normal stakeholder recipients. This true customer production path explicitly
enables the guarded Qualys deletion flow for eligible non-FCEB web applications
that were inaccessible in two consecutive scans. Before deletion, the tracker
commits a `MANUAL QUALYS DELETION PENDING` claim. An interrupted or failed
deletion stays manual and is not automatically replayed.

There is currently no supported command that reconciles a
`MANUAL QUALYS DELETION PENDING` or `MANUAL QUALYS DELETION FAILED` tracker row.
Because deletion is performed one URL at a time, a failure can leave a partial
external outcome. Stop automated retries, preserve the batch ID, tracker row,
complete removed-target URL list, console, and structured logs, and escalate to
the WAS and Qualys service owners. They must verify each URL's current Qualys
state before an approved manual tracker correction is designed. Do not rerun the
destructive refresh, use the generic tracker editor, or change the row directly
to `Targets Removed`; those actions cannot prove which deletions completed.

Both analyst notifications use semantic HTML tables with a matching plain-text
table fallback. Time measurements use two decimal places, and final elapsed real
time uses `h:mm:ss.ss`. Each notification includes pending manual-report counts
for analysts who have at least one pending item, plus `Unassigned` when needed.
Detailed tags, tracker IDs, scan names, and notes remain in the final CSV.

For a controlled functional batch that overrides every report and summary
recipient with an approved email-enabled analyst:

```bash
make recent-scan-batch-assignee-test BATCH_WORKERS=30 \
  BATCH_DAYS_BACK=7 \
  TEST_RECIPIENTS="approved.analyst@example.gov"
```

Do not treat the recipient override as database isolation. This command still
uses the production database and production coordinator rules. However, the
recipient override keeps the tracker refresh non-destructive. It does not delete
Qualys web applications, and any eligible removal remains manual. Capacity and
other test workflows are also non-destructive.

## Retained tmux session cleanup

Completed batch panes remain available for diagnosis until a guarded cleanup
removes them. Always preview cleanup first:

```bash
make recent-scan-batch-cleanup
make capacity-cleanup
```

Each command is scoped to its own WAS workflow and ignores running panes. The
first applied cleanup archives a dead pane and records when cleanup first
observed it. A later applied cleanup can remove a successful pane only after
that observation is at least 24 hours old by default. Override that threshold
only for an intentional, reviewed cleanup:

```bash
make recent-scan-batch-cleanup TMUX_CLEANUP_RETENTION_HOURS=48
```

After reviewing the dry-run output, apply cleanup for eligible successful
sessions:

```bash
make recent-scan-batch-cleanup TMUX_CLEANUP_APPLY=1
make capacity-cleanup TMUX_CLEANUP_APPLY=1
```

Failed dead sessions are retained unless the operator explicitly acknowledges
their removal. Record and investigate the failure, then repeat the dry run with
the acknowledgement before applying it:

```bash
make recent-scan-batch-cleanup \
  TMUX_SESSION="was-production-<batch-UUID>" \
  TMUX_CLEANUP_ACKNOWLEDGE_FAILURES=1
make recent-scan-batch-cleanup \
  TMUX_SESSION="was-production-<batch-UUID>" \
  TMUX_CLEANUP_APPLY=1 TMUX_CLEANUP_ACKNOWLEDGE_FAILURES=1
```

Failure acknowledgement applies only to the exact validated session named by
`TMUX_SESSION`; it never approves every failed session in a workflow. Use
`capacity-cleanup` and an exact `was-capacity-<batch-UUID>` session instead when
reviewing capacity sessions. Before an exact session is removed, cleanup
archives its retained console and metadata under:

```text
local-output/tmux-archives/<session>/console.log
local-output/tmux-archives/<session>/metadata.json
```

Archive directories are created with mode `0700`, and archive files use mode
`0600`. Console output can contain operational recipient information, so handle
these archives under the same access and retention controls as batch logs.
Confirm that both archive files exist after applied cleanup. Removing a tmux
session does not stop or reconcile worker containers, settle Qualys activity,
confirm email delivery, or repair database state. Complete those checks through
their dedicated operational and recovery workflows.

The repository includes an hourly systemd timer that applies this two-pass
cleanup to both production and capacity sessions. The timer never acknowledges
failed sessions. After deploying the same reviewed revision to the EC2 host,
install and verify it with:

The checked-in unit is intentionally bound to user `ubuntu` and the exact
checkout `/home/ubuntu/code/was_reporting/backend/was`. The commands below are
valid only for that layout. If the approved host uses a different user, checkout,
Python environment, tmux socket owner, or output directory, do not install the
unit unchanged. Have the service definition reviewed with every absolute path,
`User`, `Group`, and `ReadWritePaths` value updated for that host first.

```bash
cd "$HOME/code/was_reporting/backend/was"
sudo install -m 0644 systemd/was-tmux-cleanup.service \
  /etc/systemd/system/was-tmux-cleanup.service
sudo install -m 0644 systemd/was-tmux-cleanup.timer \
  /etc/systemd/system/was-tmux-cleanup.timer
sudo systemctl daemon-reload
sudo systemctl start was-tmux-cleanup.service
systemctl status was-tmux-cleanup.service --no-pager
journalctl -u was-tmux-cleanup.service -n 100 --no-pager
sudo systemctl enable --now was-tmux-cleanup.timer
systemctl status was-tmux-cleanup.timer --no-pager
systemctl list-timers was-tmux-cleanup.timer --no-pager
```

The initial service run must show that it inspected both production and
capacity workflows. A nonzero service result caused by an unacknowledged failed
session is an intentional alert: review that exact session and its archive
before using the acknowledgement workflow. Permission, tmux socket, archive,
or malformed-state errors are operational failures and must be corrected before
the timer is considered verified.

Disable the automation without deleting its evidence archives with:

```bash
sudo systemctl disable --now was-tmux-cleanup.timer
```

## Common operational Make commands

The following table is an index, not authorization to run a mutating command.

| Purpose | Command | State impact |
| --- | --- | --- |
| Menu | `make menu` | Depends on the selected menu action |
| Tracker preflight | `make recent-scan-batch-preflight` | Read-only database selection |
| Production batch | `make recent-scan-batch` | Guarded eligible Qualys web-application deletion, database, S3, and SES writes |
| Production batch status | `make recent-scan-batch-status TMUX_SESSION="..."` | Read-only tmux state |
| Production batch console | `make recent-scan-batch-console TMUX_SESSION="..."` | Read-only retained output |
| Graceful production stop | `make recent-scan-batch-stop TMUX_SESSION="..."` | Interrupts the selected coordinator and starts cleanup |
| Preview production tmux cleanup | `make recent-scan-batch-cleanup` | Read-only eligible-session review |
| Apply production tmux cleanup | `make recent-scan-batch-cleanup TMUX_CLEANUP_APPLY=1` | Archives and removes eligible successful sessions |
| Controlled recipient batch | `make recent-scan-batch-assignee-test TEST_RECIPIENTS="..."` | Production database, S3, and SES writes with recipient override; no Qualys web-application deletion |
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
| Capacity test | `make capacity-start APPLY=1 BATCH_WORKERS=30 TEST_RECIPIENTS="..."` | Test database, non-destructive Qualys access, capacity S3 prefix, and SES writes |
| Preview capacity tmux cleanup | `make capacity-cleanup` | Read-only eligible-session review |
| Apply capacity tmux cleanup | `make capacity-cleanup TMUX_CLEANUP_APPLY=1` | Archives and removes eligible successful sessions |

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
The secure streaming parser rejects an actual document DTD. Declaration-like
text inside comments or CDATA is inert and is not classified as a DTD.

Detail PDFs are also streamed to private partial files. Set
`WAS_QUALYS_DETAIL_PDF_MAX_BYTES` and
`WAS_QUALYS_DETAIL_PDF_MIN_FREE_BYTES` to the approved limits, normally the
same 10 GiB and 5 GiB defaults as XML. A PDF is published only after its header
and end marker pass validation; failures preserve any existing final file and
remove the partial download.

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

For a held **customer** SES delivery, use `make reconcile-email-delivery
REPORT_RUN_ID=<id>` to inspect the linked run and tracker. The guarded command
supports only two applied outcomes for `delivery_purpose=customer`:

- `confirm-delivered` records externally verified delivery without calling SES.
- `retry-confirmed-undelivered` records externally verified non-delivery and
  makes one atomically claimed retry. Test recipients are required unless the
  operator explicitly selects stored customer recipients and supplies the
  stronger customer-send confirmation.

The ordinary batch and direct customer mailer cannot claim uncertain held
deliveries. Each confirmed non-delivery creates a one-time retry authorization
bound to the selected recipient scope. The atomic claim consumes it and
rechecks that the linked tracker is still unsent. A repeated uncertain outcome
returns to held and requires new external evidence and confirmation.

An SES response-parsing failure after the delivery request starts is a held,
uncertain outcome even when no message ID was returned. Confirm the SES outcome
before changing that report run or attempting another delivery. A failure that
occurs before the SES request starts remains retryable for an ordinary, unheld
customer delivery. Initial held analyst delivery is allowed only when no prior
email error exists.

The reconciliation command does not support `delivery_purpose=analyst` or
`delivery_purpose=standalone`. If either delivery becomes held after an attempt,
stop. Preserve the run ID and external SES or mailbox evidence, do not rerun
generation or edit database status, and escalate for an approved recovery. The
direct mailer cannot reclaim a held analyst run with a previous email error or a
held standalone run.

## Capacity testing

Capacity testing requires the isolated capacity database, the seven
`TEST_WAS_DB_*` settings, approved test recipients, and a representative
baseline. It still uses real Qualys, S3, and SES services. Follow
[capacity testing](capacity-testing.md). Never point normal reporting commands
at the capacity database and never point the capacity launcher at production.

## Update and rebuild

Finish active work before changing the checkout. Complete supported held
customer-delivery reconciliation first, and preserve and escalate any other
uncertain state rather than updating code beneath it:

```bash
cd "$HOME/code/was_reporting"
git branch --show-current
git status --short
git pull --ff-only origin develop
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
  stored stable report name and ID before generation. No general operator command
  resolves an uncertain creation outcome; preserve the run and Qualys evidence
  and escalate rather than starting replacement generation.
- There is no production continuation command. If interruption leaves `running`
  generation or `sending` delivery state, preserve the session and database
  evidence and stop new production starts. The coordinator rejects active or
  uncertain operations, and its automatic stale-state handling is not a blanket
  authorization to retry external side effects.
- Customer held email can use the guarded reconciliation command after external
  verification. Analyst and standalone held delivery, uncertain S3 completion,
  and pending or failed Qualys web-application deletion currently require
  escalation because no supported operator reconciliation command exists.
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
