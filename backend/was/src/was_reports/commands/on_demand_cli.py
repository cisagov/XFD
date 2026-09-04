"""Generate, archive, and optionally email one explicit WAS report request."""

# Standard Python Libraries
import argparse
from email.headerregistry import Address
import logging
import sys

# Third-Party Libraries
from was_mailer.email_reports import send_report_run_email
from was_mailer.message import parse_email_addresses, unique_addresses
from was_reports.commands.batch_runner import (
    DEFAULT_STAGING_DIRECTORY,
    generate_report_output,
    summarize_report_failure,
)
from was_reports.commands.report_generator import validate_stakeholder_tag
from was_reports.data.report_runs import (
    complete_report_run_by_id,
    create_on_demand_report_run,
    fail_report_run_by_id,
)
from was_reports.data.stakeholders import get_stakeholder_details_by_tag
from was_reports.utils.env import getenv, require_env

LOGGER = logging.getLogger(__name__)


def validated_recipients(value: str) -> str:
    """Reject empty or malformed delivery overrides instead of falling back."""
    recipients = unique_addresses(parse_email_addresses(value))
    if not recipients:
        raise ValueError("At least one email recipient is required.")
    for recipient in recipients:
        address = Address(addr_spec=recipient)
        if not address.username or not address.domain:
            raise ValueError("Recipients must be complete email addresses.")
    return ",".join(recipients)


def run_on_demand(args: argparse.Namespace) -> int:
    """Run shared generation, S3 storage, and atomic email delivery services."""
    stakeholder_tag = validate_stakeholder_tag(args.tag)
    recipients = None
    source_email = None
    if args.send_email:
        source_email = require_env("WAS_EMAIL_SOURCE")
        if args.test_recipients is not None:
            recipients = validated_recipients(args.test_recipients)
        else:
            stakeholder = get_stakeholder_details_by_tag(stakeholder_tag)
            if stakeholder is None:
                raise ValueError("WAS stakeholder was not found.")
            recipients = validated_recipients(
                ",".join(
                    [stakeholder.tech_poc_email or "", stakeholder.distro_email or ""]
                )
            )
    require_env("WAS_REPORTS_BUCKET_NAME")
    report_run = create_on_demand_report_run(stakeholder_tag, args.tracker_id)
    LOGGER.info("Created on-demand WAS report run %s.", report_run.id)
    try:
        LOGGER.info(
            "Generating report and uploading to S3; Qualys may take several minutes."
        )
        output_reference = generate_report_output(
            report_run_id=report_run.id,
            stakeholder_tag=stakeholder_tag,
            resource_root=args.resource_root,
            python_executable=sys.executable,
            create_missing_password=args.create_missing_password,
            output_directory="/output",
            storage_mode="s3",
            staging_directory=args.staging_directory,
        )
    except Exception as error:
        fail_report_run_by_id(report_run.id, summarize_report_failure(error))
        raise
    try:
        complete_report_run_by_id(
            report_run.id, output_path=output_reference, artifact_type="pdf"
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
    recipients = parser.add_mutually_exclusive_group()
    recipients.add_argument("--test-recipients")
    recipients.add_argument("--stakeholder-recipients", action="store_true")
    parser.add_argument(
        "--resource-root", default=getenv("WAS_RESOURCE_ROOT", "/WAS_REPORT_RESOURCES")
    )
    parser.add_argument(
        "--staging-directory",
        default=getenv("WAS_REPORT_STAGING_DIRECTORY", DEFAULT_STAGING_DIRECTORY),
    )
    args = parser.parse_args(argv)
    has_recipients = args.test_recipients is not None or args.stakeholder_recipients
    if args.send_email != has_recipients:
        parser.error("Use --send-email together with exactly one recipient option.")
    if args.tracker_id is not None and args.tracker_id <= 0:
        parser.error("--tracker-id must be positive.")
    return args


def main(argv: list[str] | None = None) -> int:
    """Return a failure exit code without automatically repeating side effects."""
    logging.basicConfig(level=logging.INFO)
    args = parse_args(argv)
    try:
        run_on_demand(args)
    except Exception as error:
        LOGGER.error(
            "On-demand report failed (%s). Inspect its run before retrying.",
            type(error).__name__,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
