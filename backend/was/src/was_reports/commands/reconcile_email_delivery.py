"""Inspect or reconcile one held customer email delivery."""

# Standard Python Libraries
import argparse
import sys
from typing import Sequence

# First-Party Libraries
from was_mailer.email_reports import (
    reconciliation_recipient_scope,
    send_report_run_email,
)
from was_mailer.message import AnalystRecipientError, approved_analyst_recipients
from was_reports.data.report_runs import (
    HeldEmailReconciliationPreview,
    confirm_held_report_email_delivered_by_id,
    confirm_held_report_email_not_delivered_by_id,
    inspect_held_report_email_reconciliation_by_id,
)
from was_reports.utils.env import require_env
from was_reports.utils.logging_config import configure_logging

DELIVERY_CONFIRMED = "DELIVERY_CONFIRMED"
NONDELIVERY_CONFIRMED_RETRY = "NONDELIVERY_CONFIRMED_RETRY"
NONDELIVERY_CONFIRMED_RETRY_CUSTOMERS = (
    "NONDELIVERY_CONFIRMED_RETRY_CUSTOMERS"
)


def positive_integer(value: str) -> int:
    """Parse an integer greater than zero."""
    parsed_value = int(value)
    if parsed_value < 1:
        raise argparse.ArgumentTypeError("Value must be greater than zero.")
    return parsed_value


def _add_report_run_argument(parser: argparse.ArgumentParser) -> None:
    """Add the required report-run identifier to one subcommand."""
    parser.add_argument(
        "--report-run-id",
        required=True,
        type=positive_integer,
        help="Held customer report-run ID to inspect or reconcile.",
    )


def _add_mutation_arguments(parser: argparse.ArgumentParser) -> None:
    """Add evidence and explicit mutation confirmation arguments."""
    parser.add_argument(
        "--evidence-reference",
        required=True,
        help=(
            "Non-sensitive SES, mailbox, or ticket reference supporting the "
            "delivery decision."
        ),
    )
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse guarded delivery-reconciliation arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)

    inspect_command = subcommands.add_parser(
        "inspect",
        help="Read the current held-delivery state without changing it.",
    )
    _add_report_run_argument(inspect_command)

    delivered_command = subcommands.add_parser(
        "confirm-delivered",
        help="Record externally confirmed delivery without sending again.",
    )
    _add_report_run_argument(delivered_command)
    _add_mutation_arguments(delivered_command)

    retry_command = subcommands.add_parser(
        "retry-confirmed-undelivered",
        help=(
            "Record confirmed non-delivery and make one atomically claimed "
            "email attempt."
        ),
    )
    _add_report_run_argument(retry_command)
    _add_mutation_arguments(retry_command)
    retry_recipients = retry_command.add_mutually_exclusive_group(required=True)
    retry_recipients.add_argument(
        "--test-recipients",
        help="Override customer recipients with approved functional-test addresses.",
    )
    retry_recipients.add_argument(
        "--use-stored-customer-recipients",
        action="store_true",
        help="Send to the customer recipients stored for this report run.",
    )
    retry_command.add_argument(
        "--source-email",
        help="Verified SES sender. Defaults to WAS_EMAIL_SOURCE.",
    )
    return parser.parse_args(argv)


def _preview_text(preview: HeldEmailReconciliationPreview) -> str:
    """Return a secret-safe reconciliation preview."""
    eligibility = "eligible" if preview.eligible else "blocked"
    reason = ""
    if preview.ineligible_reason:
        reason = "; reason={}".format(preview.ineligible_reason.rstrip("."))
    return (
        "Run {run_id}: {eligibility}; tag={tag}; tracker={tracker}; "
        "report_status={report_status}; email_status={email_status}{reason}."
    ).format(
        run_id=preview.report_run_id,
        eligibility=eligibility,
        tag=preview.stakeholder_tag,
        tracker=preview.source_tracker_id or "not available",
        report_status=preview.report_status,
        email_status=preview.email_status,
        reason=reason,
    )


def _validated_test_recipients(value: str | None) -> str | None:
    """Return normalized approved functional-test recipients."""
    if value is None:
        return None
    try:
        return ",".join(approved_analyst_recipients(value))
    except AnalystRecipientError as error:
        raise ValueError(str(error)) from error


def _required_confirmation(arguments: argparse.Namespace) -> str:
    """Return the exact confirmation required for one requested action."""
    if arguments.command == "confirm-delivered":
        return DELIVERY_CONFIRMED
    if arguments.use_stored_customer_recipients:
        return NONDELIVERY_CONFIRMED_RETRY_CUSTOMERS
    return NONDELIVERY_CONFIRMED_RETRY


def _recipient_scope(
    test_recipients: str | None,
    use_stored_customer_recipients: bool,
) -> str:
    """Return a non-sensitive recipient scope bound to one retry."""
    if use_stored_customer_recipients:
        return reconciliation_recipient_scope(None)
    if test_recipients is None:
        raise ValueError("Approved test recipients are required.")
    return reconciliation_recipient_scope(test_recipients)


def main(argv: Sequence[str] | None = None) -> int:
    """Inspect or perform one guarded held-delivery reconciliation."""
    configure_logging()
    arguments = parse_args(argv)
    preview = inspect_held_report_email_reconciliation_by_id(
        arguments.report_run_id
    )
    print(_preview_text(preview))
    if arguments.command == "inspect":
        return 0 if preview.eligible else 2
    if not preview.eligible:
        print("Reconciliation blocked. No state was changed.", file=sys.stderr)
        return 2

    test_recipients = None
    if arguments.command == "retry-confirmed-undelivered":
        test_recipients = _validated_test_recipients(arguments.test_recipients)
    required_confirmation = _required_confirmation(arguments)
    if not arguments.apply:
        print(
            "Preview only. Apply with --apply --confirm {}.".format(
                required_confirmation
            )
        )
        return 0
    if arguments.confirm != required_confirmation:
        raise ValueError(
            "--apply requires --confirm {}.".format(required_confirmation)
        )

    if arguments.command == "confirm-delivered":
        confirm_held_report_email_delivered_by_id(
            report_run_id=arguments.report_run_id,
            reconciliation_reference=arguments.evidence_reference,
        )
        print(
            "Run {} was reconciled as delivered without sending another email.".format(
                arguments.report_run_id
            )
        )
        return 0

    source_email = arguments.source_email or require_env("WAS_EMAIL_SOURCE")
    recipient_scope = _recipient_scope(
        test_recipients,
        arguments.use_stored_customer_recipients,
    )
    reconciliation_token = confirm_held_report_email_not_delivered_by_id(
        report_run_id=arguments.report_run_id,
        reason=arguments.evidence_reference,
        recipient_scope=recipient_scope,
    )
    message_id = send_report_run_email(
        report_run_id=arguments.report_run_id,
        source_email=source_email,
        override_recipients=test_recipients,
        held_reconciliation_token=reconciliation_token,
        held_reconciliation_scope=recipient_scope,
        delivery_purpose="customer",
    )
    print(
        "Run {} retry was accepted by SES with message ID {}.".format(
            arguments.report_run_id,
            message_id,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
