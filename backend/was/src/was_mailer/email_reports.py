"""CLI for emailing WAS reports through AWS SES."""

# Standard Python Libraries
import argparse
import logging
import os
import sys
from pathlib import Path
from typing import List, Optional

# First-Party Libraries
from was_mailer.message import build_report_email, recipient_addresses
from was_reports.data.report_runs import (
    get_report_run_email_by_id,
    list_report_runs_ready_for_email_from_db,
    mark_report_run_email_failed_by_id,
    mark_report_run_emailed_by_id,
)

LOGGER = logging.getLogger(__name__)


def require_environment_variable(name: str) -> str:
    """Return a required environment variable value."""
    value = os.environ.get(name)
    if not value:
        raise RuntimeError("Missing required environment variable: {}".format(name))
    return value


def send_message(ses_client, message) -> str:
    """Send a raw email message through SES and return its message id."""
    response = ses_client.send_raw_email(
        RawMessage={"Data": message.as_bytes()}
    )
    return response["MessageId"]


def send_report_run_email(
    report_run_id: int,
    source_email: str,
    override_recipients: Optional[str] = None,
    dry_run: bool = False,
    ses_client=None,
) -> Optional[str]:
    """Send a completed WAS report run email."""
    report_run_email = get_report_run_email_by_id(report_run_id)
    recipients = recipient_addresses(
        report_run_email=report_run_email,
        override_recipients=override_recipients,
    )
    message = build_report_email(
        source_email=source_email,
        recipients=recipients,
        stakeholder_tag=report_run_email.stakeholder_tag,
        report_path=Path(report_run_email.output_path),
    )

    if dry_run:
        LOGGER.info(
            "Dry run enabled; WAS report email for run id %s was not sent.",
            report_run_id,
        )
        return None

    try:
        if ses_client is not None:
            client = ses_client
        else:
            import boto3

            client = boto3.client("ses")
        message_id = send_message(client, message)
        mark_report_run_emailed_by_id(report_run_id, message_id)
        return message_id
    except Exception as error:
        mark_report_run_email_failed_by_id(
            report_run_id=report_run_id,
            error_message="WAS report email delivery failed.",
        )
        LOGGER.exception(
            "WAS report email delivery failed for report run id %s",
            report_run_id,
        )
        raise error


def send_ready_report_emails(
    source_email: str,
    override_recipients: Optional[str] = None,
    dry_run: bool = False,
    limit: Optional[int] = None,
    include_previous_failures: bool = False,
) -> int:
    """Send all completed WAS report runs that are ready for email delivery."""
    report_runs = list_report_runs_ready_for_email_from_db(
        limit=limit,
        include_previous_failures=include_previous_failures,
    )
    sent_count = 0

    for report_run in report_runs:
        message_id = send_report_run_email(
            report_run_id=report_run.id,
            source_email=source_email,
            override_recipients=override_recipients,
            dry_run=dry_run,
        )
        if message_id or dry_run:
            sent_count += 1

    return sent_count


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse WAS mailer command line arguments."""
    parser = argparse.ArgumentParser(
        description="Email completed WAS report runs through AWS SES."
    )
    run_selection = parser.add_mutually_exclusive_group(required=True)
    run_selection.add_argument(
        "--report-run-id",
        type=int,
        help="Completed was_report_runs id to email.",
    )
    run_selection.add_argument(
        "--all-ready",
        action="store_true",
        help="Email all completed report runs that have not been emailed.",
    )
    parser.add_argument(
        "--source-email",
        default=os.environ.get("WAS_EMAIL_SOURCE"),
        help="Verified SES sender email address.",
    )
    parser.add_argument(
        "--test-recipients",
        help="Override report recipients with test addresses.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build the email but do not send through SES.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of ready report emails to send.",
    )
    parser.add_argument(
        "--include-previous-failures",
        action="store_true",
        help="Retry report runs with a previous email error.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """Run the WAS mailer CLI."""
    logging.basicConfig(level=logging.INFO)
    args = parse_args(argv)
    source_email = args.source_email
    if not source_email:
        source_email = require_environment_variable("WAS_EMAIL_SOURCE")

    if args.all_ready:
        send_ready_report_emails(
            source_email=source_email,
            override_recipients=args.test_recipients,
            dry_run=args.dry_run,
            limit=args.limit,
            include_previous_failures=args.include_previous_failures,
        )
    else:
        send_report_run_email(
            report_run_id=args.report_run_id,
            source_email=source_email,
            override_recipients=args.test_recipients,
            dry_run=args.dry_run,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
