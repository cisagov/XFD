"""Preview or recover a production batch interrupted during report generation."""

# Standard Python Libraries
import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import partial
import json
import os
from pathlib import Path
import sys
from time import monotonic
from typing import Sequence
from uuid import UUID

# Third-Party Libraries
from requests.exceptions import HTTPError
from was_mailer.email_reports import approved_recipient_scope, send_report_run_email
from was_mailer.message import approved_analyst_recipients

# First-Party Libraries
from was_reports.commands.batch_runner import (
    NO_REPORT_TEMPLATES,
    generate_report_output,
    record_generation_failure,
    summarize_report_failure,
)
from was_reports.data.report_runs import (
    InterruptedReportRun,
    claim_interrupted_report_run,
    clear_qualys_report_id_by_run_id,
    complete_report_run_by_id,
    list_interrupted_report_runs,
    touch_report_run_by_id,
)
from was_reports.qualys.qualys_client import create_qualys_client
from was_reports.qualys.report_data import get_report_status
from was_reports.reporting import analyst_summaries
from was_reports.storage.s3_reports import S3_STORAGE
from was_reports.utils.database import connect
from was_reports.utils.env import getenv, require_env
from was_reports.utils.logging_config import configure_logging, exception_details
from was_reports.utils.operation_lease import operation_heartbeat
from was_reports.utils.qualys_config import load_qualys_credentials_from_environment

RECOVERY_CONFIRMATION = "RECOVER_INTERRUPTED_BATCH"
REPLACEMENT_CONFIRMATION = "REPLACE_MISSING_QUALYS_REPORTS"
DEFAULT_STALE_SECONDS = 300


@dataclass(frozen=True)
class QualysInspection:
    """Live, read-only Qualys state associated with one interrupted run."""

    report_run: InterruptedReportRun
    detail_status: str | None
    xml_status: str | None
    missing_labels: tuple[str, ...]


@dataclass(frozen=True)
class RecoveryWorkload:
    """Validated tracker and recipient scope saved by the coordinator."""

    tracker_ids: tuple[int, ...]
    delivery_mode: str | None
    recipient_scope: str | None


def positive_integer(value: str) -> int:
    """Parse an integer greater than zero."""
    parsed_value = int(value)
    if parsed_value < 1:
        raise argparse.ArgumentTypeError("Value must be greater than zero.")
    return parsed_value


def report_run_ids(value: str) -> frozenset[int]:
    """Parse unique positive report-run IDs from a comma-separated value."""
    identifiers: list[int] = []
    for raw_value in value.split(","):
        normalized_value = raw_value.strip()
        if not normalized_value:
            raise argparse.ArgumentTypeError("Report-run IDs cannot contain blanks.")
        identifier = positive_integer(normalized_value)
        if identifier in identifiers:
            raise argparse.ArgumentTypeError("Report-run IDs must be unique.")
        identifiers.append(identifier)
    return frozenset(identifiers)


def parse_args(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse preview-first interrupted-batch recovery arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-id", required=True, type=UUID)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path(getenv("WAS_OUTPUT_DIRECTORY", "/output") or "/output"),
    )
    parser.add_argument(
        "--resource-root",
        default=getenv("WAS_RESOURCE_ROOT", "/WAS_REPORT_RESOURCES"),
    )
    parser.add_argument(
        "--stale-seconds", type=positive_integer, default=DEFAULT_STALE_SECONDS
    )
    parser.add_argument(
        "--replace-missing-report-runs",
        type=report_run_ids,
        default=frozenset(),
    )
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm")
    parser.add_argument("--replacement-confirm")
    parser.add_argument("--send-email", action="store_true")
    parser.add_argument("--send-final-summary", action="store_true")
    parser.add_argument("--test-recipients")
    return parser.parse_args(arguments)


