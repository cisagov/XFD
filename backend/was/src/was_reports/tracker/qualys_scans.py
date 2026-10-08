"""Qualys schedule and scan discovery for the WAS daily tracker."""

# Future Python Libraries
from __future__ import annotations

# Standard Python Libraries
from dataclasses import replace
from datetime import datetime, timedelta
import hashlib
import json
import logging
import unicodedata

# Third-Party Libraries
# lxml is required for namespace-aware XPath on bounded Qualys responses.
from lxml import etree  # nosec B410

# The builder creates trusted outbound XML with fixed element names.
from lxml.builder import E  # nosec B410
import requests

# First-Party Libraries
from was_reports.data.daily_report_tracker import (
    latest_tracker_pull_date,
    recent_schedule_ids,
)
from was_reports.qualys.qualys_client import QualysClient, QualysRequest
from was_reports.tracker.models import (
    MISSING_QUALYS_SCHEDULE_NOTE_PREFIX,
    QualysScan,
    TrackerItem,
    TrackerStakeholder,
    scan_time_bounds,
    scheduled_execution_key,
)
from was_reports.utils.database import close, connect

LOGGER = logging.getLogger(__name__)
SCHEDULE_RESULTS_LIMIT = 1000
SCAN_RESULTS_LIMIT = 1000
DEFAULT_TRACKER_LOOKBACK_DAYS = 3


def serialize_xml(root: etree._Element) -> str:
    """Serialize one Qualys XML request."""
    return etree.tostring(root, encoding="unicode")


def parse_xml(response_xml: str, operation: str) -> etree._Element:
    """Parse a Qualys XML response with a bounded error message."""
    try:
        parser = etree.XMLParser(
            resolve_entities=False,
            no_network=True,
            load_dtd=False,
            dtd_validation=False,
            attribute_defaults=False,
            huge_tree=False,
        )
        root = etree.fromstring(  # nosec B320
            response_xml.encode("utf-8"),
            parser=parser,
        )
        if root.getroottree().docinfo.doctype:
            raise RuntimeError(
                "Qualys returned invalid XML during {}.".format(operation)
            )
        return root
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


def tracker_search_window(
    lookback_days: int = DEFAULT_TRACKER_LOOKBACK_DAYS,
) -> tuple[datetime, set[int]]:
    """Return the lookback timestamp and recorded schedule IDs."""
    if lookback_days < 1:
        raise ValueError("Tracker lookback days must be at least 1.")
    conn = connect()
    try:
        conn.set_session(readonly=True)
        input_date = latest_tracker_pull_date(conn) - timedelta(days=lookback_days)
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


def schedule_tag_id(schedule: etree._Element) -> int:
    """Return the single included tag ID from a Qualys schedule response."""
    tag_ids: list[str] = []
    for path in (
        "./target/tags/included/tagList/list/Tag/id",
        "./target/tags/included/tagList/set/Tag/id",
        "./target/tags/included/tagList/Tag/id",
    ):
        tag_ids.extend(
            value.strip()
            for value in schedule.xpath("{}/text()".format(path))
            if value.strip()
        )
    unique_tag_ids = tuple(dict.fromkeys(tag_ids))
    if len(unique_tag_ids) != 1:
        raise LookupError("Qualys schedule must contain exactly one included tag ID.")
    return int(unique_tag_ids[0])


def schedule_field_note(fields: list[str]) -> str:
    """Describe absent or invalid schedule fields without response contents."""
    return MISSING_QUALYS_SCHEDULE_NOTE_PREFIX + ", ".join(dict.fromkeys(fields))


def schedule_review_key(schedule: etree._Element, schedule_id: int | None) -> str:
    """Identify review records from limited nonsecret schedule metadata."""
    if schedule_id is not None:
        return "schedule-review:{}".format(schedule_id)
    identity = tuple(
        (schedule.findtext(path) or "").strip()
        for path in ("name", "./lastScan/id", "./lastScan/launchedDate", "id")
    )
    digest = hashlib.sha256(
        json.dumps(identity, ensure_ascii=True).encode("utf-8")
    ).hexdigest()
    return "schedule-review:unidentified:{}".format(digest)


