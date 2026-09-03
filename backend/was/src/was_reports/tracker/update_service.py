"""Postgres-backed updates for the WAS daily report tracker."""

# Future Python Libraries
from __future__ import annotations

# Standard Python Libraries
from datetime import date, datetime, timezone
import logging
import time
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

# First-Party Libraries
from was_reports.data.assignees import (
    list_active_assignee_names,
    upsert_assignee,
)
from was_reports.data.daily_report_tracker import (
    DailyReportTrackerRow,
    insert_daily_report_tracker_row,
)
from was_reports.data.stakeholders import (
    StakeholderDetails,
    get_stakeholder_details,
    update_scan_metadata_for_tag,
)
from was_reports.qualys.qualys_admin import delete_webapp
from was_reports.qualys.qualys_client import QualysClient
from was_reports.qualys.report_data import count_webapps
from was_reports.tracker.assignments import round_robin_assignee
from was_reports.tracker.models import TrackerItem
from was_reports.utils.database import close, connect

if TYPE_CHECKING:
    # Third-Party Libraries
    from psycopg2.extensions import connection

LOGGER = logging.getLogger(__name__)
EASTERN_TIME = ZoneInfo("America/New_York")


def resolve_stakeholder_details(
    tag: str,
    conn: connection,
) -> StakeholderDetails | None:
    """Return stakeholder details for an exact or child tag."""
    stakeholder = get_stakeholder_details(tag, conn)
    if stakeholder is None and "_" in tag:
        stakeholder = get_stakeholder_details(tag.split("_", 1)[0], conn)
    return stakeholder


def combined_email_value(
    tech_poc_email: str | None,
    distro_email: str | None,
) -> str | None:
    """Return the combined tracker POC email field."""
    if tech_poc_email and distro_email:
        return "{}; {}".format(tech_poc_email, distro_email)
    return tech_poc_email or distro_email


def convert_qualys_date(scan_date: str) -> date:
    """Convert a Qualys UTC datetime string to an Eastern calendar date."""
    utc_datetime = datetime.strptime(
        scan_date,
        "%Y-%m-%dT%H:%M:%SZ",
    ).replace(tzinfo=timezone.utc)
    return utc_datetime.astimezone(EASTERN_TIME).date()


def tracker_result_fields(
    item: TrackerItem,
    num_apps: int,
    no_error: bool,
    report_scan_notes: str,
) -> tuple[str | None, str | None, str]:
    """Return the tracker NWS summary, template, and report notes."""
    template = None
    nws = None
    if item.nws:
        recent_count = len(item.recent_nws.split("<br>")) - 1
        removed_count = len(item.removed_nws.split("<br>")) - 1
        nws = "{}, {}, {}".format(num_apps, recent_count, removed_count)
        if num_apps == removed_count:
            if item.fceb:
                template = "FCEB All NWS"
            else:
                template = "Deactivated"
                report_scan_notes = "DEACTIVATE"
        elif num_apps == recent_count:
            template = "FCEB All NWS" if item.fceb else "All NWS"
        elif removed_count > 0:
            template = (
                "FCEB Action Required" if item.fceb else "Targets Removed"
            )
        else:
            template = (
                "FCEB Action Required" if item.fceb else "Action Required"
            )
    elif no_error and item.scan_name:
        nws = str(num_apps)
        template = "Results"
    return nws, template, report_scan_notes


def update_stakeholder_scan_metadata(
    tag: str,
    last_scan: str,
    next_scan: str,
    app_count: int,
) -> None:
    """Update stakeholder scan metadata while preserving tracker completion."""
    last_scan_datetime = datetime.strptime(
        last_scan,
        "%Y-%m-%dT%H:%M:%SZ",
    ).replace(tzinfo=timezone.utc)
    next_scan_datetime = datetime.strptime(
        next_scan,
        "%Y-%m-%dT%H:%M:%SZ",
    ).replace(tzinfo=timezone.utc)
    try:
        update_scan_metadata_for_tag(
            tag=tag,
            last_scanned=int(last_scan_datetime.timestamp()),
            next_scheduled=int(next_scan_datetime.timestamp()),
            num_web_apps=app_count,
            web_apps_last_updated=int(time.time()),
        )
    except Exception:
        LOGGER.exception(
            "Unable to update stakeholder scan metadata for %s",
            tag,
        )


