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
from uuid import UUID

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


def parse_args(argv=None):
    """Require an explicit trial identity, workload, and approved recipients."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True, type=UUID)
    parser.add_argument("--workload-label", required=True)
    parser.add_argument("--test-recipients", required=True)
    parser.add_argument("--workers", type=int, default=30)
    parser.add_argument("--expected-candidates", type=int, default=600)
    parser.add_argument("--days-back", type=int, default=7)
    parser.add_argument("--lookback-days", type=int, default=3)
    parser.add_argument("--max-seconds", type=int, default=28800)
    parser.add_argument("--apply", action="store_true")
    arguments = parser.parse_args(argv)
    if not 1 <= arguments.workers <= 30:
        parser.error("--workers must be from 1 through 30.")
    if min(arguments.days_back, arguments.lookback_days,
           arguments.expected_candidates, arguments.max_seconds) <= 0:
        parser.error("Candidate count and lookback windows must be positive.")
    if arguments.max_seconds > 28800:
        parser.error("--max-seconds cannot exceed the eight-hour capacity target.")
    if not arguments.workload_label.strip():
        parser.error("--workload-label must identify the clone baseline.")
    arguments.run_id = str(arguments.run_id)
    return arguments


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
            cursor.execute(
                "SELECT EXISTS(SELECT 1 FROM was_report_runs WHERE status='running' "
                "OR email_status='sending' OR (status='completed' "
                "AND COALESCE(email_status,'pending') IN ('pending','failed')))"
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
                "ARRAY_AGG(attempts.tracker_id) "
                "FROM was_batch_report_attempts attempts "
                "JOIN was_batch_runs batch ON batch.batch_id=attempts.batch_id "
                "LEFT JOIN was_report_runs runs ON runs.id=attempts.report_run_id "
                "WHERE attempts.batch_id=%s", (run_id,)
            )
            return dict(zip(("attempted", "pdfs_generated", "notifications_generated",
                             "sent", "tracker_ids"), cursor.fetchone()))
    finally:
        connection.close()


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

    summary_module = "was_reports.reporting.analyst_summaries"
    summary_arguments = ["--batch-id", arguments.run_id, "--days-back",
                         str(arguments.days_back), "--test-recipients", recipients]
    workers = []
    succeeded = False
    started = monotonic()
    result = {"run_id": arguments.run_id, "capacity_pass": False}
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
            run_phase(command("was_reports.commands.update_tracker_cli",
                              "--lookback-days", str(arguments.lookback_days)),
                      check=True, timeout=remaining())
            candidates = list_ready_report_candidates_from_db(days_back=arguments.days_back)
            snapshot = {
                "run_id": arguments.run_id,
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
            (output_directory / "workload.json").write_text(
                json.dumps(snapshot, indent=2), encoding="utf-8"
            )
            if len(candidates) != arguments.expected_candidates:
                raise ValueError("Refreshed candidate count differs from expected workload.")
            run_phase(command(summary_module, "--phase", "tracker",
                              *summary_arguments), check=True, timeout=remaining())
            for worker_index in range(arguments.workers):
                workers.append(subprocess.Popen(command(  # nosec B603
                    "was_reports.commands.batch_runner", "--recent-scans",
                    "--skip-tracker-refresh", "--worker-count", str(arguments.workers),
                    "--worker-index", str(worker_index), "--create-missing-password",
                    "--continue-on-error", "--days-back", str(arguments.days_back),
                    "--send-email", "--test-recipients", recipients,
                    "--skip-ready-email-retry", "--output-directory", str(output_directory)
                ), start_new_session=True))
            statuses = [worker.wait(timeout=remaining()) for worker in workers]
            delivery = run_phase(
                ["was-mailer", "--all-ready", "--include-previous-failures",
                 "--days-back", str(arguments.days_back), "--test-recipients", recipients],
                check=False, timeout=remaining(),
            )
            trial_elapsed = monotonic() - started
            result.update(trial_counts(arguments.run_id))
            result.update({"worker_exit_codes": statuses,
                           "delivery_exit_code": delivery.returncode})
            workflow_clean = not any(statuses) and delivery.returncode == 0
            succeeded = (
                result["attempted"] == arguments.expected_candidates
                and set(result["tracker_ids"] or []) == set(snapshot["candidate_ids"])
                and result["pdfs_generated"] + result["notifications_generated"]
                == arguments.expected_candidates
                and result["sent"] == arguments.expected_candidates
                and trial_elapsed <= arguments.max_seconds
            )
        finally:
            for worker in workers:
                if worker.poll() is None:
                    stop_process(worker)
            trial_elapsed = trial_elapsed if trial_elapsed is not None else monotonic() - started
            summary_succeeded = False
            summary_started = monotonic()
            try:
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
                               "capacity_pass": succeeded})
                (output_directory / "result.json").write_text(
                    json.dumps(result, indent=2), encoding="utf-8"
                )
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
        if not arguments.apply:
            print("Isolation and recipient checks passed. No refresh, writes, or sends.")
            return 0
        require_env("WAS_EMAIL_SOURCE")
        require_env("WAS_REPORTS_BUCKET_NAME")
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
