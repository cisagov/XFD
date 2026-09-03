"""Application service for refreshing the WAS daily tracker."""

# Standard Python Libraries
import logging

# First-Party Libraries
from was_reports.data.special_cases import list_active_special_case_names
from was_reports.qualys.qualys_client import QualysClient
from was_reports.tracker.item_builder import create_tracker_items
from was_reports.tracker.qualys_scans import (
    search_scans,
    search_schedules,
    tracker_search_window,
)
from was_reports.tracker.update_service import update_tracker
from was_reports.utils.database import close, connect

LOGGER = logging.getLogger(__name__)


def active_no_deletion_tags() -> set[str]:
    """Return stakeholder tags exempt from inaccessible-app removal."""
    conn = connect()
    try:
        return set(list_active_special_case_names(conn))
    finally:
        close(conn)


def refresh_daily_tracker(
    client: QualysClient,
    delete_apps: bool = False,
    stakeholder_tag: str | None = None,
) -> int:
    """Refresh recent Qualys scan results into Postgres tracker rows."""
    input_date, previous_schedule_ids = tracker_search_window()
    stakeholders = search_schedules(
        client=client,
        input_date=input_date,
        previous_schedule_ids=previous_schedule_ids,
        stakeholder_tag=stakeholder_tag,
    )
    if not stakeholders:
        if stakeholder_tag:
            LOGGER.info(
                "No recent Qualys schedules found for stakeholder tag %s.",
                stakeholder_tag,
            )
        else:
            LOGGER.info("No recent Qualys schedules found.")
        return 0

    scan_groups = search_scans(
        client=client,
        stakeholders=stakeholders,
        input_date=input_date,
    )
    tracker_items = create_tracker_items(
        client=client,
        scan_groups=scan_groups,
        stakeholders=stakeholders,
        keep_nws_tags=active_no_deletion_tags(),
    )
    update_tracker(
        client=client,
        tracker_items=tracker_items,
        delete_apps=delete_apps,
    )
    LOGGER.info("Added %d rows to the WAS daily tracker.", len(tracker_items))
    return len(tracker_items)
