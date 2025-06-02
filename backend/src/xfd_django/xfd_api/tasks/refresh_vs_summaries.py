"""Run Summary population methods via a scan."""  # Standard Python Libraries
# Standard Python Libraries
import logging
import os

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
LOGGER = logging.getLogger(__name__)
# Third-Party Libraries
from xfd_api.tasks.syncdb_helpers import build_fake_host_summaries
from xfd_api.tasks.vulnScanningSync import (
    create_daily_host_summary,
    create_port_scan_service_summaries,
    create_port_scan_summary,
    create_vuln_scan_summary,
    enforce_latest_flag_port_scan,
)
from xfd_mini_dl.models import Organization


def rebuild_org_id_dict(db_name="mini_data_lake"):
    """Rebuild a mapping from organization acronym to UUID."""
    return {
        org.acronym: str(org.id)
        for org in Organization.objects.using(db_name).all()
        if org.acronym  # defensive check
    }


def handler(event):
    """Retrieve and save NIST update alerts from the DMZ."""
    is_local_value = os.getenv("IS_LOCAL", "1")
    is_local = str(is_local_value).lower() in ["1", "true"] or is_local_value is True
    LOGGER.info("IS_LOCAL equal %s", os.getenv("IS_LOCAL", "1"))
    try:
        try:
            LOGGER.info("Flagging latest port scans.")
            enforce_latest_flag_port_scan()

        except Exception as e:
            LOGGER.error("error flagging latest port scans: %s", e)
        try:
            if not is_local:
                LOGGER.info("Creating Host summaries.")
                create_daily_host_summary(rebuild_org_id_dict())
            else:
                LOGGER.info("Creating Fake host summary for today.")
                build_fake_host_summaries()
        except Exception as e:
            LOGGER.error("error saving host summary: %s", e)

        try:
            LOGGER.info("Creating Port summaries.")
            create_port_scan_summary()

        except Exception as e:
            LOGGER.error("error saving Port summary: %s", e)
        try:
            LOGGER.info("Creating port service summaries.")
            create_port_scan_service_summaries()

        except Exception as e:
            LOGGER.error("error saving port service summary: %s", e)

        try:
            LOGGER.info("Creating VS summaries.")
            create_vuln_scan_summary()

        except Exception as e:
            LOGGER.error("error saving VS summary: %s", e)
        return {
            "statusCode": 200,
            "body": "DMZ NIST update completed successfully.",
        }
    except Exception as e:
        return {"statusCode": 500, "body": str(e)}
