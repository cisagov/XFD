# WAS capacity testing

## Goal and completion rule

Demonstrate 600 report outcomes within eight hours, including full tracker
refresh, generation, S3 storage, and persisted SES acceptance. Inbox delivery is
outside scope. Report PDFs and notification-only emails separately; a workload
with many notifications is not evidence of capacity for 600 generated PDFs.
Failed or uncertain deliveries do not count as complete. A projection from a
smaller test is an estimate, not a demonstrated eight-hour capacity result.

The SSN/credit-card finding queries are currently disabled. Record this limitation
in the capacity result and repeat the relevant measurements if they are enabled.

## Isolation prerequisites

An administrator must prepare these resources separately. The launcher does not
provision infrastructure, copy data, reset tables, or restore snapshots.

1. A dedicated database and login role whose names start with `was_capacity_`.
   Give that role privileges only in the test database, no production-table
   access, no superuser, database-creation, or role-creation privileges, and no
   membership allowing escalation to privileged roles. Names and runtime identity
   checks are safeguards, not proof of correct cross-database permissions.
2. A controlled baseline snapshot containing the representative stakeholder,
   schedule/history, special-case, and assignee data needed by the normal code.
   Customer contacts should be sanitized to test destinations. Protect stored PDF
   passwords and other copied data as sensitive. Keep the operational database
   untouched. Apply the comprehensive schema to a new empty database, or the
   appropriate local increments to an existing clone. Local migration
   `schema/updates/019_capacity_metrics.sql` adds the shared metrics fields.
3. Private, Git-ignored environment configuration. Keep the ordinary `WAS_DB_*`
   settings and the capacity-only `TEST_WAS_DB_*` settings together in `dev.env`,
   copied to `.env` on EC2. Only the capacity launcher selects the test settings;
   ordinary commands continue to use `WAS_DB_*`. Qualys and SES settings remain
   shared. Use the same EC2 size and relevant resource limits planned for
   production. The launcher enforces S3 storage under `capacity/<run-id>`.
4. An email-enabled test assignee, such as the approved Zachary address. All
   report and summary stages receive the explicit override. Do not use customer
   destinations. Agree on mailbox volume and service load before running.
5. An idle test window with no normal batch or other workload on the clone.
   Qualys and SES are real services: this is not a mock test. Confirm quotas and
   acceptable API load with the service owners before scaling up.

The clone must contain no active or pending/failed deliverable prior reports.
The operator prepares eligible work in the clone only. Restore the approved
baseline between comparison runs using the administrator's controlled process;
do not clear production tracker dates or report history. A fresh run UUID is not
a reset of the dataset. The live Qualys dataset can change between trials, so
compare the saved workload manifests as well as the baseline label.

Add all seven test database settings to the existing environment file, replacing
the placeholders privately. The test database and restricted role must already
exist; these settings do not create either resource:

```dotenv
TEST_WAS_DB_HOST=replace-me-rds-endpoint
TEST_WAS_DB_NAME=was_capacity_test
TEST_WAS_DB_USERNAME=was_capacity_test_user
TEST_WAS_DB_PASSWORD=replace-me
TEST_WAS_DB_PORT=5432
TEST_WAS_DB_SSLMODE=require
TEST_WAS_DB_CONNECT_TIMEOUT_SECONDS=10
```

The launcher requires every test setting and does not fall back to operational
database settings when one is missing. It selects the test settings before any
database access and passes that selection to its worker and summary subprocesses.
The selection is local to the capacity process and its children; it does not
rewrite `.env` or change later normal commands. Database name and role name must
still start with `was_capacity_`. Keep both sets of credentials out of Git and
logs. Shared credentials mean the trial still uses real Qualys and AWS resources.

## Commands

### Database-only refresh of the test baseline

`capacity-database-reset` dumps the `public` schema of `was` and restores it into
`was_capacity_test`. It includes the schema, sequences, and data, but not server
roles or other database schemas. It uses ordinary `WAS_DB_*` settings for the
read-only source and all seven `TEST_WAS_DB_*` settings for the destination.
Both database names are checked exactly. This command does not call Qualys,
generate reports, access S3, or send email.