def schedule_review_item(
    schedule: etree._Element,
    schedule_id: int | None,
    tag: str,
    fields: list[str],
    next_scan_date: str | None,
    tag_id: int | None,
) -> TrackerItem:
    """Keep an unresolved schedule visible without inventing an execution."""
    return TrackerItem(
        tag=tag,
        scan_name=(
            schedule.findtext("./lastScan/name") or schedule.findtext("name") or ""
        ),
        status="Unknown",
        result="Unknown",
        launched_date=None,
        next_scan_date=next_scan_date,
        nws=False,
        recent_nws="",
        removed_nws="",
        manual=schedule_field_note(fields),
        fceb=False,
        schedule_id=schedule_id,
        qualys_errors=", ".join(dict.fromkeys(fields)),
        tag_id=tag_id,
        scan_execution_key=schedule_review_key(schedule, schedule_id),
    )


def valid_schedule_timestamp(value: str | None) -> bool:
    """Require an actual timezone-aware date before deriving execution identity."""
    if not value:
        return False
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return timestamp.tzinfo is not None
    except ValueError:
        return False


def recover_schedule_scan(
    client: QualysClient,
    schedule: etree._Element,
) -> etree._Element | None:
    """Retrieve only the scan explicitly identified by a schedule's lastScan."""
    identifier = (schedule.findtext("./lastScan/id") or "").strip()
    if not identifier.isascii() or not identifier.isdigit():
        return None
    try:
        response = client.request(
            QualysRequest(
                endpoint="/get/was/wasscan/{}".format(identifier), http_method="get"
            )
        )
        detail = parse_xml(response, "schedule scan detail").find("./data/WasScan")
        if detail is None or (detail.findtext("id") or "").strip() != identifier:
            return None
        if not valid_schedule_timestamp(detail.findtext("launchedDate")):
            return None
        return detail
    except (requests.RequestException, ValueError, RuntimeError, AttributeError):
        LOGGER.warning(
            "Unable to recover required Qualys schedule field: lastScan.launchedDate."
        )
        return None


def schedule_is_adhoc(schedule_name: str, tag: str) -> bool:
    """Limit primary schedule fallback to explicitly marked ad hoc schedules."""
    normalized_name = normalize_schedule_name(schedule_name).lower()
    name_marked = any(
        marker in normalized_name for marker in ("adhoc", "ad-hoc", "ad_hoc")
    )
    tag_suffix = tag.lower().partition("_ad")[2]
    tag_marked = "_ad" in tag.lower() and (
        not tag_suffix or tag_suffix.isdigit() or tag_suffix == "hoc"
    )
    return name_marked or tag_marked


