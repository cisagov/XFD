"""Run Summary population methods via a scan."""  # Standard Python Libraries
# Standard Python Libraries
from datetime import timedelta
import logging
import os
import random

# Third-Party Libraries
from django.utils import timezone

LOGGER = logging.getLogger(__name__)
# Third-Party Libraries
from xfd_api.tasks.utils.vs_host_scans import create_daily_host_summary
from xfd_api.tasks.utils.vs_port_scans import create_port_scan_summary
from xfd_api.tasks.utils.vs_vuln_scans import create_vuln_scan_summary
from xfd_mini_dl.models import HostSummary, Organization

LOGGER = logging.getLogger(__name__)


def rebuild_org_id_dict(db_name="mini_data_lake"):
    """Rebuild a mapping from organization acronym to UUID."""
    return {
        org.acronym: str(org.id)
        for org in Organization.objects.using(db_name).all()
        if org.acronym  # defensive check
    }


def random_past_datetime(min_days: int, max_days: int) -> timezone.datetime:
    """Return a random datetime between `min_days` and `max_days` ago."""
    days_ago = random.randint(min_days, max_days)
    seconds = random.randint(0, 86400)  # random time within the day
    return timezone.now() - timedelta(days=days_ago, seconds=seconds)


def build_fake_host_summaries():
    """Build a fake Ticket for a pssed org."""
    all_orgs = Organization.objects.all()

    for org in all_orgs:
        try:
            summary_date = timezone.now().date()
            start_date = random_past_datetime(25, 60)
            end_date = random_past_datetime(1, 5)
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
                    "port_scan_min_timestamp": random_past_datetime(25, 60),
                    "port_scan_max_timestamp": random_past_datetime(1, 5),
                    "vuln_scan_min_timestamp": random_past_datetime(25, 60),
                    "vuln_scan_max_timestamp": random_past_datetime(1, 5),
                    "net_scan1_min_timestamp": random_past_datetime(25, 60),
                    "net_scan1_max_timestamp": random_past_datetime(1, 5),
                    "net_scan2_min_timestamp": random_past_datetime(25, 60),
                    "net_scan2_max_timestamp": random_past_datetime(1, 5),
                },
            )
        except Exception as e:
            LOGGER.error(
                "\n❌ Error while creating host_summary for org %s: %s", org.name, e
            )
            continue


def handler(event):
    """Retrieve and save NIST update alerts from the DMZ."""
    is_local_value = os.getenv("IS_LOCAL")
    is_local = str(is_local_value).lower() in ["1", "true"]
    LOGGER.info("IS_LOCAL equal %s", os.getenv("IS_LOCAL", "1"))
    try:
        # Deprecated with new flagging functionality in vs_port_scans
        # try:
        #     LOGGER.info("Flagging latest port scans.")
        #     enforce_latest_flag_port_scan()

        # except Exception as e:
        #     LOGGER.error("error flagging latest port scans: %s", e)
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

        # TODO: Not used yet but needs to be optimized (takes 12+ hours to complete)
        # try:
        #     LOGGER.info("Creating port service summaries.")
        #     create_port_scan_service_summaries()

        # except Exception as e:
        #     LOGGER.error("error saving port service summary: %s", e)

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
