"""Task for synchronizing vulnerability organization data.

This module handles fetching, processing, and saving VS organizations,
and syncs with the DMZ environment.
"""

# Standard Python Libraries
import logging
import os

# Third-Party Libraries
from xfd_api.tasks.asm_sync import flag_cidr_changes
from xfd_api.tasks.utils.link_ips_to_cidrs import bulk_assign_ips_to_cidrs
from xfd_api.tasks.utils.mdl_insert_utils import fill_cidr_live_ips_bulk_update
from xfd_api.tasks.utils.vs_host_scans import create_daily_host_summary
from xfd_api.tasks.utils.vs_requests import fetch_orgs_from_databricks
from xfd_api.tasks.utils.vs_send_orgs_to_dmz import send_organizations_to_dmz
from xfd_api.utils.scan_utils.alerting import ScanExecutionError

LOGGER = logging.getLogger(__name__)

IS_LOCAL = os.getenv("IS_LOCAL")
SCAN_NAME = "vs_org_sync"


def handler(event):
    """Handle execution of the VS org sync task.

    Args:
        event (dict): The event data that triggers the function.

    Returns:
        dict: Response containing the status code and message.
    """
    try:
        main()
        return {"status_code": 200, "body": "VS Sync completed successfully"}
    except Exception as e:
        LOGGER.exception("Error occurred: %s", e)
        raise ScanExecutionError(SCAN_NAME, str(e), event) from e


def main():
    """Execute the vulnerability scanning synchronization task."""
    LOGGER.info("Started VS organization sync scan...")

    # Load request data
    org_id_dict = fetch_orgs_from_databricks()

    # Close unseen cidrs
    flag_cidr_changes()

    # Flag ips related to closed cidrs:
    bulk_assign_ips_to_cidrs()

    # Process Host Scans
    create_daily_host_summary(org_id_dict)

    # Fill CIDR live IPs
    fill_cidr_live_ips_bulk_update()

    # Send organizations to the DMZ MDL
    send_organizations_to_dmz()
