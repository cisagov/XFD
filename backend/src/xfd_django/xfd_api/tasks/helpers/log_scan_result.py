"""Helper function that upserts the timestamp of the latest result for each scan per organization."""
# Standard Python Libraries
import logging

# Third-Party Libraries
from django.utils import timezone
from xfd_mini_dl.models import ScanResult

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
LOGGER = logging.getLogger(__name__)


def log_scan_result(scan_id, organization_id, http_status=200, message=""):
    """Upsert timestamp of latest result saved for each organization per scan."""
    # Initialize scan and org variables for use in exception handling
    scan = scan_id
    org = organization_id
    try:
        ScanResult.objects.create(
            scan_id=scan_id,
            organization_id=organization_id,
            scanned_at=timezone.now(),
            http_status=http_status,
            message=message,
        )
        LOGGER.info(
            "Inserted scan result for scan: {}, organization: {}, http status: {} and message {}.".format(
                scan, org, http_status, message
            )
        )

    except Exception as e:
        LOGGER.error(
            "Error saving scan result for scan: {}, organization: {}, and http status: {} and message {}:\n{}".format(
                scan, org, http_status, message, str(e)
            )
        )
