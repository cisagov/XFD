"""Batch runner for scheduled WAS report generation."""

# Standard Python Libraries
import argparse
import logging
import subprocess
import sys
from datetime import datetime, timezone
from typing import List, Optional

# First-Party Libraries
from was_reports import report_generator
from was_reports.data.report_runs import (
    complete_report_run_by_id,
    create_report_run_for_tag,
    fail_report_run_by_id,
)
from was_reports.data.stakeholders import list_due_stakeholders_for_report
from was_reports.utils.env import getenv
from was_reports.utils.outputs import expected_pdf_output_path

LOGGER = logging.getLogger(__name__)


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

    return "{} occurred during report generation.".format(
        type(exception).__name__
    )


def build_report_arguments(
    stakeholder_tag: str,
    config_path: str,
    legacy_root: str,
    output_directory: str,
    python_executable: str,
    create_missing_password: bool,
    allow_unencrypted: bool,
) -> List[str]:
    """Build arguments for one WAS report generation call."""
    arguments = [
        "--tag",
        stakeholder_tag,
        "--config-path",
        config_path,
        "--legacy-root",
        legacy_root,
        "--output-directory",
        output_directory,
        "--python-executable",
        python_executable,
    ]

    if create_missing_password:
        arguments.append("--create-missing-password")

    if allow_unencrypted:
        arguments.append("--allow-unencrypted")

    return arguments


def run_due_reports(
    config_path: str,
    legacy_root: str,
    python_executable: str,
    current_epoch: int,
    create_missing_password: bool = False,
    allow_unencrypted: bool = False,
    include_manual: bool = False,
    include_retired: bool = False,
    limit: Optional[int] = None,
    continue_on_error: bool = False,
    output_directory: str = "/WAS_REPORT_GENERATION/docs",
) -> int:
    """Generate reports for all due stakeholders."""
    stakeholders = list_due_stakeholders_for_report(
        current_epoch=current_epoch,
        include_manual=include_manual,
        include_retired=include_retired,
        limit=limit,
    )
    failed_count = 0

    for stakeholder in stakeholders:
        report_run = create_report_run_for_tag(
            stakeholder_tag=stakeholder.tag,
            scheduled_epoch=stakeholder.next_scheduled,
        )
        report_arguments = build_report_arguments(
            stakeholder_tag=stakeholder.tag,
            config_path=config_path,
            legacy_root=legacy_root,
            output_directory=output_directory,
            python_executable=python_executable,
            create_missing_password=create_missing_password,
            allow_unencrypted=allow_unencrypted,
        )
        try:
            report_generator.main(report_arguments)
            complete_report_run_by_id(
                report_run.id,
                output_path=str(
                    expected_pdf_output_path(
                        stakeholder_tag=stakeholder.tag,
                        output_directory=output_directory,
                    )
                ),
                artifact_type="pdf",
            )
        except Exception as exception:
            failed_count += 1
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
    default_config_path = getenv(
        "WAS_CONFIG_PATH", "/WAS_REPORT_GENERATION/docs/was_config.txt"
    )
    default_legacy_root = getenv("WAS_LEGACY_ROOT", "/WAS_REPORT_GENERATION")

    parser = argparse.ArgumentParser(
        description="Generate WAS reports for stakeholders whose schedule is due."
    )
    parser.add_argument(
        "--config-path",
        default=default_config_path,
        help="Path to was_config.txt inside the container.",
    )
    parser.add_argument(
        "--legacy-root",
        default=default_legacy_root,
        help="Directory containing WAS_report_creator.py and legacy assets.",
    )
    parser.add_argument(
        "--python-executable",
        default=sys.executable,
        help="Python executable used to run the legacy creator.",
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
        "--allow-unencrypted",
        action="store_true",
        help="Allow report generation without encryption when no password exists.",
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
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """Run scheduled WAS report generation."""
    logging.basicConfig(level=logging.INFO)
    args = parse_args(argv)
    failed_count = run_due_reports(
        config_path=args.config_path,
        legacy_root=args.legacy_root,
        python_executable=args.python_executable,
        current_epoch=args.current_epoch,
        create_missing_password=args.create_missing_password,
        allow_unencrypted=args.allow_unencrypted,
        include_manual=args.include_manual,
        include_retired=args.include_retired,
        limit=args.limit,
        continue_on_error=args.continue_on_error,
        output_directory=args.output_directory,
    )
    if failed_count:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
