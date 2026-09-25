"""Preview or execute isolated analyst-only report resends and manual retries."""

import argparse
from functools import partial
import logging
import sys
from uuid import UUID

from was_mailer.email_reports import send_report_run_email
from was_mailer.message import approved_analyst_recipients
from was_reports.commands.batch_runner import (
    DEFAULT_STAGING_DIRECTORY,
    generate_report_output,
    record_generation_failure,
    summarize_report_failure,
)
from was_reports.data.report_runs import (
    complete_report_run_by_id,
    touch_report_run_by_id,
)
from was_reports.data.test_replay import list_replay_candidates, reserve_replay_run
from was_reports.storage.s3_reports import resolve_storage_mode
from was_reports.utils.env import getenv, require_env
from was_reports.utils.logging_config import configure_logging
from was_reports.utils.operation_lease import operation_heartbeat
from was_reports.utils.operation_cancellation import (
    OperationCancelledError,
    raise_if_operation_cancelled,
)

LOGGER = logging.getLogger(__name__)


def tracker_ids(value: str) -> list[int]:
    """Parse an explicit, positive tracker allowlist without duplicates."""
    try:
        values = [int(part.strip()) for part in value.split(",")]
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "Use comma-separated positive tracker IDs."
        ) from error
    if not values or any(item <= 0 for item in values):
        raise argparse.ArgumentTypeError("Tracker IDs must be positive.")
    return list(dict.fromkeys(values))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Require deliberate recipient, manual selection, and apply identity."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days-back", type=int, default=7)
    parser.add_argument("--test-recipients", required=True)
    parser.add_argument("--manual-tracker-ids", type=tracker_ids, default=[])
    parser.add_argument(
        "--targets-removed-tracker-ids",
        type=tracker_ids,
        default=[],
        help=(
            "Explicit QUALYS DELETION REQUIRED rows to generate without deleting "
            "web applications and email as Targets Removed to test recipients."
        ),
    )
    parser.add_argument(
        "--report-run-ids",
        type=tracker_ids,
        default=[],
        help="Explicit existing PDF run IDs to resend after preview.",
    )
    parser.add_argument(
        "--replay-id", help="Stable UUID; reuse it to avoid duplicate sends."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Generate and send; default is read-only preview.",
    )
    parser.add_argument("--source-email")
    parser.add_argument(
        "--resource-root", default=getenv("WAS_RESOURCE_ROOT", "/WAS_REPORT_RESOURCES")
    )
    parser.add_argument(
        "--output-directory", default=getenv("WAS_OUTPUT_DIRECTORY", "/output")
    )
    parser.add_argument("--staging-directory", default=DEFAULT_STAGING_DIRECTORY)
    parser.add_argument("--storage-mode", choices=("local", "s3"))
    parser.add_argument("--python-executable", default=sys.executable)
    arguments = parser.parse_args(argv)
    if arguments.days_back <= 0:
        parser.error("--days-back must be positive.")
    if arguments.apply and not arguments.replay_id:
        parser.error("--apply requires a stable --replay-id UUID.")
    if arguments.apply and not (
        arguments.manual_tracker_ids
        or arguments.targets_removed_tracker_ids
        or arguments.report_run_ids
    ):
        parser.error(
            "--apply requires explicit report-run, manual-tracker, or Targets "
            "Removed tracker IDs."
        )
    if arguments.replay_id:
        try:
            arguments.replay_id = str(UUID(arguments.replay_id))
        except ValueError:
            parser.error("--replay-id must be a UUID.")
    return arguments


def execute_candidate(candidate, arguments: argparse.Namespace, recipient: str) -> bool:
    """Claim one isolated child and never retry an already reserved operation."""
    report_run, created = reserve_replay_run(arguments.replay_id, recipient, candidate)
    if not created:
        print(
            "Already reserved: tracker {} child run {}; skipping.".format(
                candidate.tracker_id, report_run.id
            )
        )
        return False
    if candidate.action in {"manual", "targets_removed"}:
        completion_attempted = False
        try:
            with operation_heartbeat(
                heartbeat=partial(
                    touch_report_run_by_id,
                    report_run.id,
                    generation_token=report_run.generation_token,
                ),
                operation_name="test replay {} generation".format(report_run.id),
            ):
                output_reference = generate_report_output(
                    report_run_id=report_run.id,
                    generation_token=report_run.generation_token,
                    stakeholder_tag=candidate.tag,
                    resource_root=arguments.resource_root,
                    python_executable=arguments.python_executable,
                    create_missing_password=False,
                    output_directory=arguments.output_directory,
                    storage_mode=resolve_storage_mode(arguments.storage_mode),
                    staging_directory=arguments.staging_directory,
                    tag_id=candidate.tag_id,
                    organization_name=candidate.organization_name,
                    allow_tag_lookup=False,
                )
            completion_attempted = True
            complete_report_run_by_id(
                report_run.id,
                generation_token=report_run.generation_token,
                output_path=output_reference,
                artifact_type="pdf",
            )
        except Exception as error:
            if not completion_attempted:
                record_generation_failure(
                    report_run, summarize_report_failure(error), error
                )
            raise
    raise_if_operation_cancelled()
    send_report_run_email(
        report_run_id=report_run.id,
        source_email=arguments.source_email or require_env("WAS_EMAIL_SOURCE"),
        override_recipients=recipient,
        delivery_purpose="analyst",
        preserve_customer_template=True,
        storage_mode=arguments.storage_mode,
        local_output_directory=arguments.output_directory,
    )
    return True


