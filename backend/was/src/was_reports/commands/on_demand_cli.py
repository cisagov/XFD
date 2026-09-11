"""Generate, archive, and optionally email one explicit WAS report request."""

# Standard Python Libraries
import argparse
from functools import partial
import logging
import sys

# Third-Party Libraries
from was_mailer.email_reports import send_report_run_email
from was_mailer.message import approved_analyst_recipients
from was_reports.commands.batch_runner import (
    DEFAULT_STAGING_DIRECTORY,
    generate_report_output,
    summarize_report_failure,
)
from was_reports.commands.report_generator import validate_stakeholder_tag
from was_reports.data.report_runs import (
    ActiveReportOperationError,
    complete_report_run_by_id,
    create_on_demand_report_run,
    fail_report_run_by_id,
    touch_report_run_by_id,
)
from was_reports.utils.env import getenv, require_env
from was_reports.utils.logging_config import configure_logging, exception_details
from was_reports.utils.operation_lease import operation_heartbeat

LOGGER = logging.getLogger(__name__)


def validated_recipients(value: str) -> str:
    """Require explicit recipients configured as active WAS assignees."""
    return ",".join(approved_analyst_recipients(value))


def run_on_demand(args: argparse.Namespace) -> int:
    """Run shared generation, S3 storage, and atomic email delivery services."""
    stakeholder_tag = validate_stakeholder_tag(args.tag)
    recipients = None
    source_email = None
    if args.send_email:
        source_email = require_env("WAS_EMAIL_SOURCE")
        recipients = validated_recipients(args.test_recipients)
    require_env("WAS_REPORTS_BUCKET_NAME")
    report_run = create_on_demand_report_run(stakeholder_tag, args.tracker_id)
    LOGGER.info("Created on-demand WAS report run %s.", report_run.id)
    try:
        LOGGER.info(
            "Generating report and uploading to S3; Qualys may take several minutes."
        )
        with operation_heartbeat(
            heartbeat=partial(
                touch_report_run_by_id,
                report_run.id,
                generation_token=report_run.generation_token,
            ),
            operation_name="report run {} generation".format(report_run.id),
        ):
            output_reference = generate_report_output(
                report_run_id=report_run.id,
                generation_token=report_run.generation_token,
                stakeholder_tag=stakeholder_tag,
                resource_root=args.resource_root,
                python_executable=sys.executable,
                create_missing_password=args.create_missing_password,
                output_directory="/output",
                storage_mode="s3",
                staging_directory=args.staging_directory,
            )
    except Exception as error:
        fail_report_run_by_id(
            report_run.id,
            summarize_report_failure(error),
            generation_token=report_run.generation_token,
        )
        raise
    try:
        complete_report_run_by_id(
            report_run.id,
            output_path=output_reference,
            artifact_type="pdf",
            generation_token=report_run.generation_token,
        )
    except Exception:
        LOGGER.error(
            "S3 upload succeeded for run %s but completion could not be recorded. "
            "Retain the artifact and reconcile the run before retrying.",
            report_run.id,
        )
        raise
    LOGGER.info("Report run %s archived at %s.", report_run.id, output_reference)
    if args.send_email:
        LOGGER.info(
            "Downloading archived report and sending run %s through SES.", report_run.id
        )
        message_id = send_report_run_email(
            report_run_id=report_run.id,
            source_email=source_email,
            override_recipients=recipients,
            storage_mode="s3",
            allow_held=True,
            delivery_purpose="analyst",
        )
        LOGGER.info("SES accepted run %s; message ID: %s.", report_run.id, message_id)
    if args.tracker_id is None:
        LOGGER.info(
            "Standalone report run: no scan tracker row was created or changed."
        )
    return report_run.id


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Require explicit delivery selection and a positive optional tracker ID."""
    parser = argparse.ArgumentParser(
        description="Generate and archive a new WAS report regardless of scan eligibility."
    )
    parser.add_argument("-t", "--tag", required=True)
    parser.add_argument("--create-missing-password", action="store_true")
    parser.add_argument("--tracker-id", type=int)
    parser.add_argument("--send-email", action="store_true")
    parser.add_argument(
        "--test-recipients",
        help="Explicit active WAS assignee recipients for on-demand delivery.",
    )
    parser.add_argument(
        "--resource-root", default=getenv("WAS_RESOURCE_ROOT", "/WAS_REPORT_RESOURCES")
    )
    parser.add_argument(
        "--staging-directory",
        default=getenv("WAS_REPORT_STAGING_DIRECTORY", DEFAULT_STAGING_DIRECTORY),
    )
    args = parser.parse_args(argv)
    has_recipients = args.test_recipients is not None
    if args.send_email != has_recipients:
        parser.error("Use --send-email together with exactly one recipient option.")
    if args.tracker_id is not None and args.tracker_id <= 0:
        parser.error("--tracker-id must be positive.")
    return args


def main(argv: list[str] | None = None) -> int:
    """Return a failure exit code without automatically repeating side effects."""
    configure_logging()
    args = parse_args(argv)
    try:
        run_on_demand(args)
    except ActiveReportOperationError as error:
        LOGGER.error("On-demand report not started: %s", exception_details(error))
        return 1
    except Exception as error:
        LOGGER.error(
            "On-demand report failed (%s). Inspect its run before retrying.",
            exception_details(error),
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
