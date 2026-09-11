"""CLI for emailing WAS reports through AWS SES."""

# Standard Python Libraries
import argparse
from contextlib import nullcontext
from datetime import date
from functools import partial
import logging
from pathlib import Path
import sys
from typing import List, Optional
from uuid import uuid4

# Third-Party Libraries
# First-Party Libraries
from was_mailer.message import (
    approved_analyst_recipients,
    build_assignee_digest_email,
    build_report_email,
    recipient_addresses,
)
from was_mailer.ses_client import create_ses_client
from was_reports.data.daily_report_tracker import (
    claim_assignee_digest_rows,
    finish_assignee_digest_rows,
    list_ready_assignee_digests_from_db,
)
from was_reports.data.report_runs import (
    claim_report_run_email_by_id,
    get_report_run_email_by_id,
    list_report_runs_ready_for_email_from_db,
    mark_report_run_email_failed_by_id,
    mark_report_run_emailed_by_id,
    recover_stale_report_operations_in_db,
    touch_report_email_claim_by_id,
)
from was_reports.storage.s3_reports import materialize_report
from was_reports.utils.env import getenv, require_env
from was_reports.utils.logging_config import configure_logging
from was_reports.utils.operation_lease import (
    check_operation_ownership,
    operation_heartbeat,
)

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
    allow_held: bool = False,
    delivery_purpose: str = "customer",
) -> Optional[str]:
    """Send a completed WAS report run email."""
    if dry_run:
        report_run_email = get_report_run_email_by_id(report_run_id)
        delivery_claimed = False
    else:
        report_run_email = claim_report_run_email_by_id(
            report_run_id=report_run_id,
            include_previous_failure=include_previous_failure,
            allow_held=allow_held,
            delivery_purpose=delivery_purpose,
        )
        delivery_claimed = report_run_email is not None
        if report_run_email is None:
            raise RuntimeError(
                "WAS report run {} is not available for email delivery.".format(
                    report_run_id
                )
            )
    delivery_accepted = False
    delivery_attempted = False
    try:
        recipients = recipient_addresses(
            report_run_email=report_run_email,
            override_recipients=override_recipients,
        )
        analyst_delivery = report_run_email.delivery_purpose == "analyst"
        heartbeat_context = nullcontext()
        if delivery_claimed:
            heartbeat_context = operation_heartbeat(
                heartbeat=partial(
                    touch_report_email_claim_by_id,
                    report_run_id,
                    email_claim_token=report_run_email.email_claim_token,
                ),
                operation_name="report run {} email".format(report_run_id),
            )
        with heartbeat_context:
            report_context = nullcontext(None)
            if report_run_email.output_path is not None:
                report_context = materialize_report(
                    report_reference=report_run_email.output_path,
                    s3_client=s3_client,
                    storage_mode=storage_mode,
                    expected_local_root=(
                        None
                        if local_output_directory is None
                        else Path(local_output_directory)
                    ),
                )
            with report_context as report_path:
                message = build_report_email(
                    source_email=source_email,
                    recipients=recipients,
                    stakeholder_tag=report_run_email.stakeholder_tag,
                    report_path=report_path,
                    template=(
                        "Results" if analyst_delivery else report_run_email.template
                    ),
                    assignee_name=report_run_email.assignee_name,
                    recent_nws=(
                        None if analyst_delivery else report_run_email.recent_nws
                    ),
                    remove_nws=(
                        None if analyst_delivery else report_run_email.remove_nws
                    ),
                    qualys_error=(
                        None if analyst_delivery else report_run_email.qualys_error
                    ),
                    last_scanned=report_run_email.last_scanned,
                    next_scheduled=report_run_email.next_scheduled,
                    analyst_delivery=analyst_delivery,
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
            check_operation_ownership()
            delivery_attempted = True
            message_id = send_message(client, message)
            delivery_accepted = True
        mark_report_run_emailed_by_id(
            report_run_id,
            message_id,
            email_claim_token=report_run_email.email_claim_token,
        )
        return message_id
    except Exception:
        if delivery_claimed:
            try:
                mark_report_run_email_failed_by_id(
                    report_run_id=report_run_id,
                    error_message="WAS report email delivery failed.",
                    email_claim_token=report_run_email.email_claim_token,
                    hold_for_manual_retry=(
                        delivery_attempted
                        or report_run_email.delivery_purpose == "analyst"
                        or allow_held
                    ),
                )
            except Exception:
                LOGGER.error(
                    "Unable to persist WAS report email failure for run id %s",
                    report_run_id,
                )
        if delivery_accepted:
            LOGGER.critical(
                "SES accepted WAS report run id %s, but delivery status could not "
                "be persisted; manual reconciliation is required.",
                report_run_id,
            )
        LOGGER.error(
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
    """Claim and finish exactly the rows included in one digest."""
    row_ids = [row.id for row in assignee_digest.rows]
    if not row_ids or any(row_id is None for row_id in row_ids):
        raise ValueError("Digest rows require persisted IDs.")
    token = str(uuid4())
    claimed = False
    attempted = False
    try:
        if not dry_run:
            claimed = claim_assignee_digest_rows(
                row_ids,
                token,
                expected_revisions={
                    row.id: row.digest_revision for row in assignee_digest.rows
                },
            )
            if not claimed:
                return None
        recipients = approved_analyst_recipients(
            assignee_digest.email
            if override_recipients is None
            else override_recipients
        )
        message = build_assignee_digest_email(
            source_email=source_email,
            recipients=recipients,
            assignee_digest=assignee_digest,
        )
        if dry_run:
            LOGGER.info(
                "Dry run enabled; assignee digest %s was not sent.",
                assignee_digest.assignee_id,
            )
            return None
        client = ses_client if ses_client is not None else create_ses_client()
        attempted = True
        message_id = send_message(client, message)
        finish_assignee_digest_rows(row_ids, token, message_id=message_id)
        return message_id
    except Exception:
        if claimed:
            try:
                finish_assignee_digest_rows(
                    row_ids,
                    token,
                    error_message="WAS assignee digest email delivery failed.",
                    uncertain=attempted,
                )
            except Exception:
                LOGGER.error(
                    "Unable to persist digest failure for assignee id %s; "
                    "manual reconciliation is required.",
                    assignee_digest.assignee_id,
                )
        LOGGER.error(
            "WAS assignee digest email delivery failed for assignee id %s.",
            assignee_digest.assignee_id,
        )
        raise


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
        try:
            message_id = send_report_run_email(
                report_run_id=report_run.id,
                source_email=source_email,
                override_recipients=override_recipients,
                dry_run=dry_run,
                include_previous_failure=include_previous_failures,
            )
        except Exception:
            LOGGER.error(
                "Report email failed for run id %s; continuing.", report_run.id
            )
            continue
        if message_id or dry_run:
            sent_count += 1

    return sent_count


def send_ready_assignee_digests(
    source_email: str,
    override_recipients: Optional[str] = None,
    dry_run: bool = False,
    data_pull_date: Optional[date] = None,
    limit: Optional[int] = None,
    include_previous_failures: bool = False,
) -> int:
    """Send ready WAS daily tracker assignee digests through SES."""
    digests = list_ready_assignee_digests_from_db(
        data_pull_date=data_pull_date,
        limit=limit,
        include_previous_failures=include_previous_failures,
    )
    sent_count = 0

    for digest in digests:
        try:
            message_id = send_assignee_digest_email(
                assignee_digest=digest,
                source_email=source_email,
                override_recipients=override_recipients,
                dry_run=dry_run,
            )
        except Exception:
            LOGGER.error(
                "Assignee digest failed for id %s; continuing.", digest.assignee_id
            )
            continue
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
        "--delivery-purpose",
        choices=("customer", "analyst"),
        default="customer",
        help="Persisted purpose required when claiming an individual report.",
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
    configure_logging()
    args = parse_args(argv)
    recover_stale_report_operations_in_db()
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
            include_previous_failures=args.include_previous_failures,
        )
    else:
        send_report_run_email(
            report_run_id=args.report_run_id,
            source_email=source_email,
            override_recipients=args.test_recipients,
            dry_run=args.dry_run,
            include_previous_failure=args.include_previous_failures,
            allow_held=True,
            delivery_purpose=args.delivery_purpose,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
