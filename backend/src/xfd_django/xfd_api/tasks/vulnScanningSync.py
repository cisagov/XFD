"""Task for synchronizing vulnerability scanning data.

This module handles fetching, processing, and saving vulnerability scans,
port scans, hosts, and tickets from Redshift into the Django models.
"""

# Standard Python Libraries
from datetime import datetime, timezone
import logging
from logging import FileHandler
import os

# Third-Party Libraries
from xfd_api.tasks.ecs_client import ECSClient
from xfd_api.tasks.utils.datetime_utils import freeze_window
from xfd_api.tasks.utils.vs_tickets import fetch_tickets_from_redshift_single_org
from xfd_api.tasks.utils.vs_vuln_scans import (
    create_vuln_scan_summary,
    fetch_vuln_scans_from_redshift,
)
from xfd_api.utils.scan_utils.alerting import ScanExecutionError
from xfd_mini_dl.models import NMIServiceGroup, Organization, RiskyServiceGroup

LOGGER = logging.getLogger(__name__)

IS_LOCAL = os.getenv("IS_LOCAL")
SCAN_NAME = "VulnScanningSync"
VS_PULL_DATE_RANGE = os.getenv("VS_PULL_DATE_RANGE", "2")


def setup_vuln_sync_logging(
    filename: str = "/tmp/vuln_scanning_sync.log",  # nosec B108
    logger_name: str = "xfd",  # Use the main logger
) -> None:
    """Attach a file handler that reuses the unified formatter & filters. Runs once."""
    # Don't add twice
    if any(
        isinstance(handler, FileHandler)
        and getattr(handler, "baseFilename", "").endswith(filename)
        for handler in LOGGER.handlers
    ):
        return

    # Find a formatter to reuse: prefer a handler on the unified logger, else root
    def _find_formatter_and_filters():
        for current_logger in (logging.getLogger(logger_name), logging.getLogger()):
            for handler in current_logger.handlers:
                if handler.formatter:
                    return handler.formatter, list(handler.filters) or []
        # Fallback: no configured handlers yet
        return (
            logging.Formatter(
                "[%(asctime)s.%(msecs)03d] %(levelname)s "
                "[%(name)s:%(funcName)s:%(lineno)d] - %(message)s",
                "%Y-%m-%d %H:%M:%S",
            ),
            [],
        )

    formatter, filters = _find_formatter_and_filters()

    file_handler = FileHandler(filename)
    file_handler.setLevel(LOGGER.getEffectiveLevel())
    file_handler.setFormatter(formatter)
    for filter in filters:  # reuse any handler-level filters (e.g., redaction)
        file_handler.addFilter(filter)

    # Also inherit logger-level filters
    for filter in LOGGER.filters:
        file_handler.addFilter(filter)

    LOGGER.addHandler(file_handler)


def handler(event):
    """Handle execution of the vulnerability scanning sync task.

    This function serves as the entry point for triggering the synchronization
    process. It calls the `main` function and returns the appropriate response
    based on the execution outcome.

    Args:
        event (dict): The event data that triggers the function.

    Returns:
        dict: Response containing the status code and message.
    """
    LOGGER.info("VS_PULL_DATE_RANGE: %s", VS_PULL_DATE_RANGE)
    try:
        main(event)
        return {"status_code": 200, "body": "VS Sync completed successfully"}
    except Exception as e:
        LOGGER.exception("Error occurred: %s", e)
        raise ScanExecutionError(SCAN_NAME, str(e), event) from e


def main(event):  # pylint: disable=R0915
    """Execute the vulnerability scanning synchronization task."""
    setup_vuln_sync_logging()
    LOGGER.info("Started VulnScanningSync scan...")

    # Use fixed window + deterministic keyset on (time, _id)
    ps_start_dt = event.get("start_datetime")
    ps_end_dt = event.get("end_datetime")
    org_id = event.get("organizationId")
    org_name = event.get("organizationName")

    try:
        org = Organization.objects.get(id=org_id)
        acronym = org.acronym
    except Organization.DoesNotExist:
        LOGGER.warning("No acronym found for the org with the following id: %s", org_id)

    # Normalize start_datetime
    if isinstance(ps_start_dt, (int, float)):  # timestamp
        ps_start_dt = datetime.fromtimestamp(ps_start_dt, tz=timezone.utc)
    elif isinstance(ps_start_dt, str):  # ISO string
        ps_start_dt = datetime.fromisoformat(ps_start_dt).astimezone(timezone.utc)

    # Normalize end_timestamp
    if isinstance(ps_end_dt, (int, float)):  # timestamp
        ps_end_dt = datetime.fromtimestamp(ps_end_dt, tz=timezone.utc)
    elif isinstance(ps_end_dt, str):  # ISO string
        ps_end_dt = datetime.fromisoformat(ps_end_dt).astimezone(timezone.utc)

    # If either is missing, fallback to freeze_window
    if not (ps_start_dt and ps_end_dt):
        ps_start_dt, ps_end_dt = freeze_window(int(VS_PULL_DATE_RANGE))

    LOGGER.info("Frozen port-scan window: [%s .. %s]", ps_start_dt, ps_end_dt)

    LOGGER.info("Pulling VS data for %s: %s", org_name, acronym)

    # Process Port Scan in a separate workers
    # (vs_vuln_scan_worker.py) and (vs_port_scan_worker.py)
    task_arns = []
    ecs = ECSClient()
    port_scan_command_options = {
        "scanName": "vs_port_scan_worker",
        "organizationId": org_id,
        "organizationAcronym": acronym,
        "port_start_date": ps_start_dt,
        "port_end_date": ps_end_dt,
        "SERVICE_QUEUE_URL": os.getenv("SERVICE_QUEUE_URL"),
    }
    port_response = ecs.run_command(port_scan_command_options)
    tasks = port_response.get("tasks", [])
    for task in tasks:
        task_arns.append(task.get("taskArn"))

    # Start Vuln Scan in parallel
    try:
        fetch_vuln_scans_from_redshift(ps_start_dt, ps_end_dt, acronym, org_id)
    except Exception as e:
        LOGGER.exception("Vuln Scan error occurred: %s", e)
        raise ScanExecutionError(SCAN_NAME, str(e), event) from e

    if task_arns:
        ecs.wait_for_tasks_completion(
            task_arns,
            startup_delay=0,
            poll_interval=5,
            timeout=60 * 60 * 24,
        )

    LOGGER.info("Vuln and port scan syncs have completed for %s.", acronym)

    LOGGER.info("Prefetching risky and NMI service groups...")
    # Prefetch risky service groups
    risky_service_groups = {
        rsg.service_name: rsg.group for rsg in RiskyServiceGroup.objects.all()
    }

    # Prefetch NMI service groups
    nmi_service_groups = {
        nsg.service_name: nsg.group for nsg in NMIServiceGroup.objects.all()
    }

    # Process Tickets (Chunked)
    fetch_tickets_from_redshift_single_org(
        org_id,
        acronym,
        risky_service_groups,
        nmi_service_groups,
        ps_start_dt,
        ps_end_dt,
    )

    LOGGER.info("Ticket sync has completed for %s.", acronym)

    LOGGER.info("Creating vulnerability scan summary...")
    try:
        create_vuln_scan_summary(org_id=org_id)
        LOGGER.info("Finished vulnerability scan summary")
    except Exception as e:
        LOGGER.error(
            "Failed to create vulnerability scan summary: %s", e, exc_info=True
        )
    return {"status_code": 200, "body": "Vuln Scan Sync completed successfully"}
