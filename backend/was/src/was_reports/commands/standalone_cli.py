"""Generate an explicitly requested report without enrolling a stakeholder."""

import argparse
from functools import partial
import logging
import sys

from was_mailer.email_reports import send_report_run_email
from was_mailer.message import AnalystRecipientError
from was_reports.commands.batch_runner import (
    generate_report_output,
    summarize_report_failure,
    DEFAULT_STAGING_DIRECTORY,
)
from was_reports.commands.report_generator import validate_stakeholder_tag
from was_reports.data.standalone_targets import (
    create_standalone_request,
    StandaloneTargetError,
)
from was_reports.data.report_runs import (
    ActiveReportOperationError,
    complete_report_run_by_id,
    fail_report_run_by_id,
    touch_report_run_by_id,
)
from was_reports.qualys.qualys_client import create_qualys_client
from was_reports.qualys.report_data import get_tag_details
from was_reports.reporting.latex_renderer import validate_filename_component
from was_reports.utils.qualys_config import load_qualys_credentials_from_environment
from was_reports.utils.env import getenv, require_env
from was_reports.utils.logging_config import configure_logging, exception_details
from was_reports.utils.operation_cancellation import (
    OperationCancelledError,
    raise_if_operation_cancelled,
)
from was_reports.utils.operation_lease import operation_heartbeat

LOGGER = logging.getLogger(__name__)


def run_standalone(args: argparse.Namespace) -> int:
    """Validate Qualys identity, claim, encrypt, archive, and optionally deliver."""
    tag = validate_stakeholder_tag(args.tag)
    validate_filename_component(tag)
    if len(tag) > 128:
        raise StandaloneTargetError("Qualys tag name must be at most 128 characters.")
    require_env("WAS_REPORTS_BUCKET_NAME")
    source = require_env("WAS_EMAIL_SOURCE") if args.send_email else None
    client = create_qualys_client(load_qualys_credentials_from_environment())
    try:
        details = get_tag_details(client, tag)
    except LookupError as error:
        raise StandaloneTargetError(
            "No unique matching Qualys tag was found. Verify the exact tag name."
        ) from error
    if details.name != tag:
        raise ValueError("Qualys did not return an exact tag-name match.")
    raise_if_operation_cancelled()
    request = create_standalone_request(tag, int(details.tag_id), args.delivery_email)
    run = request.run
    LOGGER.info(
        "Standalone report run %s created; no stakeholder or tracker row was created.",
        run.id,
    )
    try:
        with operation_heartbeat(
            partial(
                touch_report_run_by_id, run.id, generation_token=run.generation_token
            ),
            "standalone report generation",
        ):
            output = generate_report_output(
                report_run_id=run.id,
                generation_token=run.generation_token,
                stakeholder_tag=tag,
                resource_root=args.resource_root,
                python_executable=sys.executable,
                create_missing_password=False,
                output_directory="/output",
                storage_mode="s3",
                staging_directory=args.staging_directory,
                tag_id=int(details.tag_id),
                organization_name=details.description or tag,
                allow_tag_lookup=False,
                password_override=request.password,
            )
    except Exception as error:
        fail_report_run_by_id(
            run.id,
            summarize_report_failure(error),
            generation_token=run.generation_token,
        )
        raise
    # Completion errors must not mark an uploaded report failed and trigger regeneration.
    complete_report_run_by_id(
        run.id,
        output_path=output,
        artifact_type="pdf",
        generation_token=run.generation_token,
    )
    raise_if_operation_cancelled()
    if args.send_email:
        send_report_run_email(
            report_run_id=run.id,
            source_email=source,
            storage_mode="s3",
            delivery_purpose="standalone",
        )
    LOGGER.info("Standalone report run %s archived. Daily tracker unchanged.", run.id)
    return run.id


def main(argv: list[str] | None = None) -> int:
    """Explicit standalone entry point; never selected by daily batches."""
    configure_logging()
    parser = argparse.ArgumentParser(
        description="Report on a Qualys tag NOT enrolled as a WAS stakeholder."
    )
    parser.add_argument("--tag", required=True)
    parser.add_argument(
        "--delivery-email",
        help="Approved analyst email(s); required for a new target, omit to reuse saved address.",
    )
    parser.add_argument("--send-email", action="store_true")
    parser.add_argument(
        "--resource-root", default=getenv("WAS_RESOURCE_ROOT", "/WAS_REPORT_RESOURCES")
    )
    parser.add_argument(
        "--staging-directory",
        default=getenv("WAS_REPORT_STAGING_DIRECTORY", DEFAULT_STAGING_DIRECTORY),
    )
    args = parser.parse_args(argv)
    try:
        run_standalone(args)
    except OperationCancelledError:
        raise
    except (
        StandaloneTargetError,
        AnalystRecipientError,
        ActiveReportOperationError,
    ) as error:
        print("Standalone report not started: {}".format(error), file=sys.stderr)
        return 1
    except Exception as error:
        LOGGER.error(
            "Standalone report failed (%s). Inspect any recorded run before retrying.",
            exception_details(error),
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
