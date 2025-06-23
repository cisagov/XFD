"""Run Summary population methods via a scan."""  # Standard Python Libraries
# Standard Python Libraries
from datetime import timedelta
import logging
import os
import random

# Third-Party Libraries
from django.utils import timezone

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
LOGGER = logging.getLogger(__name__)
# Third-Party Libraries
from xfd_api.tasks.vulnScanningSync import (
    create_daily_host_summary,
    create_port_scan_service_summaries,
    create_port_scan_summary,
    create_vuln_scan_summary,
    enforce_latest_flag_port_scan,
)
from xfd_mini_dl.models import HostSummary, Organization


def rebuild_org_id_dict(db_name="mini_data_lake"):
    """Rebuild a mapping from organization acronym to UUID."""
    return {
        org.acronym: str(org.id)
        for org in Organization.objects.using(db_name).all()
        if org.acronym  # defensive check
    }


def build_fake_host_summaries():
    """Build a fake Ticket for a pssed org."""
    all_orgs = Organization.objects.all()

    for org in all_orgs:
        try:
            summary_date = timezone.now().date()
            start_date = timezone.now() - timedelta(
                days=random.randint(25, 60), seconds=random.randint(0, 86400)
            )
            end_date = timezone.now() - timedelta(
                days=random.randint(1, 5), seconds=random.randint(0, 86400)
            )
            host_done_count = random.randint(3000, 5000)
            host_waiting_count = random.randint(0, 50)
            host_running_count = random.randint(0, 50)
            host_ready_count = random.randint(0, 50)
            total_count = (
                host_done_count
                + host_waiting_count
                + host_running_count
                + host_ready_count
            )
            up_host_count = total_count - random.randint(0, 1500)
            down_host_count = total_count - up_host_count

            HostSummary.objects.update_or_create(
                organization=org,
                summary_date=summary_date,
                defaults={
                    "start_date": start_date,
                    "end_date": end_date,
                    "host_done_count": host_done_count,
                    "host_waiting_count": host_waiting_count,
                    "host_running_count": host_running_count,
                    "host_ready_count": host_ready_count,
                    "up_host_count": up_host_count,
                    "down_host_count": down_host_count,
                    "scanned_asset_count": total_count,
                },
            )
        except Exception as e:
            print("\n❌ Error while creating host_summary for org %s: %s", org.name, e)
            continue


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