def search_schedules(
    client: QualysClient,
    input_date: datetime,
    previous_schedule_ids: set[int],
    stakeholder_tag: str | None = None,
    discovery_issues: list[TrackerItem] | None = None,
) -> dict[str, TrackerStakeholder]:
    """Return executions and optionally retain unresolved schedule review rows."""
    input_date_text = input_date.strftime("%Y-%m-%dT%H:%M:%SZ")
    LOGGER.info("Tracker schedule search starts after %s", input_date_text)
    stakeholders: dict[str, TrackerStakeholder] = {}
    issue_keys: set[str] = set()
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
            last_scan_status = (
                (schedule.findtext("./lastScan/status") or "").strip().upper()
            )
            last_scan_result = (
                (schedule.findtext("./lastScan/summary/resultsStatus") or "")
                .strip()
                .upper()
            )
            if (
                last_scan_status in ("RUNNING", "PROCESSING")
                or last_scan_result == "PROCESSING"
            ):
                continue
            fields: list[str] = []
            identifier = (schedule.findtext("id") or "").strip()
            schedule_id = None
            if identifier.isascii() and identifier.isdigit():
                try:
                    schedule_id = int(identifier)
                except ValueError:
                    pass
            if schedule_id is None:
                fields.append("id")
            schedule_name = schedule.findtext("name") or ""
            tag = ""
            stakeholder_name = ""
            try:
                tag, stakeholder_name = parse_stakeholder_schedule_name(schedule_name)
            except ValueError:
                fields.append("name (stakeholder tag/name)")
            if stakeholder_tag is not None and tag != stakeholder_tag:
                continue
            tag_id = None
            try:
                tag_id = schedule_tag_id(schedule)
            except (LookupError, ValueError):
                fields.append("target.tags.included.tagList (single tag ID)")
            launched_date = schedule.findtext("./lastScan/launchedDate")
            latest_scan_name = schedule.findtext("./lastScan/name") or ""
            if not valid_schedule_timestamp(launched_date):
                detail = recover_schedule_scan(client, schedule)
                if detail is not None:
                    last_scan_status = (detail.findtext("status") or "").strip().upper()
                    detail_result = (
                        (detail.findtext("./summary/resultsStatus") or "")
                        .strip()
                        .upper()
                    )
                    if (
                        last_scan_status in ("RUNNING", "PROCESSING")
                        or detail_result == "PROCESSING"
                    ):
                        continue
                    launched_date = detail.findtext("launchedDate")
                    latest_scan_name = detail.findtext("name") or latest_scan_name
                else:
                    fields.append("lastScan.launchedDate")
            next_scan_date = schedule.findtext("nextLaunchDate")
            if not valid_schedule_timestamp(next_scan_date):
                next_scan_date = None
                if tag and schedule_is_adhoc(schedule_name, tag):
                    try:
                        recovered_next = next_scan_date_for_adhoc(
                            client, tag, stakeholder_name
                        )
                        if valid_schedule_timestamp(recovered_next):
                            next_scan_date = recovered_next
                    except (
                        LookupError,
                        requests.RequestException,
                        ValueError,
                        RuntimeError,
                        AttributeError,
                    ):
                        pass
                if next_scan_date is None:
                    fields.append("nextLaunchDate")
            if fields:
                LOGGER.warning(
                    "Qualys schedule %s requires manual review for fields: %s",
                    schedule_id,
                    ", ".join(fields),
                )
            required_execution_fields = [
                field for field in fields if field != "nextLaunchDate"
            ]
            if required_execution_fields:
                review_key = schedule_review_key(schedule, schedule_id)
                if discovery_issues is not None and review_key not in issue_keys:
                    discovery_issues.append(
                        schedule_review_item(
                            schedule,
                            schedule_id,
                            tag,
                            fields,
                            next_scan_date,
                            tag_id,
                        )
                    )
                    issue_keys.add(review_key)
                continue
            execution_key = scheduled_execution_key(schedule_id, launched_date)
            if execution_key not in stakeholders:
                stakeholders[execution_key] = TrackerStakeholder(
                    name=stakeholder_name,
                    tag_id=tag_id,
                    next_scan_date=next_scan_date,
                    launched_date=launched_date,
                    schedule_id=schedule_id,
                    cadence=schedule.findtext("./scheduling/occurrenceType") or "",
                    tag=tag,
                    schedule_name=normalize_schedule_name(schedule_name),
                    latest_scan_name=latest_scan_name,
                    latest_scan_status=last_scan_status,
                    discovery_notes=schedule_field_note(fields) if fields else "",
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
    LOGGER.info("Found %d tracker schedule candidates", len(stakeholders))
    return stakeholders


def build_scan_search_payload(
    tag_ids: tuple[int, ...],
    input_date: datetime,
    offset: int,
) -> str:
    """Build the Qualys scan-slice search request."""
    normalized_tag_ids = tuple(sorted(set(tag_ids)))
    if not normalized_tag_ids:
        raise ValueError("At least one Qualys tag ID is required for scan search.")
    tag_id_filter = ",".join(str(tag_id) for tag_id in normalized_tag_ids)
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
                E.Criteria(
                    tag_id_filter,
                    field="webApp.tags.id",
                    operator="IN",
                ),
                E.Criteria("VULNERABILITY", field="type", operator="EQUALS"),
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
        " {} ".format(tag) in scan_name and " {} ".format(stakeholder.name) in scan_name
    )


def execution_detail_bounds(
    client: QualysClient,
    scan: QualysScan,
) -> tuple[datetime | None, datetime | None]:
    """Fetch one completed parent/single scan's missing timing metadata safely."""
    start, end = scan_time_bounds([scan])
    identifier = (scan.findtext("id") or "").strip()
    if (
        end is not None
        or scan.findtext("status") != "FINISHED"
        or not identifier.isdigit()
    ):
        return start, end
    try:
        response = client.request(
            QualysRequest(
                endpoint="/get/was/wasscan/{}".format(identifier), http_method="get"
            )
        )
        root = parse_xml(response, "scan timing detail")
        detail = root.find("./data/WasScan")
        if detail is None or detail.findtext("id") != identifier:
            raise ValueError("Scan detail identity did not match.")
        detail_start, detail_end = scan_time_bounds([detail])
        if detail.findtext("status") != "FINISHED" or detail_start != start:
            raise ValueError("Scan detail status or launch did not match.")
        return detail_start, detail_end
    except (
        requests.RequestException,
        ValueError,
        RuntimeError,
        AttributeError,
    ) as error:
        LOGGER.warning(
            "Unable to obtain scan timing detail for %s (%s); end remains unknown.",
            identifier,
            type(error).__name__,
        )
        return start, None


