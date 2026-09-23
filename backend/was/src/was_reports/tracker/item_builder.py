"""Consolidate Qualys scan slices into WAS daily tracker items."""

# Future Python Libraries
from __future__ import annotations

# Standard Python Libraries
import logging
from datetime import datetime

# Third-Party Libraries
import requests

# First-Party Libraries
from was_reports.data.stakeholders import get_stakeholder_details_by_tag
from was_reports.qualys.qualys_client import QualysClient
from was_reports.tracker.models import (
    QualysScan,
    TrackerItem,
    TrackerStakeholder,
    scheduled_execution_key,
    scan_time_bounds,
)
from was_reports.tracker.qualys_scans import get_previous_nws
from was_reports.utils.logging_config import exception_details

LOGGER = logging.getLogger(__name__)
ADHOC_MARKERS = ("adhoc", "ad-hoc", "ad_hoc")
QUALYS_ERROR_RESULTS = frozenset({"SCAN_INTERNAL_ERROR", "SCAN_RESULTS_INVALID"})
INACCESSIBLE_RESULTS = frozenset({"NO_WEB_SERVICE", "NO_HOST_ALIVE"})


def element_text(scan: QualysScan, path: str) -> str:
    """Return required text from a Qualys scan element."""
    value = scan.findtext(path)
    if value is None:
        raise AttributeError("Qualys scan field {} is missing.".format(path))
    return value


def combined_status_and_result(
    statuses: list[str],
    results: list[str],
) -> tuple[str, str]:
    """Combine completed slices using the operator-approved result precedence.

    Incomplete or unknown inputs never become successful. NO_HOST_ALIVE keeps
    its distinct label at the inaccessible-target tier immediately after NWS.
    """
    if not statuses or len(statuses) != len(results):
        return "Error", "Scan Incomplete"
    if "RUNNING" in statuses:
        return "Running", "Running"
    if any(status not in {"FINISHED", "ERROR"} for status in statuses):
        return "Error", "Scan Incomplete"
    priority = (
        ("SCAN_RESULTS_INVALID", "Scan Results Invalid"),
        ("SCAN_INTERNAL_ERROR", "Scan Internal Error"),
        ("NO_WEB_SERVICE", "No Web Service"),
        ("NO_HOST_ALIVE", "No Host Alive"),
        ("SERVICE_ERROR", "Service Error"),
        ("TIME_LIMIT_REACHED", "Time Limit Reached"),
        ("SUCCESSFUL", "Successful"),
    )
    allowed_results = {result for result, label in priority}
    if any(result not in allowed_results for result in results):
        return "Error", "Scan Incomplete"
    for result, label in priority:
        if result in results:
            status = "Error" if "ERROR" in statuses or result in QUALYS_ERROR_RESULTS else "Finished"
            if status == "Error" and result == "SUCCESSFUL":
                return "Error", "Scan Incomplete"
            return status, label
    return "Error", "Scan Incomplete"


def previous_run_name(scan_name: str) -> str | None:
    """Return the preceding numbered scan-run label when one exists."""
    marker = " Run #"
    if marker not in scan_name:
        return None
    run_number_text = scan_name.split(marker, 1)[1].strip()
    run_number = int(run_number_text)
    if run_number <= 1:
        return None
    return "{} Run #{}".format(scan_name.split(marker, 1)[0], run_number - 1)


def earliest_slice_start(scans: list[QualysScan]) -> datetime | None:
    """Return the earliest actual target launch only when every timestamp is known."""
    return scan_time_bounds(scans)[0]


def stakeholder_flags(tag: str) -> tuple[str, bool]:
    """Return manual-report notes and FCEB status for a stakeholder tag."""
    stakeholder = get_stakeholder_details_by_tag(tag)
    if stakeholder is None and "_" in tag:
        stakeholder = get_stakeholder_details_by_tag(tag.split("_", 1)[0])
    if stakeholder is None:
        LOGGER.warning(
            "Stakeholder tag %s is absent from Postgres; marking it manual.",
            tag,
        )
        return "MANUAL", False
    manual = "CHILD TAG / OTHER" if stakeholder.manual_report else ""
    return manual, stakeholder.fceb


