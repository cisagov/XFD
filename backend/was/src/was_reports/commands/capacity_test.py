"""Run an explicitly applied capacity trial against a dedicated database clone."""

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import signal
import subprocess  # nosec B404
import sys
from time import monotonic
from uuid import UUID, uuid4

from was_mailer.message import approved_analyst_recipients
from was_reports.data.daily_report_tracker import list_ready_report_candidates_from_db
from was_reports.utils.database import connect
from was_reports.utils.env import load_env_file, require_env


@contextmanager
def capacity_database_environment():
    """Route this trial and its children to explicit test settings only."""
    suffixes = ("HOST", "NAME", "USERNAME", "PASSWORD", "PORT", "SSLMODE",
                "CONNECT_TIMEOUT_SECONDS")
    settings = {}
    for suffix in suffixes:
        source = "TEST_WAS_DB_" + suffix
        value = os.environ.get(source)
        if not value or not value.strip():
            raise RuntimeError("Missing required environment variable: {}".format(source))
        settings["WAS_DB_" + suffix] = value
    previous = {name: os.environ.get(name) for name in settings}
    os.environ.update(settings)
    try:
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def expected_candidates(value):
    """Parse automatic workload sizing or an optional strict positive count."""
    if value.strip().lower() == "auto":
        return None
    try:
        count = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("Use auto or a positive candidate count.") from error
    if count <= 0:
        raise argparse.ArgumentTypeError("Candidate count must be positive.")
    return count


