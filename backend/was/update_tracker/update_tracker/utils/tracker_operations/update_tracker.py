"""Postgres-backed daily WAS tracker updates."""

# Standard Python Libraries
from datetime import datetime, timezone

# Third-Party Libraries
import pytz

# First-Party Libraries
from data.search_customer_data import get_customer_data, get_dynamo_value
from data.special_reqs import ASSIGNEES
from data.update_customer_data import update_customer_data
from utils.tracker_operations.webapp_operations import delete_webapp, webapp_count
from was_reports.assignments import round_robin_assignee
from was_reports.data.assignees import upsert_assignee
from was_reports.data.daily_report_tracker import (
    DailyReportTrackerRow,
    insert_daily_report_tracker_row,
)
from was_reports.utils.database import close, connect

CURRENT_DAY = datetime.today().strftime("%m/%d/%y")
CURRENT_DAY = datetime.strptime(CURRENT_DAY, "%m/%d/%y").date()


def update_tracker(tracker_items, delete_apps):
    """Write WAS daily tracker rows to Postgres."""
    if not ASSIGNEES:
        raise RuntimeError("No active WAS assignees are configured.")

    apps_to_delete = []
    conn = connect()
    try:
        for item_index, item in enumerate(tracker_items):
            assignee_name = current_assignee_name(item_index)
            tracker_row = populate_row(item, assignee_name, conn)
            insert_daily_report_tracker_row(row=tracker_row, conn=conn)
            if item.removed_nws and not item.fceb:
                for app in item.removed_nws.split("<br>"):
                    if app:
                        apps_to_delete.append(app)
    finally:
        close(conn)

    if delete_apps:
        for webapp in apps_to_delete:
            delete_webapp(webapp)
    else:
        print("WEBAPP DELETION SET TO FALSE")


def current_assignee_name(item_index):
    """Return the current assignee name using round-robin distribution."""
    return round_robin_assignee(ASSIGNEES, item_index)


def populate_row(item, assignee_name, conn):
    """Build one Postgres tracker row from one legacy tracker item."""
    print("Adding {} to tracker".format(item.tag))
    no_error = True
    report_scan_notes = item.manual
    legacy_password = None
    poc = None
    poc_email = None
    customer_notes = None

    try:
        stakeholder = get_customer_data(item.tag)
        if get_dynamo_value(stakeholder, "Report Password"):
            legacy_password = "STATIC PASSWORD"
    except KeyError:
        print(
            "WARNING: possible naming error / typos. setting {} as manual".format(
                item.tag
            )
        )
        report_scan_notes = "MANUAL"
        no_error = False

    scan_start_date = convert_qualys_dt(item.launched_date)
    next_scan_date = convert_qualys_dt(item.next_scan_date)

    try:
        tech_poc_email = get_dynamo_value(stakeholder, "Tech POC Email")
        distro_email = get_dynamo_value(stakeholder, "Distro Email")
        poc = get_dynamo_value(stakeholder, "WAS Report POC")
        poc_email = combined_email_value(tech_poc_email, distro_email)
        customer_notes = get_dynamo_value(stakeholder, "Comments")
    except UnboundLocalError:
        print(
            "WARNING: possible naming error / typos. setting {} as manual".format(
                item.tag
            )
        )
        report_scan_notes = "MANUAL"
        no_error = False

    try:
        num_apps = webapp_count(item.tag)
    except AttributeError:
        num_apps = 0
        print(
            "WARNING: No webapps for {}. setting {} as manual".format(
                item.tag,
                item.tag,
            )
        )
        report_scan_notes = "MANUAL"
        no_error = False

    nws, template, report_scan_notes = tracker_result_fields(
        item=item,
        num_apps=num_apps,
        no_error=no_error,
        report_scan_notes=report_scan_notes,
    )
    assignee = upsert_assignee(name=assignee_name, conn=conn)
    update_customer_data(
        item.tag,
        item.launched_date,
        item.next_scan_date,
        num_apps,
    )

    return DailyReportTrackerRow(
        data_pull_date=CURRENT_DAY,
        tag=item.tag,
        scan_name=item.scan_name,
        assignee_id=assignee.id,
        assignee=assignee.name,
        status=item.status,
        result=item.result,
        report_scan_notes=report_scan_notes,
        scan_start_date=scan_start_date,
        next_scan_date=next_scan_date,
        poc=poc,
        poc_email=poc_email,
        customer_notes=customer_notes,
        nws=nws,
        template=template,
        recent_nws=item.recent_nws,
        remove_nws=item.removed_nws,
        legacy_password=legacy_password,
        schedule_id=int(item.schedule_id),
        qualys_error=item.qualys_errors,
    )


def combined_email_value(tech_poc_email, distro_email):
    """Return the legacy combined POC email field."""
    if tech_poc_email and distro_email:
        return "{}; {}".format(tech_poc_email, distro_email)
    return tech_poc_email or distro_email


def tracker_result_fields(item, num_apps, no_error, report_scan_notes):
    """Return the NWS, template, and notes values for a tracker row."""
    template = None
    nws = None
    if item.nws:
        recent = len(item.recent_nws.split("<br>")) - 1
        removed = len(item.removed_nws.split("<br>")) - 1
        nws = "{}, {}, {}".format(num_apps, recent, removed)
        if num_apps == removed:
            if item.fceb:
                template = "FCEB All NWS"
            else:
                template = "Deactivated"
                report_scan_notes = "DEACTIVATE"
        elif num_apps == recent:
            if item.fceb:
                template = "FCEB All NWS"
            else:
                template = "All NWS"
        elif removed > 0:
            if item.fceb:
                template = "FCEB Action Required"
            else:
                template = "Targets Removed"
        else:
            if item.fceb:
                template = "FCEB Action Required"
            else:
                template = "Action Required"
    elif no_error and item.scan_name:
        nws = str(num_apps)
        template = "Results"
    return nws, template, report_scan_notes


def convert_qualys_dt(scan_date):
    """Convert a Qualys UTC datetime string to an Eastern date."""
    scan_date = datetime.strptime(
        scan_date,
        "%Y-%m-%dT%H:%M:%SZ",
    ).replace(tzinfo=timezone.utc)

    tz = pytz.timezone("US/Eastern")
    scan_date_tz = scan_date.astimezone(tz)
    return scan_date_tz.date()
