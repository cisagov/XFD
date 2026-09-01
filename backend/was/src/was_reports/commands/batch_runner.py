"""Batch runner for scheduled WAS report generation."""

# Standard Python Libraries
import argparse
from dataclasses import dataclass
from datetime import date, datetime, timezone
import logging
from pathlib import Path
import subprocess  # nosec B404
import sys
from tempfile import TemporaryDirectory, gettempdir
from typing import List, Optional

# Third-Party Libraries
from was_mailer.email_reports import (
    send_ready_assignee_digests,
    send_ready_report_emails,
    send_report_run_email,
)

# First-Party Libraries
from was_reports.commands import report_generator
from was_reports.commands.update_tracker_cli import run_update_tracker
from was_reports.data.daily_report_tracker import (
    list_ready_report_candidates_from_db,
    mark_tracker_report_manual_by_id,
)
from was_reports.data.report_runs import (
    complete_report_run_by_id,
    create_report_run_for_tag,
    create_report_run_for_tracker,
    fail_report_run_by_id,
)
from was_reports.data.stakeholders import list_due_stakeholders_for_report
from was_reports.storage.s3_reports import (
    S3_STORAGE,
    VALID_STORAGE_MODES,
    delete_report,
    resolve_storage_mode,
    upload_report,
)
from was_reports.utils.env import getenv, require_env
from was_reports.utils.outputs import expected_pdf_output_path

LOGGER = logging.getLogger(__name__)
DEFAULT_STAGING_DIRECTORY = str(Path(gettempdir()) / "was-report-storage")


@dataclass(frozen=True)
class BatchExecutionSummary:
    """Counts produced by one recent-scan report batch."""

    candidates: int
    generated: int
    sent: int
    failed: int


def current_epoch_seconds() -> int:
    """Return the current UTC epoch timestamp in seconds."""
    return int(datetime.now(timezone.utc).timestamp())


def summarize_report_failure(exception: Exception) -> str:
    """Return a safe report failure summary for database storage."""
    if isinstance(exception, subprocess.CalledProcessError):
        return "Report generation failed with exit code {}.".format(
            exception.returncode
        )

    if isinstance(exception, FileNotFoundError):
        return "Required report file was not found."

    return "{} occurred during report generation.".format(type(exception).__name__)


def build_report_arguments(
    stakeholder_tag: str,
    resource_root: str,
    output_directory: str,
    python_executable: str,
    create_missing_password: bool,
) -> List[str]:
    """Build arguments for one WAS report generation call."""
    arguments = [
        "--tag",
        stakeholder_tag,
        "--resource-root",
        resource_root,
        "--output-directory",
        output_directory,
        "--python-executable",
        python_executable,
    ]

    if create_missing_password:
        arguments.append("--create-missing-password")

    return arguments


def generate_report_output(
    report_run_id: int,
    stakeholder_tag: str,
    resource_root: str,
    python_executable: str,
    create_missing_password: bool,
    output_directory: str,
    storage_mode: str,
    staging_directory: str,
) -> str:
    """Generate one report and return its durable output reference."""
    report_date = date.today()
    if storage_mode == S3_STORAGE:
        staging_root = Path(staging_directory)
        staging_root.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(
            prefix="was-run-{}-".format(report_run_id),
            dir=str(staging_root),
        ) as run_directory:
            report_arguments = build_report_arguments(
                stakeholder_tag=stakeholder_tag,
                resource_root=resource_root,
                output_directory=run_directory,
                python_executable=python_executable,
                create_missing_password=create_missing_password,
            )
            report_generator.main(report_arguments)
            local_output_path = expected_pdf_output_path(
                stakeholder_tag=stakeholder_tag,
                output_directory=run_directory,
                report_date=report_date,
            )
            return upload_report(
                report_path=local_output_path,
                stakeholder_tag=stakeholder_tag,
                report_date=report_date,
                report_run_id=report_run_id,
            )

    report_arguments = build_report_arguments(
        stakeholder_tag=stakeholder_tag,
        resource_root=resource_root,
        output_directory=output_directory,
        python_executable=python_executable,
        create_missing_password=create_missing_password,
    )
    report_generator.main(report_arguments)
    return str(
        expected_pdf_output_path(
            stakeholder_tag=stakeholder_tag,
            output_directory=output_directory,
            report_date=report_date,
        )
    )


