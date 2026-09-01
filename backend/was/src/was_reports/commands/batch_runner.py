"""Batch runner for scheduled WAS report generation."""

# Standard Python Libraries
import argparse
from datetime import date, datetime, timezone
import logging
from pathlib import Path
import subprocess  # nosec B404
import sys
from tempfile import TemporaryDirectory, gettempdir
from typing import List, Optional

# Third-Party Libraries
# First-Party Libraries
from was_reports.commands import report_generator
from was_reports.data.report_runs import (
    complete_report_run_by_id,
    create_report_run_for_tag,
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
from was_reports.utils.env import getenv
from was_reports.utils.outputs import expected_pdf_output_path

LOGGER = logging.getLogger(__name__)
DEFAULT_STAGING_DIRECTORY = str(Path(gettempdir()) / "was-report-storage")


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
            report_date = date.today()
            if resolved_storage_mode == S3_STORAGE:
                staging_root = Path(staging_directory)
                staging_root.mkdir(parents=True, exist_ok=True)
                with TemporaryDirectory(
                    prefix="was-run-{}-".format(report_run.id),
                    dir=str(staging_root),
                ) as run_directory:
                    report_arguments = build_report_arguments(
                        stakeholder_tag=stakeholder.tag,
                        resource_root=resource_root,
                        output_directory=run_directory,
                        python_executable=python_executable,
                        create_missing_password=create_missing_password,
                    )
                    report_generator.main(report_arguments)
                    local_output_path = expected_pdf_output_path(
                        stakeholder_tag=stakeholder.tag,
                        output_directory=run_directory,
                        report_date=report_date,
                    )
                    output_reference = upload_report(
                        report_path=local_output_path,
                        stakeholder_tag=stakeholder.tag,
                        report_date=report_date,
                        report_run_id=report_run.id,
                    )
                    uploaded_reference = output_reference
            else:
                report_arguments = build_report_arguments(
                    stakeholder_tag=stakeholder.tag,
                    resource_root=resource_root,
                    output_directory=output_directory,
                    python_executable=python_executable,
                    create_missing_password=create_missing_password,
                )
                report_generator.main(report_arguments)
                output_reference = str(
                    expected_pdf_output_path(
                        stakeholder_tag=stakeholder.tag,
                        output_directory=output_directory,
                        report_date=report_date,
                    )
                )
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
