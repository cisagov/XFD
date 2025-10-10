"""Task for processing vuln scan data from Redshift.

This module handles fetching, processing, and saving vulnerability scans
from Redshift into the Django models. This will run in it's own container,
one organization at a time.
"""

# Standard Python Libraries
import logging

# Third-Party Libraries
from xfd_api.tasks.utils.vs_vuln_scans import fetch_vuln_scans_from_redshift
from xfd_api.utils.scan_utils.alerting import ScanExecutionError

LOGGER = logging.getLogger(__name__)

SCAN_NAME = "vs_vuln_scan_worker"


def handler(event):
    """Handle execution of the vulnerability scanning sync task.

    Args:
        event (dict): The event data that triggers the function.

    Returns:
        dict: Response containing the status code and message.
    """
    try:
        start_dt = event.get("vuln_start_date")
        end_dt = event.get("vuln_end_date")
        organization_id = event.get("organizationId")
        organization_acronym = event.get("organizationAcronym")
        fetch_vuln_scans_from_redshift(
            start_dt, end_dt, organization_acronym, organization_id
        )
    except Exception as e:
        LOGGER.exception("Error occurred: %s", e)
        raise ScanExecutionError(SCAN_NAME, str(e), event) from e