def run_due_reports(
    resource_root: str,
    python_executable: str,
    current_epoch: int,
    create_missing_password: bool = False,
    include_manual: bool = False,
    include_retired: bool = False,
    limit: Optional[int] = None,
    continue_on_error: bool = False,
    output_directory: str = "/WAS_REPORT_GENERATION/docs",
    storage_mode: str = S3_STORAGE,
    staging_directory: str = DEFAULT_STAGING_DIRECTORY,
) -> int:
    """Generate reports for all due stakeholders."""
    stakeholders = list_due_stakeholders_for_report(
        current_epoch=current_epoch,
        include_manual=include_manual,
        include_retired=include_retired,
        limit=limit,
    )
    failed_count = 0
    resolved_storage_mode = resolve_storage_mode(storage_mode)

    for stakeholder in stakeholders:
        report_run = create_report_run_for_tag(
            stakeholder_tag=stakeholder.tag,
            scheduled_epoch=stakeholder.next_scheduled,
        )
        if report_run is None:
            LOGGER.info(
                "Skipping stakeholder tag %s because schedule %s is already claimed.",
                stakeholder.tag,
                stakeholder.next_scheduled,
            )
            continue
        uploaded_reference = None
        try:
            output_reference = generate_report_output(
                report_run_id=report_run.id,
                stakeholder_tag=stakeholder.tag,
                resource_root=resource_root,
                python_executable=python_executable,
                create_missing_password=create_missing_password,
                output_directory=output_directory,
                storage_mode=resolved_storage_mode,
                staging_directory=staging_directory,
            )
            if resolved_storage_mode == S3_STORAGE:
                uploaded_reference = output_reference
            complete_report_run_by_id(
                report_run.id,
                output_path=output_reference,
                artifact_type="pdf",
            )
        except Exception as exception:
            failed_count += 1
            if uploaded_reference:
                try:
                    delete_report(uploaded_reference)
                except Exception:
                    LOGGER.exception(
                        "Unable to remove orphaned WAS S3 report for run id %s",
                        report_run.id,
                    )
            fail_report_run_by_id(
                report_run_id=report_run.id,
                error_message=summarize_report_failure(exception),
            )
            LOGGER.exception(
                "WAS report generation failed for stakeholder tag %s",
                stakeholder.tag,
            )
            if not continue_on_error:
                raise

    return failed_count


