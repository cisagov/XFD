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
    """Handle execution of the port scanning sync task.

    Args:
        event (dict): The event data that triggers the function.

    Returns:
        dict: Response containing the status code and message.
    """
    try:
        start_dt = event.get("port_start_date")
        end_dt = event.get("port_end_date")
        organization_id = event.get("organizationId")
        organization_acronym = event.get("organizationAcronym")

        # Prefetch risky service groups
        risky_service_groups = {
            rsg.service_name: rsg.group for rsg in RiskyServiceGroup.objects.all()
        }

        # Prefetch NMI service groups
        nmi_service_groups = {
            nsg.service_name: nsg.group for nsg in NMIServiceGroup.objects.all()
        }
        fetch_port_scans_from_redshift(
            organization_id,
            organization_acronym,
            risky_service_groups,
            nmi_service_groups,
            start_dt,
            end_dt,
        )
        # Create summaries with individual error handling
        LOGGER.info("Creating port scan summary...")
        try:
            create_port_scan_summary(org_id=organization_id)
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
        return {"status_code": 200, "body": "Port Scan Sync completed successfully"}
    except Exception as e:
        LOGGER.exception("Error occurred: %s", e)
        raise ScanExecutionError(SCAN_NAME, str(e), event) from e
