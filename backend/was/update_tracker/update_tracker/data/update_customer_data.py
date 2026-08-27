"""Stakeholder scan metadata update helpers for the WAS tracker."""

# Standard Python Libraries
from datetime import datetime, timezone
import time

# First-Party Libraries
from was_reports.data.stakeholders import update_scan_metadata_for_tag


def update_customer_data(tag, last_scan, next_scan, app_count):
    """Update stakeholder scan dates and web app counts in Postgres."""
    last_scan_dt = datetime.strptime(
        last_scan,
        "%Y-%m-%dT%H:%M:%SZ",
    ).replace(tzinfo=timezone.utc)
    next_scan_dt = datetime.strptime(
        next_scan,
        "%Y-%m-%dT%H:%M:%SZ",
    ).replace(tzinfo=timezone.utc)

    try:
        update_scan_metadata_for_tag(
            tag=tag,
            last_scanned=int(last_scan_dt.timestamp()),
            next_scheduled=int(next_scan_dt.timestamp()),
            num_web_apps=app_count,
            web_apps_last_updated=int(time.time()),
        )
    except Exception:
        print("WARNING: Unable to update scan dates / app count for {}".format(tag))