def run_recent_scan_reports(
    resource_root: str,
    python_executable: str,
    create_missing_password: bool = False,
    stakeholder_tag: Optional[str] = None,
    limit: Optional[int] = None,
    continue_on_error: bool = True,
    output_directory: str = "/WAS_REPORT_GENERATION/docs",
    storage_mode: str = S3_STORAGE,
    staging_directory: str = DEFAULT_STAGING_DIRECTORY,
    send_email: bool = False,
    send_assignee_digests: bool = False,
    source_email: Optional[str] = None,
    test_recipients: Optional[str] = None,
    dry_run_email: bool = False,
) -> BatchExecutionSummary:
    """Generate and deliver reports for recent tracker rows with delivery gaps."""
    candidates = list_ready_report_candidates_from_db(
        stakeholder_tag=stakeholder_tag,
        limit=limit,
    )
    resolved_storage_mode = resolve_storage_mode(storage_mode)
    generated_count = 0
    sent_count = 0
    failed_count = 0

    if send_email:
        sent_count += send_ready_report_emails(
            source_email=source_email or require_env("WAS_EMAIL_SOURCE"),
            override_recipients=test_recipients,
            dry_run=dry_run_email,
            stakeholder_tag=stakeholder_tag,
        )

    for candidate in candidates:
        report_run = create_report_run_for_tracker(
            stakeholder_tag=candidate.tag,
            source_tracker_id=candidate.id,
        )
        if report_run is None:
            LOGGER.info(
                "Skipping tracker row %s because another worker already claimed it.",
                candidate.id,
            )
            continue

        uploaded_reference = None
        try:
            output_reference = generate_report_output(
                report_run_id=report_run.id,
                stakeholder_tag=candidate.tag,
                resource_root=resource_root,
                python_executable=python_executable,
                create_missing_password=create_missing_password,
                output_directory=output_directory,
                storage_mode=resolved_storage_mode,
                staging_directory=staging_directory,
            )
            if resolved_storage_mode == S3_STORAGE:
                uploaded_reference = output_reference
            complete_report_run_by_id(
                report_run.id,
                output_path=output_reference,
                artifact_type="pdf",
            )
            generated_count += 1
        except Exception as exception:
            failed_count += 1
            if uploaded_reference:
                try:
                    delete_report(uploaded_reference)
                except Exception:
                    LOGGER.exception(
                        "Unable to remove orphaned WAS S3 report for run id %s",
                        report_run.id,
                    )
            fail_report_run_by_id(
                report_run_id=report_run.id,
                error_message=summarize_report_failure(exception),
            )
            mark_tracker_report_manual_by_id(candidate.id)
            LOGGER.exception(
                "WAS report generation failed for tracker row %s and tag %s",
                candidate.id,
                candidate.tag,
            )
            if not continue_on_error:
                raise
            continue

        if send_email:
            try:
                message_id = send_report_run_email(
                    report_run_id=report_run.id,
                    source_email=source_email or require_env("WAS_EMAIL_SOURCE"),
                    override_recipients=test_recipients,
                    dry_run=dry_run_email,
                )
                if message_id or dry_run_email:
                    sent_count += 1
            except Exception:
                failed_count += 1
                LOGGER.exception(
                    "WAS report email failed for tracker row %s and run id %s",
                    candidate.id,
                    report_run.id,
                )
                if not continue_on_error:
                    raise

    if send_assignee_digests:
        send_ready_assignee_digests(
            source_email=source_email or require_env("WAS_EMAIL_SOURCE"),
            override_recipients=test_recipients,
            dry_run=dry_run_email,
        )

    summary = BatchExecutionSummary(
        candidates=len(candidates),
        generated=generated_count,
        sent=sent_count,
        failed=failed_count,
    )
    LOGGER.info(
        "Recent-scan WAS batch completed: candidates=%d generated=%d sent=%d "
        "failed=%d",
        summary.candidates,
        summary.generated,
        summary.sent,
        summary.failed,
    )
    return summary


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command line arguments for scheduled WAS reports."""
    default_resource_root = getenv("WAS_RESOURCE_ROOT", "/WAS_REPORT_RESOURCES")

    parser = argparse.ArgumentParser(
        description="Generate WAS reports for stakeholders whose schedule is due."
    )
    parser.add_argument(
        "--resource-root",
        default=default_resource_root,
        help="Directory containing production WAS templates and report assets.",
    )
    parser.add_argument(
        "--python-executable",
        default=sys.executable,
        help="Python executable used for report helper subprocesses.",
    )
    parser.add_argument(
        "--current-epoch",
        type=int,
        default=current_epoch_seconds(),
        help="UTC epoch seconds used for due-report selection.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of due stakeholder reports to generate.",
    )
    parser.add_argument(
        "--recent-scans",
        action="store_true",
        help=(
            "Refresh recent Qualys scans, then generate reports for tracker rows "
            "that have not been sent."
        ),
    )
    parser.add_argument(
        "--skip-tracker-refresh",
        action="store_true",
        help="Use existing tracker rows without querying Qualys for recent scans.",
    )
    parser.add_argument(
        "-t",
        "--tag",
        help="Limit recent-scan discovery and reporting to one stakeholder tag.",
    )
    parser.add_argument(
        "--create-missing-password",
        action="store_true",
        help="Create stakeholder report passwords when missing.",
    )
    parser.add_argument(
        "--include-manual",
        action="store_true",
        help="Include stakeholders marked for manual reporting.",
    )
    parser.add_argument(
        "--include-retired",
        action="store_true",
        help="Include retired stakeholders.",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue generating remaining reports after a stakeholder failure.",
    )
    parser.add_argument(
        "--send-email",
        action="store_true",
        help="Send ready reports through SES after generation.",
    )
    parser.add_argument(
        "--send-assignee-digests",
        action="store_true",
        help="Send tracker statistics and assignments to WAS assignees.",
    )
    parser.add_argument(
        "--source-email",
        default=getenv("WAS_EMAIL_SOURCE"),
        help="Verified SES sender address used by recent-scan batch delivery.",
    )
    parser.add_argument(
        "--test-recipients",
        help="Override report and digest recipients for controlled testing.",
    )
    parser.add_argument(
        "--dry-run-email",
        action="store_true",
        help="Build report and digest emails without sending them through SES.",
    )
    parser.add_argument(
        "--output-directory",
        default=getenv("WAS_OUTPUT_DIRECTORY", "/WAS_REPORT_GENERATION/docs"),
        help="Directory where generated WAS PDF reports are written.",
    )
    parser.add_argument(
        "--storage-mode",
        choices=VALID_STORAGE_MODES,
        default=resolve_storage_mode(),
        help="Store completed reports in S3 or retain them on local disk.",
    )
    parser.add_argument(
        "--staging-directory",
        default=getenv("WAS_REPORT_STAGING_DIRECTORY", DEFAULT_STAGING_DIRECTORY),
        help="Temporary report directory used before S3 upload.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """Run scheduled WAS report generation."""
    logging.basicConfig(level=logging.INFO)
    args = parse_args(argv)
    if args.recent_scans:
        stakeholder_tag = args.tag.strip() if args.tag else None
        if args.tag and not stakeholder_tag:
            raise ValueError("Stakeholder tag must not be empty.")
        if not args.skip_tracker_refresh:
            run_update_tracker(
                delete_apps=False,
                stakeholder_tag=stakeholder_tag,
            )
        summary = run_recent_scan_reports(
            resource_root=args.resource_root,
            python_executable=args.python_executable,
            create_missing_password=args.create_missing_password,
            stakeholder_tag=stakeholder_tag,
            limit=args.limit,
            continue_on_error=args.continue_on_error,
            output_directory=args.output_directory,
            storage_mode=args.storage_mode,
            staging_directory=args.staging_directory,
            send_email=args.send_email,
            send_assignee_digests=args.send_assignee_digests,
            source_email=args.source_email,
            test_recipients=args.test_recipients,
            dry_run_email=args.dry_run_email,
        )
        return 1 if summary.failed else 0

    recent_scan_only_options = [
        args.skip_tracker_refresh,
        args.tag is not None,
        args.send_email,
        args.send_assignee_digests,
        args.test_recipients is not None,
        args.dry_run_email,
    ]
    if any(recent_scan_only_options):
        raise ValueError("Recent-scan batch options require --recent-scans.")
    failed_count = run_due_reports(
        resource_root=args.resource_root,
        python_executable=args.python_executable,
        current_epoch=args.current_epoch,
        create_missing_password=args.create_missing_password,
        include_manual=args.include_manual,
        include_retired=args.include_retired,
        limit=args.limit,
        continue_on_error=args.continue_on_error,
        output_directory=args.output_directory,
        storage_mode=args.storage_mode,
        staging_directory=args.staging_directory,
    )
    if failed_count:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
