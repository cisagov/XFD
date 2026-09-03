"""Consolidate Qualys scan slices into WAS daily tracker items."""

# Future Python Libraries
from __future__ import annotations

# Standard Python Libraries
import logging

# Third-Party Libraries
import requests

# First-Party Libraries
from was_reports.data.stakeholders import get_stakeholder_details_by_tag
from was_reports.qualys.qualys_client import QualysClient
from was_reports.tracker.models import (
    QualysScan,
    TrackerItem,
    TrackerStakeholder,
)
from was_reports.tracker.qualys_scans import get_previous_nws

LOGGER = logging.getLogger(__name__)
ADHOC_MARKERS = ("adhoc", "ad-hoc", "ad_hoc")
QUALYS_ERROR_RESULTS = frozenset(
    {"SCAN_INTERNAL_ERROR", "SCAN_RESULTS_INVALID", "PROCESSING"}
)
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
    """Return the consolidated status and result for multiple scan slices."""
    if "RUNNING" in statuses:
        return "Running", "Running"
    if "ERROR" in statuses:
        error_index = statuses.index("ERROR")
        return "Error", results[error_index]

    allowed_results = frozenset(
        {"SUCCESSFUL", "NO_WEB_SERVICE", "TIME_LIMIT_REACHED", "SERVICE_ERROR"}
    )
    if any(result not in allowed_results for result in results):
        return "Error", "Scan Internal Error"
    if "SERVICE_ERROR" in results:
        return "Finished", "Service Error"
    if "NO_WEB_SERVICE" in results:
        return "Finished", "No Web Service"
    if "TIME_LIMIT_REACHED" in results:
        return "Finished", "Time Limit Reached"
    return "Finished", "Successful"


def previous_run_name(scan_name: str) -> str | None:
    """Return the preceding numbered scan-run label when one exists."""
    marker = " Run #"
    if marker not in scan_name:
        return None
    run_number_text = scan_name.split(marker, 1)[1].strip()
    run_number = int(run_number_text)
    if run_number <= 1:
        return None
    return "Run #{}".format(run_number - 1)


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

        if result not in INACCESSIBLE_RESULTS or tag in keep_nws_tags:
            continue
        recent_nws.append(webapp_url)
        prior_run = previous_run_name(scan_name)
        if prior_run and not previous_checked and not is_adhoc:
            previous_urls = get_previous_nws(
                client=client,
                tag=tag,
                stakeholder_name=stakeholder_name,
                previous_run=prior_run,
                search_date=search_date,
            )
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
) -> list[TrackerItem]:
    """Build one consolidated tracker item for every stakeholder scan group."""
    tracker_items: list[TrackerItem] = []
    for tag, scans in scan_groups.items():
        stakeholder = stakeholders[tag]
        try:
            scan_name = element_text(scans[0], "name").split(" Slice", 1)[0]
            result_fields = create_multiscan(
                client=client,
                tag=tag,
                stakeholder_name=stakeholder.name,
                scan_name=scan_name,
                scans=scans,
                search_date=stakeholder.launched_date,
                keep_nws_tags=keep_nws_tags,
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
                    qualys_errors=result_fields[7],
                )
            )
        except (
            AttributeError,
            IndexError,
            LookupError,
            ValueError,
            requests.HTTPError,
        ) as error:
            LOGGER.exception(
                "Unable to consolidate Qualys scans for %s; "
                "marking it manual.",
                tag,
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
                    qualys_errors=type(error).__name__,
                )
            )
    return tracker_items