def parse_args(argv=None):
    """Require an explicit trial identity, workload, and approved recipients."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", type=UUID)
    parser.add_argument("--workload-label", default="capacity-current-workload")
    parser.add_argument("--test-recipients", required=True)
    parser.add_argument("--workers", type=int, default=30)
    parser.add_argument("--expected-candidates", type=expected_candidates, default=None)
    continuation = parser.add_mutually_exclusive_group()
    continuation.add_argument("--continue-latest", action="store_true")
    continuation.add_argument("--continue-run", type=UUID)
    parser.add_argument("--days-back", type=int, default=7)
    parser.add_argument("--lookback-days", type=int, default=3)
    parser.add_argument("--max-seconds", type=int, default=28800)
    parser.add_argument("--apply", action="store_true")
    arguments = parser.parse_args(argv)
    if not 1 <= arguments.workers <= 30:
        parser.error("--workers must be from 1 through 30.")
    if min(arguments.days_back, arguments.lookback_days, arguments.max_seconds) <= 0:
        parser.error("Candidate count and lookback windows must be positive.")
    if arguments.max_seconds > 28800:
        parser.error("--max-seconds cannot exceed the eight-hour capacity target.")
    if not arguments.workload_label.strip():
        parser.error("--workload-label must identify the clone baseline.")
    if len(arguments.workload_label) > 200:
        parser.error("--workload-label cannot exceed 200 characters.")
    arguments.run_id = str(arguments.run_id or uuid4())
    arguments.continue_run = str(arguments.continue_run) if arguments.continue_run else None
    arguments.continuation_manifest = None
    return arguments


def load_continuation(cursor, arguments, root=Path("/output/capacity")):
    """Select a database-backed prior trial and validate its immutable workload."""
    if arguments.continue_latest:
        cursor.execute("SELECT batch_id FROM was_batch_runs WHERE run_mode='capacity' "
                       "ORDER BY started_at DESC, batch_id DESC LIMIT 1")
    else:
        cursor.execute("SELECT batch_id FROM was_batch_runs WHERE run_mode='capacity' "
                       "AND batch_id=%s", (arguments.continue_run,))
    row = cursor.fetchone()
    if not row:
        raise ValueError("No matching capacity batch exists in this clone; start a new trial.")
    parent_run_id = str(UUID(str(row[0])))
    if parent_run_id == arguments.run_id:
        raise ValueError("Continuation requires a new run ID, separate from its parent.")
    manifest_path = root / parent_run_id / "workload.json"
    if not manifest_path.is_file():
        raise ValueError("Prior trial has no workload manifest, possibly stopped before refresh; "
                         "start a new trial after reconciling the clone.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    identifiers = manifest.get("candidate_ids")
    candidates = manifest.get("candidates")
    if (manifest.get("run_id") != parent_run_id or not isinstance(identifiers, list)
            or not isinstance(candidates, list)
            or any(type(identifier) is not int or identifier <= 0 for identifier in identifiers)
            or len(set(identifiers)) != len(identifiers)
            or any(not isinstance(candidate, dict) for candidate in candidates)
            or [candidate.get("tracker_id") for candidate in candidates] != identifiers
            or manifest.get("candidate_count") != len(identifiers)):
        raise ValueError("Prior workload manifest identity or candidate IDs are invalid.")
    cursor.execute("SELECT id, tag FROM was_daily_report_tracker WHERE id=ANY(%s)",
                   (identifiers,))
    current = dict(cursor.fetchall())
    if current != {candidate["tracker_id"]: candidate.get("tag") for candidate in candidates}:
        raise ValueError("Prior workload does not match this clone, possibly after a reset; "
                         "start a new trial.")
    root_run_id = str(UUID(str(manifest.get("root_run_id", parent_run_id))))
    arguments.continue_run = parent_run_id
    arguments.continuation_manifest = dict(manifest, parent_run_id=parent_run_id,
                                           root_run_id=root_run_id)
    return identifiers


def guard_database(arguments):
    """Verify live isolation and retain a clone-wide lock for applied trials."""
    expected_database = require_env("WAS_DB_NAME")
    expected_user = require_env("WAS_DB_USERNAME")
    if not all(value.startswith("was_capacity_") for value in
               (expected_database, expected_user)):
        raise ValueError("Dedicated database and role must start with was_capacity_.")
    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT current_database(), current_user, rolsuper, "
                "rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname=current_user"
            )
            database, username, superuser, createdb, createrole = cursor.fetchone()
            if (database, username) != (expected_database, expected_user) or any(
                (superuser, createdb, createrole)
            ):
                raise ValueError("Live database identity or role privileges are unsafe.")
            if arguments.apply:
                cursor.execute(
                    "SELECT pg_try_advisory_lock(hashtext(current_database()), "
                    "hashtext('was_capacity_trial'))"
                )
                if not cursor.fetchone()[0]:
                    raise ValueError("Another capacity trial holds this clone.")
            cursor.execute("SELECT EXISTS(SELECT 1 FROM was_batch_runs WHERE batch_id=%s)",
                           (arguments.run_id,))
            if cursor.fetchone()[0]:
                raise ValueError("Run ID already exists; restore the baseline for a new trial.")
            continuing = arguments.continue_latest or arguments.continue_run is not None
            allowed_ids = load_continuation(cursor, arguments) if continuing else []
            cursor.execute(
                "SELECT EXISTS(SELECT 1 FROM was_report_runs WHERE status='running' "
                "OR email_status='sending' OR (status='completed' "
                "AND COALESCE(email_status,'pending') IN ('pending','failed') "
                "AND NOT (COALESCE(source_tracker_id,0)=ANY(%s))))", (allowed_ids,)
            )
            if cursor.fetchone()[0]:
                raise ValueError("Clone contains active or deliverable prior reports.")
        connection.rollback()
        return connection
    except BaseException:
        connection.close()
        raise


def command(module, *arguments):
    """Build a subprocess command without shell expansion."""
    return [sys.executable, "-m", module, *arguments]


def trial_counts(run_id):
    """Count only current-trial generated artifacts and durable deliveries."""
    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*), COUNT(*) FILTER (WHERE attempts.generated "
                "AND runs.artifact_type='pdf'), COUNT(*) FILTER (WHERE attempts.generated "
                "AND runs.artifact_type='notification'), COUNT(*) FILTER (WHERE "
                "runs.email_status='sent' AND runs.emailed_at >= batch.started_at), "
                "ARRAY_AGG(attempts.tracker_id), COUNT(*) FILTER "
                "(WHERE runs.status='failed' OR runs.email_status='failed'), "
                "COUNT(*) FILTER (WHERE runs.email_status='held' OR "
                "(runs.status='failed' AND (STRPOS(COALESCE(runs.error_message,''), "
                "'QualysReportCreationUncertainError') > 0 OR STRPOS(COALESCE(runs.error_message,''), "
                "'creation outcome is uncertain') > 0))) "
                "FROM was_batch_report_attempts attempts "
                "JOIN was_batch_runs batch ON batch.batch_id=attempts.batch_id "
                "LEFT JOIN was_report_runs runs ON runs.id=attempts.report_run_id "
                "WHERE attempts.batch_id=%s", (run_id,)
            )
            return dict(zip(("attempted", "pdfs_generated", "notifications_generated",
                             "sent", "tracker_ids", "failed", "blocked"), cursor.fetchone()))
    finally:
        connection.close()


def continuation_status(identifiers, batch_id):
    """Measure the saved workload and seed this continuation's own summary rows."""
    from was_reports.reporting import analyst_summaries

    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT tracker.id, runs.id, runs.status, runs.email_status, "
                "runs.artifact_type, runs.emailed_at, runs.error_message FROM was_daily_report_tracker tracker "
                "LEFT JOIN LATERAL (SELECT id,status,email_status,artifact_type,emailed_at,error_message "
                "FROM was_report_runs WHERE source_tracker_id=tracker.id "
                "AND delivery_purpose='customer' ORDER BY id DESC LIMIT 1) runs ON TRUE "
                "WHERE tracker.id=ANY(%s)", (identifiers,)
            )
            rows = cursor.fetchall()
    finally:
        connection.close()
    if {row[0] for row in rows} != set(identifiers):
        raise ValueError("Continuation workload changed during execution.")
    result = {"attempted": len(rows), "pdfs_generated": 0, "notifications_generated": 0,
              "sent": 0, "blocked": 0, "failed": 0, "tracker_ids": identifiers}
    for tracker_id, report_run_id, status, email_status, artifact_type, emailed_at, error_message in rows:
        generated = status == "completed" and artifact_type in {"pdf", "notification"}
        sent = email_status == "sent" and emailed_at is not None
        uncertain = any(marker in (error_message or "") for marker in
                        ("QualysReportCreationUncertainError", "creation outcome is uncertain"))
        retry_safe = status == "failed" and not emailed_at and (
            email_status or "pending") in {"pending", "failed"} and not uncertain
        blocked = (status == "failed" and not retry_safe) or email_status == "held"
        if generated:
            result["pdfs_generated" if artifact_type == "pdf" else "notifications_generated"] += 1
        result["sent"] += int(sent)
        result["blocked"] += int(blocked)
        result["failed"] += int(status == "failed" or email_status == "failed")
        analyst_summaries.record_report_attempt(
            batch_id, tracker_id, 0, generated=generated, sent=sent,
            report_run_id=report_run_id, artifact_type=artifact_type,
            error="NeedsReconciliation" if blocked else None,
        )
    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE was_batch_report_attempts attempts SET sent_recorded_at=runs.emailed_at "
                "FROM was_report_runs runs WHERE attempts.batch_id=%s "
                "AND attempts.report_run_id=runs.id AND attempts.sent "
                "AND runs.email_status='sent' AND runs.emailed_at IS NOT NULL", (batch_id,)
            )
        connection.commit()
    finally:
        connection.close()
    result["remaining"] = len(rows) - result["sent"]
    return result


