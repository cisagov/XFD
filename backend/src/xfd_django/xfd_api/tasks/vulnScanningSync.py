"""Task for synchronizing vulnerability scanning data.

This module handles fetching, processing, and saving vulnerability scans,
port scans, hosts, and tickets from Redshift into the Django models.
"""

# Standard Python Libraries
import logging
from logging import FileHandler
import os

# Third-Party Libraries
from xfd_api.tasks.asm_sync import flag_cidr_changes
from xfd_api.tasks.refresh_material_views import handler as refresh_materialized_views
from xfd_api.tasks.syncdb_task import synchronize
from xfd_api.tasks.utils.datetime_utils import freeze_window
from xfd_api.tasks.utils.link_ips_to_cidrs import bulk_assign_ips_to_cidrs
from xfd_api.tasks.utils.mdl_insert_utils import fill_cidr_live_ips_bulk_update
from xfd_api.tasks.utils.vs_host_scans import create_daily_host_summary
from xfd_api.tasks.utils.vs_port_scans import (
    create_port_scan_summary,
    fetch_port_scans_from_redshift,
)
from xfd_api.tasks.utils.vs_requests import fetch_orgs_from_redshift
from xfd_api.tasks.utils.vs_send_orgs_to_dmz import send_organizations_to_dmz
from xfd_api.tasks.utils.vs_tickets import fetch_tickets_from_redshift
from xfd_api.tasks.utils.vs_vuln_scans import (
    create_vuln_scan_summary,
    fetch_vuln_scans_from_redshift,
)
from xfd_api.utils.scan_utils.alerting import ScanExecutionError
from xfd_mini_dl.models import NMIServiceGroup, RiskyServiceGroup

LOGGER = logging.getLogger(__name__)

IS_LOCAL = os.getenv("IS_LOCAL")
SCAN_NAME = "VulnScanningSync"

VS_PULL_DATE_RANGE = os.getenv("VS_PULL_DATE_RANGE", "2")


def setup_vuln_sync_logging(
    filename: str = "vuln_scanning_sync.log",
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
        main()
        return {"status_code": 200, "body": "VS Sync completed successfully"}
    except Exception as e:
        LOGGER.exception("Error occurred: %s", e)
        raise ScanExecutionError(SCAN_NAME, str(e), event) from e


def main():  # pylint: disable=R0915
    """Execute the vulnerability scanning synchronization task."""
    setup_vuln_sync_logging()
    LOGGER.info("Started VulnScanningSync scan...")

    LOGGER.info("Running syncdb")
    synchronize(target_app_label="xfd_mini_dl")

    # Use fixed window + deterministic keyset on (time, _id)
    ps_start_dt, ps_end_dt = freeze_window(int(VS_PULL_DATE_RANGE))
    LOGGER.info("Frozen port-scan window: [%s .. %s)", ps_start_dt, ps_end_dt)

    # Load request data
    org_id_dict = fetch_orgs_from_redshift()
    # org_id_dict = fetch_org_id_dict_fast()

    # Close unseen cidrs
    flag_cidr_changes()

    # Flag ips related to closed cidrs:
    bulk_assign_ips_to_cidrs()

    # Process Vulnerability Scans
    fetch_vuln_scans_from_redshift(ps_start_dt, ps_end_dt, org_id_dict)

    # # Process Host Scans
    create_daily_host_summary(org_id_dict)

    LOGGER.info("Prefetching risky and NMI service groups...")
    # Prefetch risky service groups
    risky_service_groups = {
        rsg.service_name: rsg.group for rsg in RiskyServiceGroup.objects.all()
    }

    # Prefetch NMI service groups
    nmi_service_groups = {
        nsg.service_name: nsg.group for nsg in NMIServiceGroup.objects.all()
    }

    # Port Scans (Chunked)
    fetch_port_scans_from_redshift(
        org_id_dict, risky_service_groups, nmi_service_groups, ps_start_dt, ps_end_dt
    )

    # # Fill CIDR live IPs
    fill_cidr_live_ips_bulk_update()

    # # Send organizations to the DMZ MDL
    send_organizations_to_dmz()

    # Process Tickets (Chunked)
    fetch_tickets_from_redshift(
        org_id_dict, risky_service_groups, nmi_service_groups, ps_start_dt, ps_end_dt
    )

    # REFRESH MATERIALIZED VIEWS BEFORE CREATING SUMMARIES
    LOGGER.info("Refreshing materialized views before creating summaries...")
    # Create or refresh materialized views
    result = refresh_materialized_views({})
    LOGGER.info(result)
    LOGGER.info("Finished refreshing materialized views")

    # Create summaries with individual error handling
    LOGGER.info("Creating port scan summary...")
    try:
        create_port_scan_summary()
        LOGGER.info("Finished port scan summary")
    except Exception as e:
        LOGGER.error("Failed to create port scan summary: %s", e, exc_info=True)

    # TODO: Not used yet but needs to be optimized (takes 12+ hours to complete)
    # LOGGER.info("Creating port scan service summaries...")
    # try:
    #     create_port_scan_service_summaries()
    #     LOGGER.info("Finished port scan service summaries")
    # except Exception as e:
    #     LOGGER.error(
    #         "Failed to create port scan service summaries: %s", e, exc_info=True
    #     )

    LOGGER.info("Creating vulnerability scan summary...")
    try:
        create_vuln_scan_summary()
        LOGGER.info("Finished vulnerability scan summary")
    except Exception as e:
        LOGGER.error(
            "Failed to create vulnerability scan summary: %s", e, exc_info=True
        )