def load_workload(output_root: Path, batch_id: str) -> RecoveryWorkload:
    """Load and validate the immutable tracker and recipient scopes."""
    workload_path = (
        output_root.expanduser().resolve() / "batches" / batch_id / "workload.json"
    )
    if not workload_path.is_file() or workload_path.is_symlink():
        raise ValueError(
            "The interrupted batch workload snapshot is missing or invalid."
        )
    with workload_path.open(encoding="utf-8") as workload_file:
        workload = json.load(workload_file)
    if workload.get("run_id") != batch_id:
        raise ValueError("The workload snapshot does not match the selected batch.")
    tracker_ids = workload.get("candidate_ids")
    if not isinstance(tracker_ids, list) or not tracker_ids:
        raise ValueError("The workload snapshot has no candidate tracker IDs.")
    if any(
        not isinstance(identifier, int) or identifier < 1 for identifier in tracker_ids
    ):
        raise ValueError("The workload snapshot contains an invalid tracker ID.")
    if len(tracker_ids) != len(set(tracker_ids)):
        raise ValueError("The workload snapshot contains duplicate tracker IDs.")
    delivery_mode = workload.get("delivery_mode")
    recipient_scope = workload.get("recipient_scope")
    if delivery_mode is None and recipient_scope is None:
        return RecoveryWorkload(tuple(tracker_ids), None, None)
    if delivery_mode not in {"customer", "test"} or not isinstance(
        recipient_scope, str
    ):
        raise ValueError("The workload snapshot has invalid delivery metadata.")
    if delivery_mode == "customer" and recipient_scope != "stored-customer":
        raise ValueError("The customer workload recipient scope is invalid.")
    if delivery_mode == "test":
        scope_prefix = "test-sha256:"
        scope_digest = recipient_scope.removeprefix(scope_prefix)
        if (
            not recipient_scope.startswith(scope_prefix)
            or len(scope_digest) != 64
            or any(character not in "0123456789abcdef" for character in scope_digest)
        ):
            raise ValueError("The test workload recipient scope is invalid.")
    return RecoveryWorkload(tuple(tracker_ids), delivery_mode, recipient_scope)


def recovery_recipients(
    workload: RecoveryWorkload,
    raw_recipients: str | None,
    *,
    applying: bool,
) -> str | None:
    """Verify recovery recipients against the immutable workload scope."""
    if workload.delivery_mode is None:
        if applying:
            raise ValueError(
                "Applied recovery is blocked because this legacy workload has no "
                "recorded delivery mode or recipient scope."
            )
        if raw_recipients is not None:
            raise ValueError(
                "Test recipients cannot be verified for a legacy workload snapshot."
            )
        return None
    if workload.delivery_mode == "customer":
        if raw_recipients is not None:
            raise ValueError(
                "A customer workload cannot be recovered with test recipients."
            )
        return None
    if raw_recipients is None:
        if applying:
            raise ValueError(
                "Applied test-batch recovery requires the original approved "
                "--test-recipients."
            )
        return None
    normalized_recipients = ",".join(approved_analyst_recipients(raw_recipients))
    if approved_recipient_scope(normalized_recipients) != workload.recipient_scope:
        raise ValueError(
            "The supplied test recipients do not match the interrupted workload."
        )
    return normalized_recipients


def acquire_coordinator_lock():
    """Open the production database and retain its coordinator advisory lock."""
    if os.environ.get("WAS_RUN_MODE") == "capacity" or any(
        name.startswith("WAS_CAPACITY_") for name in os.environ
    ):
        raise ValueError("Production recovery cannot inherit capacity settings.")
    expected_database = require_env("WAS_DB_NAME")
    expected_user = require_env("WAS_DB_USERNAME")
    if any(
        value.startswith("was_capacity_")
        for value in (expected_database, expected_user)
    ):
        raise ValueError("Production recovery cannot use the capacity database.")
    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_database(), current_user")
            if tuple(cursor.fetchone()) != (expected_database, expected_user):
                raise ValueError("Live database identity does not match configuration.")
            cursor.execute(
                "SELECT pg_try_advisory_lock(hashtext(current_database()), "
                "hashtext('was_batch_coordinator'))"
            )
            if not cursor.fetchone()[0]:
                raise ValueError("Another report coordinator holds this database.")
        connection.rollback()
        return connection
    except BaseException:
        connection.close()
        raise


def _missing_report(error: Exception) -> bool:
    """Return whether Qualys definitively answered that a report is absent."""
    return (
        isinstance(error, HTTPError)
        and error.response is not None
        and error.response.status_code == 404
    )


def inspect_qualys_reports(
    interrupted_runs: list[InterruptedReportRun],
) -> list[QualysInspection]:
    """Read current Qualys status for every persisted report identifier."""
    credentials = load_qualys_credentials_from_environment()
    client = create_qualys_client(credentials)
    inspections: list[QualysInspection] = []
    for interrupted_run in interrupted_runs:
        statuses: dict[str, str | None] = {"detail": None, "xml": None}
        missing_labels: list[str] = []
        for label, report_id, persisted_status in (
            (
                "detail",
                interrupted_run.detail_report_id,
                interrupted_run.detail_report_status,
            ),
            ("xml", interrupted_run.xml_report_id, interrupted_run.xml_report_status),
        ):
            if report_id is None:
                if persisted_status == "CREATE_REQUESTED":
                    raise ValueError(
                        "Run {} has uncertain {} creation without a report ID.".format(
                            interrupted_run.id, label
                        )
                    )
                continue
            try:
                statuses[label] = get_report_status(client, report_id)
            except Exception as error:
                if not _missing_report(error):
                    raise
                missing_labels.append(label)
        inspections.append(
            QualysInspection(
                report_run=interrupted_run,
                detail_status=statuses["detail"],
                xml_status=statuses["xml"],
                missing_labels=tuple(missing_labels),
            )
        )
    return inspections