def stop_process(process):
    """Stop an isolated subprocess group, tolerating concurrent process exit."""
    for signal_number, timeout in ((signal.SIGTERM, 30), (signal.SIGKILL, 5)):
        try:
            os.killpg(process.pid, signal_number)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=timeout)
            return
        except subprocess.TimeoutExpired:
            continue


def run_phase(arguments, *, check, timeout):
    """Bound a phase and stop its descendants on cancellation or timeout."""
    process = subprocess.Popen(arguments, start_new_session=True)  # nosec B603
    try:
        returncode = process.wait(timeout=timeout)
    except BaseException:
        stop_process(process)
        raise
    if check and returncode:
        raise subprocess.CalledProcessError(returncode, arguments)
    return subprocess.CompletedProcess(arguments, returncode)


def execute_trial(arguments, recipients, output_directory):
    """Refresh, validate workload, execute partitions, then deliver and summarize."""
    from was_reports.reporting import analyst_summaries
    from was_reports.utils.capacity_telemetry import resource_monitor

    continuing = arguments.continuation_manifest is not None
    days_back = "all" if continuing else str(arguments.days_back)
    summary_module = "was_reports.reporting.analyst_summaries"
    summary_arguments = ["--batch-id", arguments.run_id, "--days-back",
                         days_back, "--test-recipients", recipients]
    workers = []
    succeeded = False
    started = monotonic()
    result = {"run_id": arguments.run_id, "capacity_pass": False}
    expected_count = None
    scope_environment = ("WAS_CAPACITY_TRACKER_IDS", "WAS_CAPACITY_CONTINUATION", "WAS_CAPACITY_PROGRESS")
    previous_scope = {name: os.environ.get(name) for name in scope_environment}
    workflow_clean = False
    trial_elapsed = None

    def remaining():
        """Return remaining trial time, failing before launching overdue work."""
        seconds = arguments.max_seconds - (monotonic() - started)
        if seconds <= 0:
            raise TimeoutError("Capacity trial exceeded its time budget.")
        return seconds

    with resource_monitor(output_directory):
        analyst_summaries.start_batch(arguments.run_id)
        try:
            if continuing:
                snapshot = dict(arguments.continuation_manifest,
                                run_id=arguments.run_id, workers=arguments.workers,
                                workload_label=arguments.workload_label)
            else:
                run_phase(command("was_reports.commands.update_tracker_cli",
                                  "--lookback-days", str(arguments.lookback_days)),
                          check=True, timeout=remaining())
                candidates = list_ready_report_candidates_from_db(days_back=arguments.days_back)
                snapshot = {
                    "run_id": arguments.run_id,
                    "root_run_id": arguments.run_id,
                    "workload_label": arguments.workload_label,
                    "workers": arguments.workers,
                    "candidate_count": len(candidates),
                    "candidate_ids": [candidate.id for candidate in candidates],
                    "candidates": [{"tracker_id": candidate.id, "tag": candidate.tag,
                                    "template": candidate.template}
                                   for candidate in candidates],
                    "notification_count": sum(candidate.template in
                                              {"All NWS", "FCEB All NWS"}
                                              for candidate in candidates),
                }
            expected_count = snapshot["candidate_count"]
            result.update({"expected": expected_count, "continuation": continuing,
                           "root_run_id": snapshot.get("root_run_id", arguments.run_id),
                           "parent_run_id": snapshot.get("parent_run_id")})
            os.environ["WAS_CAPACITY_TRACKER_IDS"] = json.dumps(snapshot["candidate_ids"])
            os.environ["WAS_CAPACITY_CONTINUATION"] = "1" if continuing else "0"
            print("Capacity run {} selected {} outcomes{}.".format(
                arguments.run_id, expected_count, " (continuation)" if continuing else ""))
            (output_directory / "workload.json").write_text(
                json.dumps(snapshot, indent=2), encoding="utf-8"
            )
            if arguments.expected_candidates is not None and expected_count != arguments.expected_candidates:
                raise ValueError("Refreshed candidate count differs from expected workload.")
            if continuing:
                result.update(continuation_status(snapshot["candidate_ids"], arguments.run_id))
                result["inherited_sent"] = result["sent"]
                result["inherited_generated"] = result["pdfs_generated"] + result["notifications_generated"]
            run_phase(command(summary_module, "--phase", "tracker",
                              *summary_arguments), check=True, timeout=remaining())
            for worker_index in range(arguments.workers if expected_count else 0):
                workers.append(subprocess.Popen(command(  # nosec B603
                    "was_reports.commands.batch_runner", "--recent-scans",
                    "--skip-tracker-refresh", "--worker-count", str(arguments.workers),
                    "--worker-index", str(worker_index), "--create-missing-password",
                    "--continue-on-error", "--days-back", days_back,
                    "--send-email", "--test-recipients", recipients,
                    "--skip-ready-email-retry", "--output-directory", str(output_directory)
                ), start_new_session=True))
            statuses = [worker.wait(timeout=remaining()) for worker in workers]
            delivery = run_phase(
                ["was-mailer", "--all-ready", "--include-previous-failures",
                 "--days-back", days_back, "--test-recipients", recipients],
                check=False, timeout=remaining(),
            ) if expected_count else subprocess.CompletedProcess([], 0)
            trial_elapsed = monotonic() - started
            if continuing:
                result.update(continuation_status(snapshot["candidate_ids"], arguments.run_id))
            elif expected_count:
                result.update(trial_counts(arguments.run_id))
            else:
                result.update({"attempted": 0, "pdfs_generated": 0, "notifications_generated": 0,
                               "sent": 0, "tracker_ids": []})
            result["remaining"] = expected_count - result["sent"]
            result.update({"worker_exit_codes": statuses,
                           "delivery_exit_code": delivery.returncode})
            workflow_clean = not any(statuses) and delivery.returncode == 0
            succeeded = (
                result["attempted"] == expected_count
                and set(result["tracker_ids"] or []) == set(snapshot["candidate_ids"])
                and result["pdfs_generated"] + result["notifications_generated"]
                == expected_count
                and result["sent"] == expected_count
                and trial_elapsed <= arguments.max_seconds
            )
        except BaseException as error:
            result["execution_error"] = type(error).__name__
            raise
        finally:
            for worker in workers:
                if worker.poll() is None:
                    stop_process(worker)
            trial_elapsed = trial_elapsed if trial_elapsed is not None else monotonic() - started
            if expected_count:
                try:
                    persisted = (continuation_status(snapshot["candidate_ids"], arguments.run_id)
                                 if continuing else trial_counts(arguments.run_id))
                    result.update(persisted)
                    result["remaining"] = expected_count - result["sent"]
                    result["counts_available"] = True
                except Exception as error:
                    result["counts_available"] = False
                    result["counts_error"] = type(error).__name__
            summary_succeeded = False
            summary_started = monotonic()
            try:
                os.environ["WAS_CAPACITY_PROGRESS"] = json.dumps({
                    "total": expected_count or 0,
                    "completed": result.get("pdfs_generated", 0) + result.get("notifications_generated", 0),
                    "failed": result.get("failed", 0), "remaining": result.get("remaining", expected_count or 0),
                    "blocked": result.get("blocked", 0),
                })
                os.environ["WAS_BATCH_OUTCOME"] = "completed" if succeeded else "failed"
                analyst_summaries.finish_batch(arguments.run_id, os.environ["WAS_BATCH_OUTCOME"])
                summary = run_phase(command(summary_module, "--phase", "final",
                                            *summary_arguments), check=False, timeout=60)
                summary_succeeded = summary.returncode == 0
            finally:
                result.update({"elapsed_seconds": trial_elapsed,
                               "summary_seconds": monotonic() - summary_started,
                               "summary_succeeded": summary_succeeded,
                               "workflow_clean": workflow_clean and summary_succeeded,
                               "workflow_completed": succeeded and summary_succeeded,
                               "capacity_pass": succeeded and not continuing and bool(expected_count)})
                (output_directory / "result.json").write_text(
                    json.dumps(result, indent=2), encoding="utf-8"
                )
                for name, value in previous_scope.items():
                    if value is None:
                        os.environ.pop(name, None)
                    else:
                        os.environ[name] = value
                print("Capacity outcomes: sent {}; remaining {}; blocked {}; capacity pass {}.".format(
                    result.get("sent", 0), result.get("remaining", "unknown"),
                    result.get("blocked", 0), result["capacity_pass"]))
    return 0 if result["workflow_completed"] else 1