def main(argv: list[str] | None = None) -> int:
    """Preview first by default; application writes only isolated test records."""
    arguments = parse_args(argv)
    recipient = ",".join(approved_analyst_recipients(arguments.test_recipients))
    candidates = list_replay_candidates(
        days_back=arguments.days_back,
        manual_tracker_ids=arguments.manual_tracker_ids,
        include_all_manual=(
            not arguments.apply
            and not arguments.manual_tracker_ids
            and not arguments.targets_removed_tracker_ids
            and not arguments.report_run_ids
        ),
        targets_removed_tracker_ids=arguments.targets_removed_tracker_ids,
    )
    explicitly_selected = bool(
        arguments.report_run_ids
        or arguments.manual_tracker_ids
        or arguments.targets_removed_tracker_ids
    )
    if explicitly_selected:
        candidates = [
            candidate
            for candidate in candidates
            if (
                candidate.action == "manual"
                and candidate.tracker_id in arguments.manual_tracker_ids
            )
            or (
                candidate.action == "targets_removed"
                and candidate.tracker_id
                in arguments.targets_removed_tracker_ids
            )
            or (
                candidate.action == "resend"
                and candidate.original_run_id in arguments.report_run_ids
            )
        ]
    selected_runs = {
        candidate.original_run_id
        for candidate in candidates
        if candidate.action == "resend"
    }
    selected_manuals = {
        candidate.tracker_id for candidate in candidates if candidate.action == "manual"
    }
    selected_targets_removed = {
        candidate.tracker_id
        for candidate in candidates
        if candidate.action == "targets_removed"
    }
    if (
        set(arguments.report_run_ids) - selected_runs
        or set(arguments.manual_tracker_ids) - selected_manuals
        or set(arguments.targets_removed_tracker_ids) - selected_targets_removed
    ):
        raise ValueError(
            "Some explicitly selected IDs are outside the window or are not eligible. No replay work was reserved."
        )
    resend_count = sum(candidate.action == "resend" for candidate in candidates)
    manual_count = sum(candidate.action == "manual" for candidate in candidates)
    targets_removed_count = sum(
        candidate.action == "targets_removed" for candidate in candidates
    )
    print(
        "Test-only replay: {} existing PDFs; {} manual candidates; {} Targets "
        "Removed candidates. Apply requires explicit IDs.".format(
            resend_count, manual_count, targets_removed_count
        )
    )
    print(
        "Recipient: {}. Original tracker and delivery history remain unchanged.".format(
            recipient
        )
    )
    print(
        "Generated test reports use current Qualys data, not a guaranteed "
        "historical snapshot."
    )
    if targets_removed_count:
        print(
            "Targets Removed test mode does not delete Qualys web applications. "
            "It does create and clean up temporary Qualys report objects."
        )
    for candidate in candidates:
        print(
            "{}: tracker {} tag {} original run {}".format(
                candidate.action,
                candidate.tracker_id,
                candidate.tag,
                candidate.original_run_id,
            )
        )
    if not arguments.apply:
        print("Preview only: no database updates, generation, or emails.")
        return 0
    # Validate the sender before reserving any replay work.
    arguments.source_email = arguments.source_email or require_env("WAS_EMAIL_SOURCE")
    print(
        "Replay ID: {}. Save and reuse this ID for the same replay.".format(
            arguments.replay_id
        )
    )
    failures = 0
    for candidate in candidates:
        raise_if_operation_cancelled()
        try:
            execute_candidate(candidate, arguments, recipient)
        except OperationCancelledError:
            raise
        except Exception as error:
            failures += 1
            LOGGER.error(
                "Test replay tracker %s failed: %s. Inspect child run before retrying.",
                candidate.tracker_id,
                type(error).__name__,
            )
    return 1 if failures else 0


if __name__ == "__main__":
    configure_logging()
    raise SystemExit(main())
