"""Qualys schedule and scan discovery for the WAS daily tracker."""

# Future Python Libraries
from __future__ import annotations

# Standard Python Libraries
from datetime import datetime, timedelta
import logging
import unicodedata

# Third-Party Libraries
from lxml import etree
from lxml.builder import E

# First-Party Libraries
from was_reports.data.daily_report_tracker import (
    latest_tracker_pull_date,
    recent_schedule_ids,
)
from was_reports.qualys.qualys_client import QualysClient, QualysRequest
from was_reports.qualys.report_data import get_tag_id
from was_reports.tracker.models import QualysScan, TrackerStakeholder
from was_reports.utils.database import close, connect

LOGGER = logging.getLogger(__name__)
SCHEDULE_RESULTS_LIMIT = 50
SCAN_RESULTS_LIMIT = 1000
TRACKER_LOOKBACK_HOURS = 48


def serialize_xml(root: etree._Element) -> str:
    """Serialize one Qualys XML request."""
    return etree.tostring(root, encoding="unicode")


def parse_xml(response_xml: str, operation: str) -> etree._Element:
    """Parse a Qualys XML response with a bounded error message."""
    try:
        return etree.fromstring(response_xml.encode("utf-8"))
    except etree.XMLSyntaxError as error:
        raise RuntimeError(
            "Qualys returned invalid XML during {}.".format(operation)
        ) from error


def response_has_more_records(root: etree._Element) -> bool:
    """Return whether a paginated Qualys response has another page."""
    value = root.findtext("hasMoreRecords")
    return bool(value and value.strip().lower() == "true")


def response_count(root: etree._Element) -> int:
    """Return the response item count reported by Qualys."""
    raw_count = root.findtext("count")
    if raw_count is None:
        return 0
    return int(raw_count)


def tracker_search_window() -> tuple[datetime, set[int]]:
    """Return the lookback timestamp and recorded schedule IDs."""
    conn = connect()
    try:
        input_date = latest_tracker_pull_date(conn) - timedelta(
            hours=TRACKER_LOOKBACK_HOURS
        )
        previous_ids = set(recent_schedule_ids(conn, input_date))
    finally:
        close(conn)
    return input_date, previous_ids


def normalize_schedule_name(schedule_name: str) -> str:
    """Normalize Unicode dashes and repeated separators in a schedule name."""
    normalized_characters = []
    for character in schedule_name:
        if unicodedata.category(character) == "Pd":
            normalized_characters.append("-")
        else:
            normalized_characters.append(character)
    normalized_name = "".join(normalized_characters)
    while "--" in normalized_name:
        normalized_name = normalized_name.replace("--", "-")
    while "  " in normalized_name:
        normalized_name = normalized_name.replace("  ", " ")
    return normalized_name.strip()


def parse_stakeholder_schedule_name(schedule_name: str) -> tuple[str, str]:
    """Return the stakeholder tag and name from a Qualys schedule name."""
    parts = normalize_schedule_name(schedule_name).split(" - ")
    if len(parts) < 3 or not parts[1].strip() or not parts[2].strip():
        raise ValueError(
            "Qualys schedule name does not contain a stakeholder tag and name."
        )
    return parts[1].strip(), parts[2].strip()


def base_stakeholder_tag(tag: str) -> str:
    """Return the primary stakeholder tag for an ad hoc child tag."""
    lowered_tag = tag.lower()
    marker_index = lowered_tag.find("_ad")
    if marker_index >= 0:
        return tag[:marker_index]
    if "_" in tag:
        return tag.split("_", 1)[0]
    return tag


def next_scan_date_for_adhoc(
    client: QualysClient,
    tag: str,
    stakeholder_name: str,
) -> str:
    """Return the next launch date from an ad hoc tag's primary schedule."""
    primary_tag = base_stakeholder_tag(tag)
    payload = serialize_xml(
        E.ServiceRequest(
            E.preferences(E.limitResults("1")),
            E.filters(
                E.Criteria("true", field="active", operator="EQUALS"),
                E.Criteria(
                    stakeholder_name,
                    field="name",
                    operator="CONTAINS",
                ),
                E.Criteria(primary_tag, field="name", operator="CONTAINS"),
            ),
        )
    )
    response_xml = client.request(
        QualysRequest(
            endpoint="/search/was/wasscanschedule",
            payload=payload,
            http_method="POST",
        )
    )
    root = parse_xml(response_xml, "ad hoc schedule lookup")
    next_launch_date = root.findtext("./data/WasScanSchedule/nextLaunchDate")
    if not next_launch_date:
        raise LookupError("Qualys did not return a primary next launch date.")
    return next_launch_date