def main(argv=None):
    """Default to read-only isolation checks without Qualys calls or delivery."""
    arguments = parse_args(argv)
    load_env_file()
    with capacity_database_environment():
        return run_capacity(arguments)


def run_capacity(arguments):
    """Run isolation checks and trial with the selected test environment."""
    connection = guard_database(arguments)
    previous_handler = signal.getsignal(signal.SIGTERM)
    try:
        recipients = ",".join(approved_analyst_recipients(arguments.test_recipients))
        print("Capacity run ID: {}".format(arguments.run_id))
        if not arguments.apply:
            print("Isolation and recipient checks passed. No refresh, writes, or sends.")
            return 0
        require_env("WAS_EMAIL_SOURCE")
        require_env("WAS_REPORTS_BUCKET_NAME")
        if arguments.continuation_manifest:
            arguments.workload_label = "continuation of {}".format(arguments.continue_run)
        output_directory = Path("/output/capacity") / arguments.run_id
        output_directory.mkdir(parents=True, exist_ok=False, mode=0o700)
        os.environ.update({
            "WAS_ANALYST_BATCH_ID": arguments.run_id,
            "WAS_CAPACITY_RUN_ID": arguments.run_id,
            "WAS_RUN_MODE": "capacity",
            "WAS_REPORT_WORKERS": str(arguments.workers),
            "WAS_WORKLOAD_LABEL": arguments.workload_label,
            "WAS_REPORTS_PREFIX": "capacity/" + arguments.run_id,
            "WAS_REPORT_STORAGE": "s3",
            "WAS_OUTPUT_DIRECTORY": str(output_directory),
            "WAS_METRICS_DIRECTORY": str(output_directory / "metrics"),
        })
        signal.signal(signal.SIGTERM, interrupt_trial)
        return execute_trial(arguments, recipients, output_directory)
    finally:
        signal.signal(signal.SIGTERM, previous_handler)
        connection.close()


def interrupt_trial(signum, frame):
    """Unwind the trial on container termination so workers are stopped."""
    raise KeyboardInterrupt("Capacity trial interrupted.")


if __name__ == "__main__":
    raise SystemExit(main())
