"""CLI for emailing WAS reports through AWS SES."""

# Standard Python Libraries
import argparse
from datetime import date
import logging
from pathlib import Path
import sys
from typing import List, Optional

# Third-Party Libraries
# First-Party Libraries
from was_mailer.message import (
    build_assignee_digest_email,
    build_report_email,
    parse_email_addresses,
    recipient_addresses,
    unique_addresses,
)
from was_mailer.ses_client import create_ses_client
from was_reports.data.daily_report_tracker import (
    list_ready_assignee_digests_from_db,
    mark_assignee_digest_emailed,
    mark_assignee_digest_failed,
)
from was_reports.data.report_runs import (
    claim_report_run_email_by_id,
    get_report_run_email_by_id,
    list_report_runs_ready_for_email_from_db,
    mark_report_run_email_failed_by_id,
    mark_report_run_emailed_by_id,
)
from was_reports.storage.s3_reports import materialize_report
from was_reports.utils.env import getenv, require_env

LOGGER = logging.getLogger(__name__)


def require_environment_variable(name: str) -> str:
    """Return a required environment variable value."""
    return require_env(name)


def send_message(ses_client, message) -> str:
    """Send a raw email message through SES and return its message id."""
    response = ses_client.send_raw_email(RawMessage={"Data": message.as_bytes()})
    return response["MessageId"]


def send_report_run_email(
    report_run_id: int,
    source_email: str,
    override_recipients: Optional[str] = None,
    dry_run: bool = False,
    ses_client=None,
    s3_client=None,
    include_previous_failure: bool = False,
    storage_mode: Optional[str] = None,
    local_output_directory: Optional[str] = None,
) -> Optional[str]:
    """Send a completed WAS report run email."""
    if dry_run:
        report_run_email = get_report_run_email_by_id(report_run_id)
        delivery_claimed = False
    else:
        report_run_email = claim_report_run_email_by_id(
            report_run_id=report_run_id,
            include_previous_failure=include_previous_failure,
        )
        delivery_claimed = report_run_email is not None
        if report_run_email is None:
            raise RuntimeError(
                "WAS report run {} is not available for email delivery.".format(
                    report_run_id
                )
            )
    recipients = recipient_addresses(
        report_run_email=report_run_email,
        override_recipients=override_recipients,
    )
    delivery_accepted = False
    try:
        with materialize_report(
            report_reference=report_run_email.output_path,
            s3_client=s3_client,
            storage_mode=storage_mode,
            expected_local_root=(
                None if local_output_directory is None else Path(local_output_directory)
            ),
        ) as report_path:
            message = build_report_email(
                source_email=source_email,
                recipients=recipients,
                stakeholder_tag=report_run_email.stakeholder_tag,
                report_path=report_path,
            )

        if dry_run:
            LOGGER.info(
                "Dry run enabled; WAS report email for run id %s was not sent.",
                report_run_id,
            )
            return None

        if ses_client is not None:
            client = ses_client
        else:
            client = create_ses_client()
        message_id = send_message(client, message)
        delivery_accepted = True
        mark_report_run_emailed_by_id(report_run_id, message_id)
        return message_id
    except Exception:
        if delivery_claimed and not delivery_accepted:
            try:
                mark_report_run_email_failed_by_id(
                    report_run_id=report_run_id,
                    error_message="WAS report email delivery failed.",
                )
            except Exception:
                LOGGER.exception(
                    "Unable to persist WAS report email failure for run id %s",
                    report_run_id,
                )
        elif delivery_accepted:
            LOGGER.critical(
                "SES accepted WAS report run id %s, but delivery status could not "
                "be persisted; manual reconciliation is required.",
                report_run_id,
            )
        LOGGER.exception(
            "WAS report email delivery failed for report run id %s",
            report_run_id,
        )
        raise


def send_assignee_digest_email(
    assignee_digest,
    source_email: str,
    override_recipients: Optional[str] = None,
    dry_run: bool = False,
    ses_client=None,
) -> Optional[str]:
    """Send one WAS daily tracker assignee digest email."""
    if override_recipients:
        recipients = unique_addresses(parse_email_addresses(override_recipients))
    else:
        recipients = unique_addresses(parse_email_addresses(assignee_digest.email))

    message = build_assignee_digest_email(
        source_email=source_email,
        recipients=recipients,
        assignee_digest=assignee_digest,
    )

    if dry_run:
        LOGGER.info(
            "Dry run enabled; WAS assignee digest for assignee id %s was not sent.",
            assignee_digest.assignee_id,
        )
        return None

    try:
        if ses_client is not None:
            client = ses_client
        else:
            client = create_ses_client()
        message_id = send_message(client, message)
        mark_assignee_digest_success_for_dates(assignee_digest, message_id)
        return message_id
    except Exception as error:
        mark_assignee_digest_failure_for_dates(
            assignee_digest=assignee_digest,
            error_message="WAS assignee digest email delivery failed.",
        )
        LOGGER.exception(
            "WAS assignee digest email delivery failed for assignee id %s",
            assignee_digest.assignee_id,
        )
        raise error