def create_multiscan(
    client: QualysClient,
    tag: str,
    stakeholder_name: str,
    scan_name: str,
    scans: list[QualysScan],
    search_date: str,
    keep_nws_tags: set[str],
    previous_nws_cache: dict[str, list[str]] | None = None,
) -> tuple[str, str, bool, str, str, str, bool, str]:
    """Consolidate individual scan slices into one tracker result."""
    statuses: list[str] = []
    results: list[str] = []
    recent_nws: list[str] = []
    removed_nws: list[str] = []
    qualys_errors: list[str] = []
    previous_urls: list[str] = []
    previous_checked = False
    is_adhoc = any(marker in tag.lower() for marker in ADHOC_MARKERS)

    for scan in scans:
        webapp_url = element_text(scan, "./target/webApp/url")
        result = element_text(scan, "./summary/resultsStatus")
        status = element_text(scan, "status")
        statuses.append(status)
        results.append(result)

        if result in QUALYS_ERROR_RESULTS:
            qualys_errors.append("{}<br>".format(webapp_url))

        if result not in INACCESSIBLE_RESULTS:
            continue
        recent_nws.append(webapp_url)
        if tag in keep_nws_tags:
            continue
        prior_run = previous_run_name(scan_name)
        if prior_run and not previous_checked and not is_adhoc:
            if previous_nws_cache is not None and prior_run in previous_nws_cache:
                previous_urls = previous_nws_cache[prior_run]
            else:
                previous_urls = get_previous_nws(
                    client=client,
                    tag=tag,
                    stakeholder_name=stakeholder_name,
                    previous_run=prior_run,
                    search_date=search_date,
                )
                if previous_nws_cache is not None:
                    previous_nws_cache[prior_run] = previous_urls
            previous_checked = True
        if webapp_url in previous_urls:
            removed_nws.append(webapp_url)

    status, result = combined_status_and_result(statuses, results)
    manual, fceb = stakeholder_flags(tag)
    return (
        status,
        result,
        bool(recent_nws),
        "<br>".join([""] + recent_nws),
        "<br>".join([""] + removed_nws),
        manual,
        fceb,
        "".join(qualys_errors),
    )


def create_tracker_items(
    client: QualysClient,
    scan_groups: dict[str, list[QualysScan]],
    stakeholders: dict[str, TrackerStakeholder],
    keep_nws_tags: set[str],
    previous_scan_groups: dict[str, list[QualysScan]] | None = None,
) -> list[TrackerItem]:
    """Build one consolidated tracker item for every stakeholder scan group."""
    tracker_items: list[TrackerItem] = []
    previous_nws_cache: dict[str, list[str]] = {}
    for scans in (previous_scan_groups or {}).values():
        run_name = element_text(scans[0], "name").split(" Slice", 1)[0]
        previous_nws_cache[run_name] = [
            element_text(scan, "./target/webApp/url")
            for scan in scans
            if scan.findtext("status") != "ERROR"
            and scan.findtext("./summary/resultsStatus") in INACCESSIBLE_RESULTS
        ]
    for group_key, scans in scan_groups.items():
        stakeholder = stakeholders[group_key]
        tag = stakeholder.tag or group_key
        execution_key = scheduled_execution_key(
            stakeholder.schedule_id, stakeholder.launched_date
        )
        try:
            scan_name = element_text(scans[0], "name").split(" Slice", 1)[0]
            scan_started_at, scan_ended_at = scan_time_bounds(scans)
            scan_started_at = stakeholder.scan_started_at or scan_started_at
            scan_ended_at = stakeholder.scan_ended_at or scan_ended_at
            if scan_started_at is None or (
                scan_ended_at is not None and scan_ended_at < scan_started_at
            ):
                scan_ended_at = None
            result_fields = create_multiscan(
                client=client,
                tag=tag,
                stakeholder_name=stakeholder.name,
                scan_name=scan_name,
                scans=scans,
                search_date=stakeholder.launched_date,
                keep_nws_tags=keep_nws_tags,
                previous_nws_cache=previous_nws_cache,
            )
            tracker_items.append(
                TrackerItem(
                    tag=tag,
                    scan_name=scan_name,
                    status=result_fields[0],
                    result=result_fields[1],
                    launched_date=stakeholder.launched_date,
                    next_scan_date=stakeholder.next_scan_date,
                    nws=result_fields[2],
                    recent_nws=result_fields[3],
                    removed_nws=result_fields[4],
                    manual=result_fields[5],
                    fceb=result_fields[6],
                    schedule_id=stakeholder.schedule_id,
                    tag_id=stakeholder.tag_id,
                    qualys_errors=result_fields[7],
                    scan_execution_key=execution_key,
                    scan_started_at=scan_started_at,
                    scan_ended_at=scan_ended_at,
                )
            )
        except (
            AttributeError,
            IndexError,
            LookupError,
            ValueError,
            requests.HTTPError,
        ) as error:
            LOGGER.error(
                "Unable to consolidate Qualys scans for %s; marking it manual: %s",
                tag,
                exception_details(error),
            )
            tracker_items.append(
                TrackerItem(
                    tag=tag,
                    scan_name="",
                    status="",
                    result="",
                    launched_date=stakeholder.launched_date,
                    next_scan_date=stakeholder.next_scan_date,
                    nws=False,
                    recent_nws="",
                    removed_nws="",
                    manual="MANUAL",
                    fceb=False,
                    schedule_id=stakeholder.schedule_id,
                    tag_id=stakeholder.tag_id,
                    qualys_errors=type(error).__name__,
                    scan_execution_key=execution_key,
                )
            )
    return tracker_items
