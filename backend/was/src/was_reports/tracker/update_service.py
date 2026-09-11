"""Postgres-backed updates for the WAS daily report tracker."""

# Future Python Libraries
from __future__ import annotations

# Standard Python Libraries
from dataclasses import fields, replace
from datetime import date, datetime
import hashlib
import logging
import time
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

# Third-Party Libraries
from psycopg2 import sql

# First-Party Libraries
from was_reports.data.assignees import list_active_assignee_names, upsert_assignee
from was_reports.data.daily_report_tracker import (
    DailyReportTrackerRow,
    record_tracker_digest_failure,
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
from was_reports.tracker.models import TrackerItem, scheduled_execution_key
from was_reports.utils.database import close, connect
from was_reports.utils.logging_config import exception_details

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
    utc_datetime = datetime.fromisoformat(scan_date.replace("Z", "+00:00"))
    if utc_datetime.tzinfo is None:
        raise ValueError("Qualys timestamp must include a timezone.")
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
    if not no_error or item.manual or item.status != "Finished":
        return None, None, report_scan_notes or "MANUAL"
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
            template = "FCEB Action Required" if item.fceb else "Targets Removed"
        else:
            template = "FCEB Action Required" if item.fceb else "Action Required"
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
    last_scan_datetime = datetime.fromisoformat(last_scan.replace("Z", "+00:00"))
    next_scan_datetime = datetime.fromisoformat(next_scan.replace("Z", "+00:00"))
    if last_scan_datetime.tzinfo is None or next_scan_datetime.tzinfo is None:
        raise ValueError("Qualys timestamps must include a timezone.")
    try:
        update_scan_metadata_for_tag(
            tag=tag,
            last_scanned=int(last_scan_datetime.timestamp()),
            next_scheduled=int(next_scan_datetime.timestamp()),
            num_web_apps=app_count,
            web_apps_last_updated=int(time.time()),
        )
    except Exception as error:
        LOGGER.error(
            "Unable to update stakeholder scan metadata for %s: %s",
            tag,
            exception_details(error),
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
    except (AttributeError, LookupError, ValueError) as error:
        num_apps = 0
        no_error = False
        report_scan_notes = "MANUAL"
        LOGGER.error(
            "Unable to count Qualys web applications for %s; " "marking it manual: %s",
            item.tag,
            exception_details(error),
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
            "STATIC PASSWORD" if stakeholder and stakeholder.report_password else None
        ),
        schedule_id=item.schedule_id,
        qualys_error=item.qualys_errors,
        scan_execution_key=item.scan_execution_key
        or scheduled_execution_key(item.schedule_id, item.launched_date),
    )


def active_assignees(conn: connection) -> list[str]:
    """Return active assignees, requiring at least one configured name."""
    assignees = list_active_assignee_names(conn)
    if not assignees:
        raise RuntimeError("No active WAS assignees are configured.")
    return assignees


def has_legacy_execution_overlap(item: TrackerItem, conn: connection) -> bool:
    """Require reconciliation for day-only legacy execution identities.

    A matching schedule and Eastern scan day cannot prove which launch was
    recorded. Never fabricate a launch timestamp or automatically deliver a
    second report, even if multiple legitimate launches occurred that day.
    The scan day, not the historical pull day, determines the overlap.
    """
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1 FROM was_daily_report_tracker
                WHERE scan_execution_key IS NULL
                  AND schedule_id = %s
                  AND scan_start_date = %s
            )
            """,
            (item.schedule_id, convert_qualys_date(item.launched_date)),
        )
        return bool(cursor.fetchone()[0])


def update_tracker(
    client: QualysClient,
    tracker_items: list[TrackerItem],
    delete_apps: bool,
    data_pull_date: date | None = None,
) -> int:
    """Return committed inserted/updated executions, excluding skipped candidates."""
    eligible_items = []
    for item in tracker_items:
        if (
            item.status in {"Finished", "Error"}
            and item.result
            and item.result.upper() not in {"PROCESSING", "RUNNING"}
        ):
            eligible_items.append(item)
        else:
            LOGGER.warning(
                "Skipping incomplete tracker candidate for %s; "
                "execution remains unclaimed for a later refresh.",
                item.tag,
            )
    tracker_items = eligible_items
    if not tracker_items:
        return 0
    persisted_count = 0
    conn = connect()
    try:
        assignees = active_assignees(conn)
        effective_pull_date = data_pull_date or date.today()
        for item_index, item in enumerate(tracker_items):
            execution_key = scheduled_execution_key(
                item.schedule_id, item.launched_date
            )
            lock_key = int.from_bytes(
                hashlib.sha256(execution_key.encode()).digest()[:8],
                "big",
                signed=True,
            )
            with conn.cursor() as cursor:
                cursor.execute("SELECT pg_try_advisory_lock(%s)", (lock_key,))
                acquired = cursor.fetchone()[0]
            if not acquired:
                conn.rollback()
                LOGGER.info(
                    "Skipping tracker execution for %s; another refresh holds its lock.",
                    item.tag,
                )
                continue
            try:
                persisted_count += update_execution(
                    client,
                    item,
                    delete_apps,
                    effective_pull_date,
                    round_robin_assignee(assignees, item_index),
                    conn,
                    execution_key,
                )
            finally:
                conn.rollback()
                with conn.cursor() as cursor:
                    cursor.execute("SELECT pg_advisory_unlock(%s)", (lock_key,))
                conn.commit()
    finally:
        close(conn)
    return persisted_count


def update_execution(
    client: QualysClient,
    item: TrackerItem,
    delete_apps: bool,
    data_pull_date: date,
    assignee_name: str,
    conn: connection,
    execution_key: str,
) -> int:
    """Return one for a persisted execution, zero for a safely skipped claim."""
    claim_required_deletion = False
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT id, status, result, report_scan_notes FROM was_daily_report_tracker "
            "WHERE scan_execution_key = %s FOR UPDATE",
            (execution_key,),
        )
        existing = cursor.fetchone()
        if existing:
            row_id, status, result, notes = existing
            claim_required_deletion = (
                delete_apps and notes == "QUALYS DELETION REQUIRED"
            )
            if "DELETION" in (notes or "").upper() and not claim_required_deletion:
                return 0
            if (
                status in {"Finished", "Error"}
                and result
                and result.upper() not in {"RUNNING", "PROCESSING"}
                and not claim_required_deletion
            ):
                return 0
            cursor.execute(
                "SELECT EXISTS (SELECT 1 FROM was_report_runs WHERE source_tracker_id = %s) "
                "OR EXISTS (SELECT 1 FROM was_daily_report_tracker WHERE id = %s "
                "AND report_sent_date IS NOT NULL)",
                (row_id, row_id),
            )
            if cursor.fetchone()[0]:
                return 0
    if has_legacy_execution_overlap(item, conn):
        raise RuntimeError(
            "Legacy tracker execution overlaps; manual reconciliation is required."
        )
    row = build_tracker_row(client, item, assignee_name, conn, data_pull_date)
    row = replace(row, scan_execution_key=execution_key)
    applications = list(
        dict.fromkeys(app for app in item.removed_nws.split("<br>") if app)
    )
    permitted = bool(
        (not existing or claim_required_deletion)
        and applications
        and not item.fceb
        and delete_apps
        and item.status == "Finished"
        and not item.manual
        and row.report_scan_notes in {None, "", "DEACTIVATE"}
    )
    if claim_required_deletion and not permitted:
        return 0
    if applications and not item.fceb and not permitted:
        row = replace(
            row,
            template="Action Required",
            report_scan_notes="QUALYS DELETION REQUIRED",
        )
    preliminary = (
        replace(
            row,
            template=None,
            report_scan_notes="MANUAL QUALYS DELETION PENDING",
        )
        if permitted
        else row
    )
    column_names = [field.name for field in fields(preliminary) if field.name != "id"]
    with conn.cursor() as cursor:
        if existing:
            update_columns = (
                "scan_name",
                "status",
                "result",
                "report_scan_notes",
                "scan_start_date",
                "next_scan_date",
                "nws",
                "template",
                "recent_nws",
                "remove_nws",
                "qualys_error",
            )
            cursor.execute(
                sql.SQL(
                    "UPDATE was_daily_report_tracker SET {} WHERE id = %s "
                    "AND report_sent_date IS NULL "
                    "AND COALESCE(report_scan_notes, '') = %s "
                    "AND NOT EXISTS (SELECT 1 FROM was_report_runs "
                    "WHERE source_tracker_id = was_daily_report_tracker.id)"
                ).format(
                    sql.SQL(", ").join(
                        sql.SQL("{} = %s").format(sql.Identifier(name))
                        for name in update_columns
                    )
                ),
                [getattr(preliminary, name) for name in update_columns]
                + [row_id, notes or ""],
            )
            if cursor.rowcount == 0:
                conn.rollback()
                return 0
        else:
            cursor.execute(
                sql.SQL(
                    "INSERT INTO was_daily_report_tracker ({}) VALUES ({}) "
                    "ON CONFLICT (scan_execution_key) WHERE scan_execution_key IS NOT NULL "
                    "DO NOTHING RETURNING id"
                ).format(
                    sql.SQL(", ").join(map(sql.Identifier, column_names)),
                    sql.SQL(", ").join(sql.Placeholder() for name in column_names),
                ),
                [getattr(preliminary, name) for name in column_names],
            )
            inserted = cursor.fetchone()
            if inserted is None:
                conn.rollback()
                return 0
            row_id = inserted[0]
    conn.commit()
    if not permitted:
        return 1
    try:
        for webapp_url in applications:
            delete_webapp(client, webapp_url)
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE was_daily_report_tracker SET template = %s, report_scan_notes = %s "
                "WHERE id = %s AND report_scan_notes = %s",
                (
                    "Targets Removed",
                    "",
                    row_id,
                    "MANUAL QUALYS DELETION PENDING",
                ),
            )
            if cursor.rowcount != 1:
                raise RuntimeError(
                    "Tracker deletion claim changed; manual reconciliation is required."
                )
        conn.commit()
    except Exception as error:
        LOGGER.error(
            "Unable to complete tracker deletion for %s: %s",
            item.tag,
            exception_details(error),
        )
        conn.rollback()
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE was_daily_report_tracker SET template = NULL, report_scan_notes = %s "
                "WHERE id = %s AND report_scan_notes = %s",
                (
                    "MANUAL QUALYS DELETION FAILED",
                    row_id,
                    "MANUAL QUALYS DELETION PENDING",
                ),
            )
            failure_recorded = cursor.rowcount == 1
        if failure_recorded:
            record_tracker_digest_failure(row_id, conn)
        conn.commit()
        raise
    return 1