def mark_assignee_digest_success_for_dates(assignee_digest, message_id: str) -> None:
    """Mark all pull dates in one assignee digest as emailed."""
    # Third-Party Libraries
    from was_reports.utils.database import close, connect

    pull_dates = unique_digest_dates(assignee_digest)
    conn = connect()
    try:
        for pull_date in pull_dates:
            mark_assignee_digest_emailed(
                conn=conn,
                assignee_id=assignee_digest.assignee_id,
                data_pull_date=pull_date,
                message_id=message_id,
            )
    finally:
        close(conn)


def mark_assignee_digest_failure_for_dates(
    assignee_digest,
    error_message: str,
) -> None:
    """Mark all pull dates in one assignee digest with email failure."""
    # Third-Party Libraries
    from was_reports.utils.database import close, connect

    pull_dates = unique_digest_dates(assignee_digest)
    conn = connect()
    try:
        for pull_date in pull_dates:
            mark_assignee_digest_failed(
                conn=conn,
                assignee_id=assignee_digest.assignee_id,
                data_pull_date=pull_date,
                error_message=error_message,
            )
    finally:
        close(conn)


def unique_digest_dates(assignee_digest) -> List[date]:
    """Return unique data pull dates for one assignee digest."""
    pull_dates = []
    seen_dates = set()
    for tracker_row in assignee_digest.rows:
        if tracker_row.data_pull_date is None:
            continue
        if tracker_row.data_pull_date in seen_dates:
            continue
        seen_dates.add(tracker_row.data_pull_date)
        pull_dates.append(tracker_row.data_pull_date)
    return pull_dates


def send_ready_report_emails(
    source_email: str,
    override_recipients: Optional[str] = None,
    dry_run: bool = False,
    limit: Optional[int] = None,
    include_previous_failures: bool = False,
    stakeholder_tag: Optional[str] = None,
) -> int:
    """Send all completed WAS report runs that are ready for email delivery."""
    report_runs = list_report_runs_ready_for_email_from_db(
        limit=limit,
        include_previous_failures=include_previous_failures,
        stakeholder_tag=stakeholder_tag,
    )
    sent_count = 0

    for report_run in report_runs:
        message_id = send_report_run_email(
            report_run_id=report_run.id,
            source_email=source_email,
            override_recipients=override_recipients,
            dry_run=dry_run,
            include_previous_failure=include_previous_failures,
        )
        if message_id or dry_run:
            sent_count += 1

    return sent_count


def send_ready_assignee_digests(
    source_email: str,
    override_recipients: Optional[str] = None,
    dry_run: bool = False,
    data_pull_date: Optional[date] = None,
    limit: Optional[int] = None,
) -> int:
    """Send ready WAS daily tracker assignee digests through SES."""
    digests = list_ready_assignee_digests_from_db(
        data_pull_date=data_pull_date,
        limit=limit,
    )
    sent_count = 0

    for digest in digests:
        message_id = send_assignee_digest_email(
            assignee_digest=digest,
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
    run_selection.add_argument(
        "--assignee-digests",
        action="store_true",
        help="Email daily tracker assignment digests to assignees.",
    )
    parser.add_argument(
        "--source-email",
        default=getenv("WAS_EMAIL_SOURCE"),
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
    parser.add_argument(
        "--data-pull-date",
        type=date.fromisoformat,
        help="Tracker pull date for assignee digests, formatted YYYY-MM-DD.",
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
    elif args.assignee_digests:
        send_ready_assignee_digests(
            source_email=source_email,
            override_recipients=args.test_recipients,
            dry_run=args.dry_run,
            data_pull_date=args.data_pull_date,
            limit=args.limit,
        )
    else:
        send_report_run_email(
            report_run_id=args.report_run_id,
            source_email=source_email,
            override_recipients=args.test_recipients,
            dry_run=args.dry_run,
            include_previous_failure=args.include_previous_failures,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