def build_schedule_search_payload(input_date: datetime, offset: int) -> str:
    """Build the recent vulnerability schedule search request."""
    return serialize_xml(
        E.ServiceRequest(
            E.preferences(
                E.limitResults(str(SCHEDULE_RESULTS_LIMIT)),
                E.startFromOffset(str(offset)),
            ),
            E.filters(
                E.Criteria(
                    input_date.strftime("%Y-%m-%d"),
                    field="lastScan.launchedDate",
                    operator="GREATER",
                ),
                E.Criteria(
                    "RUNNING",
                    field="lastScan.status",
                    operator="NOT EQUALS",
                ),
                E.Criteria(
                    "VULNERABILITY",
                    field="type",
                    operator="EQUALS",
                ),
            ),
        )
    )


def search_schedules(
    client: QualysClient,
    input_date: datetime,
    previous_schedule_ids: set[int],
    stakeholder_tag: str | None = None,
) -> dict[str, TrackerStakeholder]:
    """Return recent Qualys schedules not already recorded in the tracker."""
    input_date_text = input_date.strftime("%Y-%m-%dT%H:%M:%SZ")
    LOGGER.info("Tracker schedule search starts after %s", input_date_text)
    stakeholders: dict[str, TrackerStakeholder] = {}
    offset = 1
    while True:
        LOGGER.info("Fetching Qualys schedules from offset %d", offset)
        response_xml = client.request(
            QualysRequest(
                endpoint="/search/was/wasscanschedule",
                payload=build_schedule_search_payload(input_date, offset),
                http_method="POST",
            )
        )
        root = parse_xml(response_xml, "schedule search")
        for schedule in root.findall("./data/WasScanSchedule"):
            schedule_id_text = schedule.findtext("id")
            schedule_name = schedule.findtext("name")
            if not schedule_id_text or not schedule_name:
                LOGGER.warning(
                    "Skipping an incomplete Qualys schedule record."
                )
                continue
            schedule_id = int(schedule_id_text)
            if schedule_id in previous_schedule_ids:
                LOGGER.info("Skipping duplicate schedule %s", schedule_name)
                continue
            tag, stakeholder_name = parse_stakeholder_schedule_name(
                schedule_name
            )
            if stakeholder_tag is not None and tag != stakeholder_tag:
                continue
            cadence = schedule.findtext("./scheduling/occurrenceType") or ""
            next_scan_date = schedule.findtext("nextLaunchDate")
            if not next_scan_date:
                next_scan_date = next_scan_date_for_adhoc(
                    client=client,
                    tag=tag,
                    stakeholder_name=stakeholder_name,
                )
            if tag not in stakeholders:
                stakeholders[tag] = TrackerStakeholder(
                    name=stakeholder_name,
                    tag_id=int(get_tag_id(client, tag)),
                    next_scan_date=next_scan_date,
                    launched_date=input_date_text,
                    schedule_id=schedule_id,
                    cadence=cadence,
                )
        count = response_count(root)
        if not response_has_more_records(root):
            break
        if count <= 0:
            raise RuntimeError(
                "Qualys schedule pagination did not advance from offset "
                "{}.".format(offset)
            )
        offset += count
    LOGGER.info(
        "Found %d tracker schedule candidates",
        len(stakeholders),
    )
    return stakeholders


def build_scan_search_payload(
    stakeholders: dict[str, TrackerStakeholder],
    input_date: datetime,
    offset: int,
) -> str:
    """Build the Qualys scan-slice search request."""
    tag_ids = ",".join(
        str(stakeholder.tag_id) for stakeholder in stakeholders.values()
    )
    return serialize_xml(
        E.ServiceRequest(
            E.preferences(
                E.limitResults(str(SCAN_RESULTS_LIMIT)),
                E.startFromOffset(str(offset)),
            ),
            E.filters(
                E.Criteria(
                    input_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    field="launchedDate",
                    operator="GREATER",
                ),
                E.Criteria(tag_ids, field="webApp.tags.id", operator="IN"),
            ),
        )
    )