def validate_application_request(
    arguments: argparse.Namespace,
    inspections: list[QualysInspection],
) -> None:
    """Require exact confirmations before any database or external mutation."""
    missing_ids = {
        inspection.report_run.id
        for inspection in inspections
        if inspection.missing_labels
    }
    requested_ids = set(arguments.replace_missing_report_runs)
    if not requested_ids.issubset(missing_ids):
        raise ValueError("Replacement was requested for a report that still exists.")
    unapproved_missing = missing_ids - requested_ids
    if arguments.apply and unapproved_missing:
        raise ValueError(
            "Missing Qualys reports require explicit per-run replacement approval: {}.".format(
                ",".join(str(identifier) for identifier in sorted(unapproved_missing))
            )
        )
    if not arguments.apply:
        return
    if arguments.confirm != RECOVERY_CONFIRMATION:
        raise ValueError("--apply requires --confirm {}.".format(RECOVERY_CONFIRMATION))
    if not arguments.send_email or not arguments.send_final_summary:
        raise ValueError(
            "Applied recovery requires customer delivery and the final summary."
        )
    if requested_ids and arguments.replacement_confirm != REPLACEMENT_CONFIRMATION:
        raise ValueError(
            "Missing-report replacement requires --replacement-confirm {}.".format(
                REPLACEMENT_CONFIRMATION
            )
        )


def display_preview(inspections: list[QualysInspection]) -> None:
    """Print a secret-safe recovery preview for operator review."""
    for inspection in inspections:
        interrupted_run = inspection.report_run
        missing = ",".join(inspection.missing_labels) or "none"
        print(
            "Run {run_id}: tag={tag}; tracker={tracker}; detail_id={detail_id}; "
            "detail_status={detail_status}; xml_id={xml_id}; xml_status={xml_status}; "
            "missing={missing}.".format(
                run_id=interrupted_run.id,
                tag=(
                    interrupted_run.report_target_tag or interrupted_run.stakeholder_tag
                ),
                tracker=interrupted_run.source_tracker_id,
                detail_id=interrupted_run.detail_report_id or "none",
                detail_status=inspection.detail_status or "not started",
                xml_id=interrupted_run.xml_report_id or "none",
                xml_status=inspection.xml_status or "not started",
                missing=missing,
            )
        )


