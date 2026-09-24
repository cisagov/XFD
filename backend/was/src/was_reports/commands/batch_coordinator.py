"""Coordinate production reporting through the shared capacity-tested engine."""

import argparse
import os
from pathlib import Path
from uuid import UUID, uuid4

from was_mailer.message import approved_analyst_recipients
from was_reports.commands import capacity_test
from was_reports.utils.database import connect
from was_reports.utils.env import load_env_file, require_env


def days_back_value(value: str):
    """Accept an explicit unlimited window or a positive calendar-day count."""
    if value.lower() == "all":
        return None
    try:
        count = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("Use all or a positive day count.") from error
    if count <= 0:
        raise argparse.ArgumentTypeError("Use all or a positive day count.")
    return count


def parse_args(argv=None):
    """Parse the production launcher without implicitly authorizing execution."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", type=UUID)
    parser.add_argument("--workers", type=int, default=30)
    parser.add_argument("--worker-backend", choices=("docker", "process"), default="docker")
    parser.add_argument("--worker-image", default="was-reporting")
    parser.add_argument("--output-root", type=Path, default=Path("/output"))
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--days-back", type=days_back_value, default=7)
    parser.add_argument("--lookback-days", type=int, default=3)
    parser.add_argument("--max-seconds", type=int, default=28800)
    parser.add_argument("--test-recipients")
    parser.add_argument("--apply", action="store_true")
    arguments = parser.parse_args(argv)
    if not 1 <= arguments.workers <= 30:
        parser.error("--workers must be from 1 through 30.")
    if arguments.lookback_days <= 0 or arguments.max_seconds <= 0:
        parser.error("Lookback and execution windows must be positive.")
    if arguments.test_recipients is not None and not arguments.test_recipients.strip():
        parser.error("An explicit test-recipient override cannot be empty.")
    arguments.run_id = str(arguments.run_id or uuid4())
    arguments.run_mode = "production"
    arguments.workload_label = "recent-scan-batch"
    arguments.expected_candidates = None
    arguments.continuation_manifest = None
    return arguments


def guard_database(arguments):
    """Retain a database-wide coordinator lock and reject ambiguous in-flight work."""
    if os.environ.get("WAS_RUN_MODE") == "capacity" or any(
        name.startswith("WAS_CAPACITY_") for name in os.environ
    ):
        raise ValueError("Production launcher cannot inherit capacity settings.")
    expected_database = require_env("WAS_DB_NAME")
    expected_user = require_env("WAS_DB_USERNAME")
    if any(value.startswith("was_capacity_") for value in (expected_database, expected_user)):
        raise ValueError("Use the capacity launcher for the capacity database and role.")
    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_database(), current_user")
            if tuple(cursor.fetchone()) != (expected_database, expected_user):
                raise ValueError("Live database identity does not match configuration.")
            if arguments.apply:
                cursor.execute(
                    "SELECT pg_try_advisory_lock(hashtext(current_database()), "
                    "hashtext('was_batch_coordinator'))"
                )
                if not cursor.fetchone()[0]:
                    raise ValueError("Another report coordinator holds this database.")
            cursor.execute("SELECT EXISTS(SELECT 1 FROM was_batch_runs WHERE batch_id=%s)",
                           (arguments.run_id,))
            if cursor.fetchone()[0]:
                raise ValueError("Run ID already exists; use a new run ID.")
            cursor.execute("SELECT EXISTS(SELECT 1 FROM was_report_runs "
                           "WHERE status='running' OR email_status='sending')")
            if cursor.fetchone()[0]:
                raise ValueError("Active or uncertain report operations require reconciliation.")
        connection.rollback()
        return connection
    except BaseException:
        connection.close()
        raise


def main(argv=None):
    """Check configuration read-only, or explicitly apply the shared reporting run."""
    arguments = parse_args(argv)
    if arguments.env_file is not None and not arguments.env_file.is_file():
        raise ValueError("Specified environment file does not exist.")
    load_env_file(arguments.env_file)
    connection = guard_database(arguments)
    try:
        capacity_test.verify_worker_backend(arguments)
        recipients = (
            ",".join(approved_analyst_recipients(arguments.test_recipients))
            if arguments.test_recipients else None
        )
        print("Report batch ID: {}".format(arguments.run_id))
        if not arguments.apply:
            print("Configuration checks passed. No refresh, writes, or sends.")
            return 0
        require_env("WAS_EMAIL_SOURCE")
        require_env("WAS_REPORTS_BUCKET_NAME")
        return capacity_test.run_coordinated(arguments, recipients)
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