Stop test workers before resetting. The reset is destructive to the existing
test database contents, so it is separate from `capacity-test` and requires
`APPLY=1`. Never point ordinary reporting commands at the test database during
the reset. A shared advisory lock prevents an applied capacity trial from
overlapping the restore transaction.

The destination login needs ownership privileges for the public schema and its
objects, and permission to create schemas in the test database. SELECT/INSERT/
UPDATE/DELETE grants alone are not sufficient for a full schema restore. Ask the
database administrator to arrange ownership only inside the isolated database.
Do not give the test login superuser, CREATEDB, CREATEROLE, or operational-table
privileges. The command checks prerequisites and does not grant itself access.
Source credentials must be able to dump every object in the public schema.
The rebuilt image includes PostgreSQL client tools. Their version must support
the source server, and the destination must support the dumped schema. A tool
version or schema-dependency failure stops the reset; do not bypass errors.

From `backend/was`, after rebuilding the image:

```bash
make capacity-database-reset
```

This performs read-only prerequisite checks. After reviewing those checks:

```bash
make capacity-database-reset APPLY=1
```

The applied command retains a private source archive and a pre-reset target
backup under `local-output/capacity-database-resets/<UUID>/`. It restores without
source ownership or grants. Restore and history cleanup share one transaction;
failure rolls back the database changes. The five emptied tables are
`was_test_replay_items`, `was_test_replay_batches`, `was_batch_report_attempts`,
`was_report_runs`, and `was_batch_runs`.

Stakeholders, assignees, tracker rows, scan facts, passwords, sent dates, and
manual flags come directly from the source and are not rewritten or sanitized.
Existing test-only assignee records are replaced by the source assignee data.
Confirm Craig's selected address exists with `email_enabled=true` after restore;
assignment to Zack does not itself determine the test delivery recipient.
Retained sent dates and legacy execution keys can exclude copied tracker rows
from report generation. Check eligibility before starting a trial rather than
assuming every copied row will run.

The archive and generated SQL contain sensitive operational data. They are
private local files, not encrypted backups. Keep them on approved encrypted
storage, out of Git, and under the applicable retention controls. Restoring a
database does not undo emails, Qualys operations, or S3 objects. To recover the
previous test state after a successful reset, have an administrator restore the
retained target backup only to `was_capacity_test`; do not restore it over `was`.
Each reset obtains a fresh source snapshot, so repeated resets may have different
workloads if the operational database has changed.

### Capacity trial

After building the updated image, from `backend/was`, run read-only isolation and
recipient checks first. Replace the example baseline label with the actual
snapshot identifier:

```bash
make capacity-start \
  CAPACITY_WORKLOAD_LABEL="approved-baseline-2026-09-24" \
  BATCH_WORKERS=30 \
  TEST_RECIPIENTS="craig.duhn@associates.cisa.dhs.gov"
```

Without `APPLY=1`, the command does not call Qualys, refresh tables, generate
reports, or send email. This checks isolation, not the post-refresh workload count.

The default expected count is now `auto`. A start refreshes the tracker, records
the actual eligible workload, and continues without stopping for a count change.
An explicit numeric `CAPACITY_EXPECTED_CANDIDATES` retains the optional strict
count check, for example when demonstrating exactly 600 outcomes. The saved
manifest limits generation and delivery retries to that workload. A new UUID is
generated and printed automatically unless one is supplied explicitly.

For a normal parallel trial, use the following command. Remove `APPLY=1` for a
read-only preview. All report and tracker/final summary emails use the explicit
recipient override, not customer POCs or the assignees on individual tracker rows.

```bash
make capacity-start APPLY=1 BATCH_WORKERS=30 \
  TEST_RECIPIENTS="craig.duhn@associates.cisa.dhs.gov"
```

Alternatively, start a new parallel trial with `make menu`, then choose
**Report Generation > 6**. Select the worker count (default 30, maximum 30),
enter the approved test recipients and workload label, and confirm the live
test. The menu launches the same coordinator in a separate process, preserving
test database isolation without changing the menu's database environment.
This option starts a new trial only; it does not restore or reset the clone.
Use the commands below for continuation or an explicit start-over.

To continue the latest saved workload:

```bash
make capacity-continue APPLY=1 BATCH_WORKERS=30 \
  TEST_RECIPIENTS="craig.duhn@associates.cisa.dhs.gov"
```