def recover_run(
    inspection: QualysInspection,
    coordinator_connection,
    arguments: argparse.Namespace,
    source_email: str,
    batch_id: str,
    override_recipients: str | None,
) -> bool:
    """Reclaim, generate, deliver, and record one interrupted customer report."""
    interrupted_run = inspection.report_run
    report_target_tag = (
        interrupted_run.report_target_tag or interrupted_run.stakeholder_tag
    )
    report_run = claim_interrupted_report_run(interrupted_run, coordinator_connection)
    if report_run is None or report_run.generation_token is None:
        print(
            "Run {} changed after preview and was not reclaimed.".format(
                interrupted_run.id
            ),
            file=sys.stderr,
        )
        return False
    if interrupted_run.id in arguments.replace_missing_report_runs:
        for label in inspection.missing_labels:
            report_id = (
                interrupted_run.detail_report_id
                if label == "detail"
                else interrupted_run.xml_report_id
            )
            if report_id is None:
                raise RuntimeError("Missing-report replacement lost its report ID.")
            clear_qualys_report_id_by_run_id(
                report_run.id,
                label,
                report_id,
                generation_token=report_run.generation_token,
            )

    started_at = monotonic()
    completion_attempted = False
    generated = False
    sent = False
    error_name = None
    delivery_started = None
    artifact_type = "pdf"
    try:
        if interrupted_run.template in NO_REPORT_TEMPLATES:
            artifact_type = "notification"
            completion_attempted = True
            complete_report_run_by_id(
                report_run.id,
                artifact_type=artifact_type,
                generation_token=report_run.generation_token,
            )
        else:
            with operation_heartbeat(
                heartbeat=partial(
                    touch_report_run_by_id,
                    report_run.id,
                    generation_token=report_run.generation_token,
                ),
                operation_name="report run {} recovery".format(report_run.id),
            ):
                output_reference = generate_report_output(
                    report_run_id=report_run.id,
                    stakeholder_tag=report_target_tag,
                    resource_root=arguments.resource_root,
                    python_executable=sys.executable,
                    create_missing_password=True,
                    output_directory=str(arguments.output_root),
                    storage_mode=S3_STORAGE,
                    staging_directory=str(arguments.output_root / ".recovery-staging"),
                    generation_token=report_run.generation_token,
                    tag_id=interrupted_run.tag_id,
                    organization_name=interrupted_run.organization_name,
                    password_stakeholder_tag=report_run.stakeholder_tag,
                )
            completion_attempted = True
            complete_report_run_by_id(
                report_run.id,
                output_path=output_reference,
                artifact_type=artifact_type,
                generation_token=report_run.generation_token,
            )
        generated = True
        delivery_started = monotonic()
        message_id = send_report_run_email(
            report_run_id=report_run.id,
            source_email=source_email,
            override_recipients=override_recipients,
            delivery_purpose="customer",
        )
        sent = bool(message_id)
    except Exception as error:
        error_name = type(error).__name__
        if not generated and not completion_attempted:
            record_generation_failure(
                report_run,
                summarize_report_failure(error),
                error,
            )
        print(
            "Run {} recovery failed: {}.".format(
                report_run.id, exception_details(error, include_origin=False)
            ),
            file=sys.stderr,
        )
    analyst_summaries.record_report_attempt(
        batch_id,
        interrupted_run.source_tracker_id,
        monotonic() - started_at,
        generated=generated,
        sent=sent,
        error=error_name,
        report_run_id=report_run.id,
        delivery_duration_seconds=(
            monotonic() - delivery_started if delivery_started is not None else None
        ),
        artifact_type=artifact_type,
    )
    return generated and sent


def active_operation_count(connection) -> int:
    """Return the number of database operations that still block production."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) FROM was_report_runs "
            "WHERE status='running' OR email_status='sending'"
        )
        return int(cursor.fetchone()[0])


def main(raw_arguments: Sequence[str] | None = None) -> int:
    """Preview interrupted state or perform explicitly confirmed recovery."""
    configure_logging()
    arguments = parse_args(raw_arguments)
    batch_id = str(arguments.batch_id)
    workload = load_workload(arguments.output_root, batch_id)
    override_recipients = recovery_recipients(
        workload,
        arguments.test_recipients,
        applying=arguments.apply,
    )
    print(
        "Recovery delivery mode: {}.".format(workload.delivery_mode or "legacy-unknown")
    )
    coordinator_connection = acquire_coordinator_lock()
    try:
        stale_before = datetime.now(timezone.utc) - timedelta(
            seconds=arguments.stale_seconds
        )
        interrupted_runs = list_interrupted_report_runs(
            batch_id,
            list(workload.tracker_ids),
            stale_before,
            coordinator_connection,
        )
        coordinator_connection.rollback()
        inspections = inspect_qualys_reports(interrupted_runs)
        display_preview(inspections)
        validate_application_request(arguments, inspections)
        if not arguments.apply:
            print(
                "Preview only. No database, Qualys, S3, tracker, or email state was changed."
            )
            return 0

        source_email = require_env("WAS_EMAIL_SOURCE")
        succeeded = 0
        for inspection in inspections:
            succeeded += int(
                recover_run(
                    inspection,
                    coordinator_connection,
                    arguments,
                    source_email,
                    batch_id,
                    override_recipients,
                )
            )
        remaining_active = active_operation_count(coordinator_connection)
        coordinator_connection.rollback()
        if remaining_active:
            print(
                "Recovery retained {} active or uncertain operation(s); the batch was not finalized.".format(
                    remaining_active
                ),
                file=sys.stderr,
            )
            return 2
        analyst_summaries.finish_batch(batch_id, outcome="failed")
        analyst_summaries.send_batch_summary(
            batch_id,
            source_email=source_email,
            override_recipients=override_recipients,
            days_back=7,
        )
        print(
            "Interrupted batch recovery completed: recovered={}; selected={}; batch outcome=failed.".format(
                succeeded, len(inspections)
            )
        )
        return 0 if succeeded == len(inspections) else 1
    finally:
        coordinator_connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
