"""Task for processing port scan data from Redshift.

This module handles fetching, processing, and saving port scans
from Redshift into the Django models. This will run in it's own container,
one organization at a time.
"""

# Standard Python Libraries
import logging

# Third-Party Libraries
from xfd_api.tasks.utils.vs_port_scans import (
    create_port_scan_summary,
    fetch_port_scans_from_redshift,
)
from xfd_api.utils.scan_utils.alerting import ScanExecutionError
from xfd_mini_dl.models import NMIServiceGroup, RiskyServiceGroup

LOGGER = logging.getLogger(__name__)

SCAN_NAME = "vs_port_scan_worker"


def handler(event):
    """
    Handle execution of the port scanning sync task for multiple organizations.

    Args:
        event (dict): The event data that triggers the function.
            Expected keys:
                - port_start_date
                - port_end_date
                - organizationMap: dict {acronym: org_id}

    Returns:
        dict: Response containing the status code and message.
    """
    try:
        start_dt = event.get("port_start_date")
        end_dt = event.get("port_end_date")
        org_id_dict = event.get("organizationMap", {})

        if not org_id_dict:
            LOGGER.warning("No organizations provided for port scan.")
            return {"status_code": 400, "body": "No organizations provided."}

        # Prefetch risky service groups
        risky_service_groups = {
            rsg.service_name: rsg.group for rsg in RiskyServiceGroup.objects.all()
        }

        # Prefetch NMI service groups
        nmi_service_groups = {
            nsg.service_name: nsg.group for nsg in NMIServiceGroup.objects.all()
        }

        # Fetch and process port scans for all orgs in one go
        fetch_port_scans_from_redshift(
            org_id_dict,
            risky_service_groups,
            nmi_service_groups,
            start_dt,
            end_dt,
        )

        # Create summaries with individual error handling
        LOGGER.info("Creating port scan summaries for all organizations...")
        try:
            for org_id in org_id_dict.values():
                create_port_scan_summary(org_id=org_id)
            LOGGER.info("Finished port scan summaries")
        except Exception as e:
            LOGGER.error("Failed to create port scan summaries: %s", e, exc_info=True)

        return {"status_code": 200, "body": "Port Scan Sync completed successfully"}

    except Exception as e:
        LOGGER.exception("Error occurred during port scan sync: %s", e)
        raise ScanExecutionError(SCAN_NAME, str(e), event) from e