Optionally supply `CAPACITY_CONTINUE_RUN_ID=<previous-run-UUID>` to choose a
specific workload. Continuation creates a new attempt UUID and summary, preserves
earlier evidence, and does not refresh or broaden the original workload. It skips
accepted emails, reuses completed reports awaiting safe delivery, and retries
safe failed generation. Held/sending deliveries, active generation, and uncertain
Qualys creation outcomes are not blindly retried. Reconcile unsafe states before
continuing; they are not a reason to remove duplicate-delivery protections.
The saved manifest and matching batch record must still exist. After a database
reset, old disk manifests cannot be used to resume deleted batch records.
If a run failed before saving a manifest, use a new start rather than continuation.

Continuation summaries explicitly include prior completions and do not present
them as fresh throughput. A recovered workload can finish successfully, but a
continuation is not a new 600-in-eight-hours benchmark. Normal start runs retain
the complete refresh-to-SES measurement. Zero candidates means no report work,
not a passed capacity benchmark.

To discard the current test state and run a fresh trial in one explicit command:

```bash
make capacity-start-over APPLY=1 BATCH_WORKERS=30 \
  TEST_RECIPIENTS="craig.duhn@associates.cisa.dhs.gov"
```

This backs up and replaces the test database using `capacity-database-reset`,
then starts a new trial only if reset succeeded. It is destructive to test state
and sends real test emails. It does not undo previous SES or Qualys operations.
Without `APPLY=1`, start-over performs reset prerequisite checks and prints the
plan without restoring or starting a workload. The reset preserves source sent
dates and copies source assignees, so verify the chosen recipient is present in
the source data. Do not run normal batches or manual edits against the clone
while any capacity operation is active.

Use a representative mix of target sizes. Start with a small expected cohort and
one worker, then compare 5, 10, 20, and 30 workers on matching approved baselines.
Increasing workers can increase throttling rather than throughput. Do not start
with 600 reports just to validate the launcher.

## Evidence and production summaries

Trial output is under `local-output/capacity/<run-id>` by default, including the
workload manifest, `result.json`, and process-local JSONL metric files.
`capacity_pass` requires the exact selected tracker IDs, all expected artifacts,
and all expected persisted deliveries within the time budget. Worker exit codes,
clean-workflow status, and final-summary success are reported separately. Recovered
errors do not erase completed deliveries; a failed administrative summary does
not change a successful capacity result, but still causes a nonzero command exit.
The capacity clock stops after report delivery, before the final analyst summary.
Refresh and the pre-generation summary are included. The default work budget is
28,800 seconds; the Python CLI exposes `--max-seconds` for a shorter diagnostic
trial. Cleanup and the final summary may take additional time after a timeout.
Preserve the run ID,
baseline identifier, Git/image version, EC2 size, workload composition, and service
limits with the result. There is no automatic deletion of the evidence or S3
artifacts; arrange retention separately.

The shared summary records worker count, run mode, a fixed finish time, outcome,
PDF and notification counts, batch-specific accepted sends, PDF generation
average/median/p95, delivery timing, and accepted deliveries per hour. Production
batches use the same summary metrics after their database schema is updated.
Timing percentiles include positive-duration failed PDF generation attempts and
exclude fast notification preparation. Repeated measurements retain the longest
per-report duration; JSONL events provide individual observations. Summed worker
durations are not wall-clock elapsed time. Historical batches without captured
timestamps are not valid capacity benchmarks.

Endpoint events record individual Qualys attempt latency, attempt number, outcome
class, and HTTP status when available, without request payloads or credentials.
Resource samples describe the launcher container's cgroup-v2 CPU total and memory,
including its worker subprocesses, plus shared output-filesystem space. They are
not host-wide EC2 metrics. Unsupported measurements are null, not zero. Optional
telemetry write failures are logged and mean the diagnostic evidence is incomplete.
Use host monitoring separately if the capacity plan requires host-wide contention
or metrics unavailable in the container.

The production Make workflow uses multiple containers; the capacity launcher uses
multiple processes in one container. Keep resource limits comparable and disclose
this topology difference. Confirm final production throughput with operational
summaries; small daily batches do not establish maximum sustained capacity.