def build_tracker_row(
    client: QualysClient,
    item: TrackerItem,
    assignee_name: str,
    conn: connection,
    data_pull_date: date,
) -> DailyReportTrackerRow:
    """Build one Postgres tracker row from a consolidated scan item."""
    stakeholder = resolve_stakeholder_details(item.tag, conn)
    no_error = stakeholder is not None
    report_scan_notes = item.manual
    if stakeholder is None:
        LOGGER.warning(
            "Stakeholder tag %s is absent from Postgres; marking it manual.",
            item.tag,
        )
        report_scan_notes = "MANUAL"

    try:
        num_apps = count_webapps(client, item.tag)
    except (AttributeError, LookupError, ValueError):
        num_apps = 0
        no_error = False
        report_scan_notes = "MANUAL"
        LOGGER.exception(
            "Unable to count Qualys web applications for %s; "
            "marking it manual.",
            item.tag,
        )

    nws, template, report_scan_notes = tracker_result_fields(
        item=item,
        num_apps=num_apps,
        no_error=no_error,
        report_scan_notes=report_scan_notes,
    )
    assignee = upsert_assignee(name=assignee_name, conn=conn)
    update_stakeholder_scan_metadata(
        tag=item.tag,
        last_scan=item.launched_date,
        next_scan=item.next_scan_date,
        app_count=num_apps,
    )

    return DailyReportTrackerRow(
        data_pull_date=data_pull_date,
        tag=item.tag,
        scan_name=item.scan_name,
        assignee_id=assignee.id,
        assignee=assignee.name,
        status=item.status,
        result=item.result,
        report_scan_notes=report_scan_notes,
        scan_start_date=convert_qualys_date(item.launched_date),
        next_scan_date=convert_qualys_date(item.next_scan_date),
        poc=stakeholder.was_report_poc if stakeholder else None,
        poc_email=(
            combined_email_value(
                stakeholder.tech_poc_email,
                stakeholder.distro_email,
            )
            if stakeholder
            else None
        ),
        customer_notes=stakeholder.comments if stakeholder else None,
        nws=nws,
        template=template,
        recent_nws=item.recent_nws,
        remove_nws=item.removed_nws,
        legacy_password=(
            "STATIC PASSWORD"
            if stakeholder and stakeholder.report_password
            else None
        ),
        schedule_id=item.schedule_id,
        qualys_error=item.qualys_errors,
    )


def active_assignees(conn: connection) -> list[str]:
    """Return active assignees, requiring at least one configured name."""
    assignees = list_active_assignee_names(conn)
    if not assignees:
        raise RuntimeError("No active WAS assignees are configured.")
    return assignees


def update_tracker(
    client: QualysClient,
    tracker_items: list[TrackerItem],
    delete_apps: bool,
    data_pull_date: date | None = None,
) -> None:
    """Write rows and optionally remove repeatedly inaccessible apps."""
    conn = connect()
    applications_to_delete: list[str] = []
    try:
        assignees = active_assignees(conn)
        effective_pull_date = data_pull_date or date.today()
        for item_index, item in enumerate(tracker_items):
            assignee_name = round_robin_assignee(assignees, item_index)
            tracker_row = build_tracker_row(
                client=client,
                item=item,
                assignee_name=assignee_name,
                conn=conn,
                data_pull_date=effective_pull_date,
            )
            insert_daily_report_tracker_row(row=tracker_row, conn=conn)
            if item.removed_nws and not item.fceb:
                applications_to_delete.extend(
                    app for app in item.removed_nws.split("<br>") if app
                )
    finally:
        close(conn)

    if not delete_apps:
        LOGGER.info("Qualys web application deletion is disabled.")
        return
    for webapp_url in applications_to_delete:
        delete_webapp(client, webapp_url)