def scan_matches_stakeholder(
    scan_name: str,
    tag: str,
    stakeholder: TrackerStakeholder,
) -> bool:
    """Return whether a Qualys scan name belongs to one stakeholder cadence."""
    lowered_name = scan_name.lower()
    if stakeholder.cadence == "DAILY" and "monthly" in lowered_name:
        return False
    adhoc_markers = ("adhoc", "ad-hoc", "ad_hoc")
    if stakeholder.cadence == "MONTHLY" and any(
        marker in lowered_name for marker in adhoc_markers
    ):
        return False
    return (
        " {} ".format(tag) in scan_name
        and " {} ".format(stakeholder.name) in scan_name
    )


def search_scans(
    client: QualysClient,
    stakeholders: dict[str, TrackerStakeholder],
    input_date: datetime,
) -> dict[str, list[QualysScan]]:
    """Return recent Qualys scan slices grouped by stakeholder tag."""
    if not stakeholders:
        return {}
    scan_groups: dict[str, list[QualysScan]] = {
        tag: [] for tag in stakeholders
    }
    offset = 1
    while True:
        response_xml = client.request(
            QualysRequest(
                endpoint="/search/was/wasscan",
                payload=build_scan_search_payload(
                    stakeholders=stakeholders,
                    input_date=input_date,
                    offset=offset,
                ),
                http_method="POST",
            )
        )
        root = parse_xml(response_xml, "scan search")
        for scan in root.findall("./data/WasScan"):
            scan_name = scan.findtext("name") or ""
            for tag, stakeholder_scans in scan_groups.items():
                if scan_matches_stakeholder(
                    scan_name=scan_name,
                    tag=tag,
                    stakeholder=stakeholders[tag],
                ):
                    stakeholder_scans.append(scan)
                    break
        count = response_count(root)
        if not response_has_more_records(root):
            break
        if count <= 0:
            raise RuntimeError(
                "Qualys scan pagination did not advance from offset "
                "{}.".format(offset)
            )
        offset += count
    LOGGER.info(
        "Finished grouping Qualys scans for %d stakeholders",
        len(scan_groups),
    )
    return dict(sorted(scan_groups.items(), reverse=True))


def build_previous_nws_payload(
    tag: str,
    stakeholder_name: str,
    previous_run: str,
    search_date: str,
    offset: int,
) -> str:
    """Build a request for inaccessible applications from a prior scan run."""
    return serialize_xml(
        E.ServiceRequest(
            E.preferences(
                E.limitResults(str(SCAN_RESULTS_LIMIT)),
                E.startFromOffset(str(offset)),
            ),
            E.filters(
                E.Criteria(
                    search_date,
                    field="launchedDate",
                    operator="LESSER",
                ),
                E.Criteria(tag, field="name", operator="CONTAINS"),
                E.Criteria(
                    stakeholder_name,
                    field="name",
                    operator="CONTAINS",
                ),
                E.Criteria(previous_run, field="name", operator="CONTAINS"),
            ),
        )
    )


def get_previous_nws(
    client: QualysClient,
    tag: str,
    stakeholder_name: str,
    previous_run: str,
    search_date: str,
) -> list[str]:
    """Return inaccessible web application URLs from a previous scan run."""
    previous_urls: list[str] = []
    offset = 1
    while True:
        response_xml = client.request(
            QualysRequest(
                endpoint="/search/was/wasscan",
                payload=build_previous_nws_payload(
                    tag=tag,
                    stakeholder_name=stakeholder_name,
                    previous_run=previous_run,
                    search_date=search_date,
                    offset=offset,
                ),
                http_method="POST",
            )
        )
        root = parse_xml(
            response_xml,
            "previous inaccessible application search",
        )
        for scan in root.findall("./data/WasScan"):
            if scan.findtext("status") == "ERROR":
                continue
            if scan.findtext("./summary/resultsStatus") == "NO_WEB_SERVICE":
                webapp_url = scan.findtext("./target/webApp/url")
                if webapp_url:
                    previous_urls.append(webapp_url)
        count = response_count(root)
        if not response_has_more_records(root):
            break
        if count <= 0:
            raise RuntimeError(
                "Qualys previous-scan pagination did not advance from offset "
                "{}.".format(offset)
            )
        offset += count
    return previous_urls
