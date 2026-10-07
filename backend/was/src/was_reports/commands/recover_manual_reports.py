"""Preview or recover explicitly selected, safely retryable manual failures."""

# Standard Python Libraries
import argparse
import sys
from typing import Sequence
from uuid import UUID

# Third-Party Libraries
# First-Party Libraries
from was_mailer.message import AnalystRecipientError, approved_analyst_recipients
from was_reports.commands.batch_runner import run_recent_scan_reports
from was_reports.commands.test_replay import main as run_test_replay
from was_reports.data.manual_recovery import (
    PASSWORD_VALIDATION,
    QUALYS_READ_TIMEOUT,
    RECOVERY_CAUSES,
    check_manual_report_recovery_by_id,
)
from was_reports.storage.s3_reports import S3_STORAGE
from was_reports.utils.env import getenv, require_env
from was_reports.utils.logging_config import configure_logging

CONFIRMATION = "RECOVER"


def tracker_ids(value: str) -> tuple[int, ...]:
    """Parse a unique, nonempty comma-separated tracker ID list."""
    parsed: list[int] = []
    for raw_value in value.split(","):
        normalized_value = raw_value.strip()
        if not normalized_value:
            raise argparse.ArgumentTypeError("Tracker IDs must not contain blanks.")
        try:
            tracker_id = int(normalized_value)
        except ValueError as error:
            raise argparse.ArgumentTypeError(
                "Tracker IDs must be positive integers."
            ) from error
        if tracker_id < 1:
            raise argparse.ArgumentTypeError("Tracker IDs must be positive integers.")
        if tracker_id in parsed:
            raise argparse.ArgumentTypeError("Tracker IDs must be unique.")
        parsed.append(tracker_id)
    return tuple(parsed)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse guarded manual-recovery arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Preview or recover explicit tracker failures caused only by an old "
            "password rule or a safe Qualys read timeout."
        )
    )
    parser.add_argument("--tracker-ids", required=True, type=tracker_ids)
    parser.add_argument(
        "--cause",
        required=True,
        choices=sorted(RECOVERY_CAUSES),
        help="Confirmed historical failure category shared by the selected rows.",
    )
    parser.add_argument("--days-back", type=int, default=7)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--confirm",
        help="Applying requires the exact value {}.".format(CONFIRMATION),
    )
    parser.add_argument(
        "--send-email",
        action="store_true",
        help="Deliver successfully regenerated reports and stamp tracker sent state.",
    )
    parser.add_argument(
        "--test-recipients",
        help=(
            "Generate an isolated analyst replay instead of changing customer "
            "recovery state."
        ),
    )
    parser.add_argument(
        "--replay-id",
        help="Stable UUID required for an applied test-recipient replay.",
    )
    parser.add_argument(
        "--resource-root",
        default=getenv("WAS_RESOURCE_ROOT", "/WAS_REPORT_RESOURCES"),
    )
    parser.add_argument(
        "--output-directory",
        default=getenv("WAS_OUTPUT_DIRECTORY", "/output"),
    )
    return parser.parse_args(argv)


def _validate_arguments(arguments: argparse.Namespace) -> str | None:
    """Validate deliberate mutation and recipient options."""
    if arguments.days_back < 1:
        raise ValueError("Days back must be at least 1.")
    if arguments.apply and arguments.confirm != CONFIRMATION:
        raise ValueError("--apply requires --confirm {}.".format(CONFIRMATION))
    if arguments.apply and not arguments.send_email:
        raise ValueError("--apply requires --send-email for complete recovery.")
    if not arguments.apply and (arguments.confirm or arguments.send_email):
        raise ValueError("--confirm and --send-email require --apply.")
    if arguments.replay_id and arguments.test_recipients is None:
        raise ValueError("--replay-id requires --test-recipients.")
    if arguments.apply and arguments.test_recipients and not arguments.replay_id:
        raise ValueError(
            "Applied test-recipient recovery requires a stable --replay-id UUID."
        )
    if arguments.replay_id:
        try:
            arguments.replay_id = str(UUID(arguments.replay_id))
        except ValueError as error:
            raise ValueError("--replay-id must be a UUID.") from error
    if arguments.test_recipients is None:
        return None
    try:
        return ",".join(approved_analyst_recipients(arguments.test_recipients))
    except AnalystRecipientError as error:
        raise ValueError(str(error)) from error


def main(argv: Sequence[str] | None = None) -> int:
    """Preview all selected rows, then recover them only after confirmation."""
    configure_logging()
    arguments = parse_args(argv)
    test_recipients = _validate_arguments(arguments)
    checks = [
        check_manual_report_recovery_by_id(
            tracker_id,
            arguments.cause,
            days_back=arguments.days_back,
        )
        for tracker_id in arguments.tracker_ids
    ]
    for check in checks:
        print(
            "Tracker {}: {}; tag={}; run={}; cause={}.".format(
                check.tracker_id,
                "eligible" if check.eligible else "blocked: {}".format(check.reason),
                check.tag or "not available",
                check.report_run_id or "not available",
                check.cause,
            )
        )
    blocked = [check for check in checks if not check.eligible]
    if blocked:
        print(
            "Recovery blocked. No selected rows were changed.",
            file=sys.stderr,
        )
        return 2
    if not arguments.apply:
        print(
            "Preview only. Re-run with --apply --confirm {} --send-email.".format(
                CONFIRMATION
            )
        )
        return 0

    source_email = require_env("WAS_EMAIL_SOURCE")
    if test_recipients is not None:
        return run_test_replay(
            [
                "--days-back",
                str(arguments.days_back),
                "--test-recipients",
                test_recipients,
                "--manual-tracker-ids",
                ",".join(str(value) for value in arguments.tracker_ids),
                "--replay-id",
                arguments.replay_id,
                "--apply",
                "--source-email",
                source_email,
                "--resource-root",
                arguments.resource_root,
                "--output-directory",
                arguments.output_directory,
                "--storage-mode",
                S3_STORAGE,
            ]
        )

    summary = run_recent_scan_reports(
        resource_root=arguments.resource_root,
        python_executable=sys.executable,
        output_directory=arguments.output_directory,
        storage_mode=S3_STORAGE,
        send_email=True,
        source_email=source_email,
        test_recipients=None,
        include_manual=True,
        continue_on_error=True,
        retry_ready_emails=False,
        days_back=arguments.days_back,
        recovery_causes={
            tracker_id: arguments.cause for tracker_id in arguments.tracker_ids
        },
    )
    print(
        "Recovery completed: selected={}; generated={}; sent={}; failed={}.".format(
            summary.candidates, summary.generated, summary.sent, summary.failed
        )
    )
    return 1 if summary.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "PASSWORD_VALIDATION",
    "QUALYS_READ_TIMEOUT",
    "main",
    "tracker_ids",
]