def search_scans(
    client: QualysClient,
    stakeholders: dict[str, TrackerStakeholder],
    input_date: datetime,
    counts: dict[str, int] | None = None,
    history_groups: dict[str, list[QualysScan]] | None = None,
) -> dict[str, list[QualysScan]]:
    """Return only each schedule's latest complete run, without older fallback."""
    if not stakeholders:
        return {}
    scan_groups: dict[tuple[int, str], list[QualysScan]] = {}
    group_stakeholders: dict[tuple[int, str], TrackerStakeholder] = {}
    multi_parents: dict[tuple[int, str], list[QualysScan]] = {}
    schedule_candidates = tuple(stakeholders.items())
    tag_ids = tuple(
        sorted({stakeholder.tag_id for _, stakeholder in schedule_candidates})
    )
    LOGGER.info(
        "Searching Qualys scans for %d schedule candidates using %d unique tags",
        len(schedule_candidates),
        len(tag_ids),
    )
    offset = 1
    while True:
        response_xml = client.request(
            QualysRequest(
                endpoint="/search/was/wasscan",
                payload=build_scan_search_payload(
                    tag_ids=tag_ids,
                    input_date=input_date,
                    offset=offset,
                ),
                http_method="POST",
            )
        )
        root = parse_xml(response_xml, "scan search")
        for scan in root.findall("./data/WasScan"):
            scan_name = scan.findtext("name") or ""
            if scan.findtext("type") not in {None, "VULNERABILITY"}:
                continue
            for group_key, stakeholder in schedule_candidates:
                tag = stakeholder.tag or group_key
                launched_date = scan.findtext("launchedDate")
                if not launched_date:
                    continue
                scan_base = normalize_schedule_name(
                    scan_name.split(" Run #", 1)[0].split(" Slice", 1)[0]
                )
                if stakeholder.schedule_name and scan_base != stakeholder.schedule_name:
                    continue
                if scan_matches_stakeholder(
                    scan_name=scan_name,
                    tag=tag,
                    stakeholder=stakeholder,
                ):
                    run_name = normalize_schedule_name(scan_name.split(" Slice", 1)[0])
                    if " Run #" not in run_name:
                        run_name = "{}:{}".format(run_name, launched_date)
                    # Slices in the same numbered run can launch seconds apart.
                    # Group the complete run without using slice timestamps as its identity.
                    run_identity = (stakeholder.schedule_id, run_name)
                    if (scan.findtext("multi") or "").strip().lower() == "true":
                        multi_parents.setdefault(run_identity, []).append(scan)
                        break
                    scan_groups.setdefault(run_identity, []).append(scan)
                    group_stakeholders[run_identity] = stakeholder
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
    latest_runs: dict[int, tuple[tuple[int, str], datetime]] = {}
    ambiguous_schedules: set[int] = set()
    run_launches: dict[tuple[int, str], str] = {}
    for run_identity, scans in sorted(scan_groups.items()):
        stakeholder = group_stakeholders[run_identity]
        launched_date = min(
            (scan.findtext("launchedDate") for scan in scans),
            key=lambda value: datetime.fromisoformat(value.replace("Z", "+00:00")),
        )
        run_launches[run_identity] = launched_date
        parent_complete = all(
            parent.findtext("status") == "FINISHED"
            and parent.findtext("./summary/resultsStatus") != "PROCESSING"
            for parent in multi_parents.get(run_identity, [])
        )
        if (
            history_groups is not None
            and parent_complete
            and all(
                scan.findtext("status") in {"FINISHED", "ERROR", "CANCELED"}
                and scan.findtext("./summary/resultsStatus") != "PROCESSING"
                for scan in scans
            )
        ):
            history_groups["{}:{}".format(*run_identity)] = scans
        launch_instant = datetime.fromisoformat(launched_date.replace("Z", "+00:00"))
        current_latest = latest_runs.get(stakeholder.schedule_id)
        if current_latest is None or launch_instant > current_latest[1]:
            latest_runs[stakeholder.schedule_id] = (run_identity, launch_instant)
            ambiguous_schedules.discard(stakeholder.schedule_id)
        elif launch_instant == current_latest[1]:
            ambiguous_schedules.add(stakeholder.schedule_id)

    named_schedules: set[int] = set()
    for _, stakeholder in schedule_candidates:
        if not stakeholder.latest_scan_name.strip():
            LOGGER.info(
                "Schedule %s has no latest scan name; using conservative timestamp checks.",
                stakeholder.schedule_id,
            )
            continue
        named_schedules.add(stakeholder.schedule_id)
        run_name = normalize_schedule_name(stakeholder.latest_scan_name).split(
            " Slice", 1
        )[0]
        run_identity = (stakeholder.schedule_id, run_name)
        # Schedule timestamps can follow all slice timestamps for the same run.
        # Its explicit numbered identity is authoritative, not timestamp order.
        ambiguous_schedules.discard(stakeholder.schedule_id)
        if " Run #" in run_name and run_identity in scan_groups:
            latest_runs[stakeholder.schedule_id] = (
                run_identity,
                datetime.fromisoformat(
                    run_launches[run_identity].replace("Z", "+00:00")
                ),
            )
        else:
            latest_runs.pop(stakeholder.schedule_id, None)
            LOGGER.warning(
                "Holding schedule %s: its named latest numbered run is not visible.",
                stakeholder.schedule_id,
            )

    # Rank before checking completion. An older finished run must never replace
    # the latest run while that latest run is running or processing.
    completed_groups = {}
    incomplete_runs = 0
    missing_latest_runs = len(
        {stakeholder.schedule_id for _, stakeholder in schedule_candidates}
        - latest_runs.keys()
    )
    for run_identity, _ in latest_runs.values():
        scans = scan_groups[run_identity]
        stakeholder = group_stakeholders[run_identity]
        if stakeholder.schedule_id in ambiguous_schedules:
            LOGGER.warning(
                "Holding schedule %s: multiple runs share the latest launch timestamp.",
                stakeholder.schedule_id,
            )
            continue
        latest_slice_launch = max(
            datetime.fromisoformat(scan.findtext("launchedDate").replace("Z", "+00:00"))
            for scan in scans
        )
        schedule_launch = datetime.fromisoformat(
            stakeholder.launched_date.replace("Z", "+00:00")
        )
        if (
            stakeholder.schedule_id not in named_schedules
            and schedule_launch > latest_slice_launch
        ):
            # Schedule discovery can precede scan-search visibility. Never
            # substitute an older run when the schedule points to a newer one.
            missing_latest_runs += 1
            LOGGER.warning(
                "Holding schedule %s: its latest launch is newer than returned scan slices.",
                stakeholder.schedule_id,
            )
            continue
        # The schedule's parent launch is stable across reordered or changing
        # slice subsets. Slice launches are used for selection, never identity.
        execution_key = scheduled_execution_key(
            stakeholder.schedule_id, stakeholder.launched_date
        )
        # Use only explicit WasScan parent bounds, never schedule metadata, for
        # displayed times. Multiple parent envelopes are ambiguous and ignored.
        parents = multi_parents.get(run_identity, [])
        parent_start, parent_end = (
            scan_time_bounds(parents) if len(parents) == 1 else (None, None)
        )
        stakeholders[execution_key] = replace(
            stakeholder, scan_started_at=parent_start, scan_ended_at=parent_end
        )
        # Failed/canceled parent envelopes cannot be discarded and replaced by
        # successful children. Hold them for review without hiding slice errors.
        parent_finished = (
            not stakeholder.latest_scan_status
            or stakeholder.latest_scan_status == "FINISHED"
        ) and all(
            parent.findtext("status") == "FINISHED"
            and parent.findtext("./summary/resultsStatus") != "PROCESSING"
            for parent in multi_parents.get(run_identity, [])
        )
        if parent_finished and all(
            scan.findtext("status") in {"FINISHED", "ERROR", "CANCELED"}
            and scan.findtext("./summary/resultsStatus") != "PROCESSING"
            for scan in scans
        ):
            timing_scan = (
                parents[0]
                if len(parents) == 1
                else (
                    scans[0]
                    if not parents
                    and len(scans) == 1
                    and " Slice" not in (scans[0].findtext("name") or "")
                    else None
                )
            )
            if timing_scan is not None:
                timing_start, timing_end = execution_detail_bounds(client, timing_scan)
                stakeholders[execution_key] = replace(
                    stakeholder, scan_started_at=timing_start, scan_ended_at=timing_end
                )
            completed_groups[execution_key] = scans
        else:
            incomplete_runs += 1
    if counts is not None:
        counts["grouped_runs"] = len(scan_groups)
        counts["completed_runs"] = len(completed_groups)
        counts["incomplete_runs"] = incomplete_runs
        counts["older_runs_excluded"] = len(scan_groups) - len(latest_runs)
        counts["missing_latest_runs"] = missing_latest_runs
        counts["ambiguous_latest_runs"] = len(ambiguous_schedules)
    return completed_groups


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
            scan_name = (scan.findtext("name") or "").split(" Slice", 1)[0]
            if scan_name != previous_run:
                continue
            if scan.findtext("status") == "ERROR":
                continue
            if scan.findtext("./summary/resultsStatus") in {
                "NO_WEB_SERVICE",
                "NO_HOST_ALIVE",
            }:
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
