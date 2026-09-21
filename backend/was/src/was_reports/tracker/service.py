"""Application service for refreshing the WAS daily tracker."""

# Standard Python Libraries
import logging
from collections import Counter
from datetime import date, timedelta

# Third-Party Libraries
# First-Party Libraries
from was_reports.data.special_cases import list_active_special_case_names
from was_reports.qualys.qualys_client import QualysClient
from was_reports.tracker.item_builder import create_tracker_items
from was_reports.tracker.models import QualysScan, TrackerStakeholder
from was_reports.tracker.update_service import convert_qualys_date
from was_reports.tracker.qualys_scans import (
    DEFAULT_TRACKER_LOOKBACK_DAYS,
    normalize_schedule_name,
    search_scans,
    search_schedules,
    tracker_search_window,
)
from was_reports.tracker.update_service import update_tracker
from was_reports.utils.database import close, connect

LOGGER = logging.getLogger(__name__)


def pending_schedules(
    stakeholders: dict[str, TrackerStakeholder],
    counts: dict[str, int] | None = None,
    delete_apps: bool = False,
) -> dict[str, TrackerStakeholder]:
    """Exclude positively handled latest executions before fetching scan slices.

    Recurring schedules require a matching numbered run and Eastern scan day.
    Missing identity, unresolved notes, and linked attempts without customer
    delivery remain candidates. This read-only filter does not alter the queue.
    """
    identities = {}
    for group_key, stakeholder in stakeholders.items():
        run_name = normalize_schedule_name(
            stakeholder.latest_scan_name.split(" Slice", 1)[0]
        )
        if " Run #" not in run_name:
            continue
        if not run_name.rsplit(" Run #", 1)[1].isdigit():
            continue
        identities[group_key] = (
            stakeholder.schedule_id,
            convert_qualys_date(stakeholder.launched_date),
            run_name,
        )
    rows = []
    if identities:
        conn = connect()
        try:
            conn.set_session(readonly=True)
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT schedule_id, scan_start_date, scan_name, status,
                           result, report_sent_date, report_scan_notes,
                           EXISTS (SELECT 1 FROM was_report_runs run
                                   WHERE run.source_tracker_id = tracker.id),
                           EXISTS (SELECT 1 FROM was_report_runs run
                                   WHERE run.source_tracker_id = tracker.id
                                     AND run.delivery_purpose = 'customer'
                                     AND run.email_status = 'sent')
                    FROM was_daily_report_tracker tracker
                    WHERE schedule_id = ANY(%s)
                    """,
                    (sorted({identity[0] for identity in identities.values()}),),
                )
                rows = cursor.fetchall()
        finally:
            close(conn)
    handled = set()
    delivered = set()
    unresolved = set()
    deletion_required = set()
    for schedule_id, start_day, name, status, result, sent, notes, linked, emailed in rows:
        identity = (
            schedule_id, start_day,
            normalize_schedule_name((name or "").split(" Slice", 1)[0]),
        )
        if delete_apps and (notes or "").strip() == "QUALYS DELETION REQUIRED":
            deletion_required.add(identity)
        if sent or emailed:
            delivered.add(identity)
        elif (
            status == "Finished" and result and result.strip()
            and result.strip().upper() not in {"PROCESSING", "RUNNING", "FAILED", "ERROR"}
            and not (notes or "").strip() and not linked
        ):
            handled.add(identity)
        else:
            unresolved.add(identity)
    excluded = {
        group_key for group_key, identity in identities.items()
        if identity not in deletion_required
        and (identity in delivered or (identity in handled and identity not in unresolved))
    }
    pending = {
        group_key: stakeholder for group_key, stakeholder in stakeholders.items()
        if group_key not in excluded
    }
    if counts is not None:
        counts["discovered_schedules"] = len(stakeholders)
        counts["early_excluded_schedules"] = len(excluded)
        counts["schedules_requiring_scans"] = len(pending)
    LOGGER.info(
        "Early tracker execution check: %d schedules discovered; %d handled "
        "executions excluded before scan search; %d require scan search.",
        len(stakeholders), len(excluded), len(pending),
    )
    return pending


def print_discovery_breakdown(
    scan_groups: dict[str, list[QualysScan]],
    pending_groups: dict[str, list[QualysScan]],
    stakeholders: dict[str, TrackerStakeholder],
    report_days: int = 7,
) -> None:
    """Print diagnostic scan-day and stakeholder eligibility counts read-only."""
    completed_days = Counter(
        convert_qualys_date(stakeholders[key].launched_date) for key in scan_groups
    )
    pending_days = Counter(
        convert_qualys_date(stakeholders[key].launched_date) for key in pending_groups
    )
    for scan_day in sorted(completed_days):
        print(
            "Scan day {}: {} completed; {} pending.".format(
                scan_day, completed_days[scan_day], pending_days[scan_day]
            )
        )
    if not pending_groups:
        return
    tags = {stakeholders[key].tag for key in pending_groups}
    conn = connect()
    try:
        conn.set_session(readonly=True)
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT tag, manual_report, retired FROM was_stakeholders "
                "WHERE tag = ANY(%s)",
                (sorted(tags),),
            )
            flags = {row[0]: (bool(row[1]), bool(row[2])) for row in cursor.fetchall()}
    finally:
        close(conn)
    manual_count = retired_count = unknown_count = older_count = 0
    earliest_report_day = date.today() - timedelta(days=report_days - 1)
    for group_key in pending_groups:
        stakeholder = stakeholders[group_key]
        stakeholder_flags = flags.get(stakeholder.tag)
        if stakeholder_flags is None:
            unknown_count += 1
        else:
            manual_count += int(stakeholder_flags[0])
            retired_count += int(stakeholder_flags[1])
        older_count += int(
            convert_qualys_date(stakeholder.launched_date) < earliest_report_day
        )
    print(
        "Pending-run flags (may overlap): {} manual; {} retired; {} unknown exact tags; "
        "{} older than the {}-day report window starting {}.".format(
            manual_count,
            retired_count,
            unknown_count,
            older_count,
            report_days,
            earliest_report_day,
        )
    )


def pending_scan_groups(
    scan_groups: dict[str, list[QualysScan]],
    stakeholders: dict[str, TrackerStakeholder],
    delete_apps: bool = False,
    counts: dict[str, int] | None = None,
) -> dict[str, list[QualysScan]]:
    """Exclude recorded executions before costly prior-run enrichment.

    Imported day-only records are held for reconciliation, because they cannot
    distinguish multiple same-day launches. Incomplete live rows remain eligible.
    """
    if not scan_groups:
        return {}
    conn = connect()
    try:
        conn.set_session(readonly=True)
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT schedule_id, scan_start_date, scan_execution_key,
                       scan_name, status, result, report_sent_date,
                       report_scan_notes,
                       EXISTS (SELECT 1 FROM was_report_runs run
                               WHERE run.source_tracker_id = tracker.id)
                FROM was_daily_report_tracker tracker
                WHERE schedule_id = ANY(%s)
                """,
                (list({stakeholders[key].schedule_id for key in scan_groups}),),
            )
            rows = cursor.fetchall()
    finally:
        close(conn)
    pending = {}
    legacy_overlap_count = 0
    recorded_count = 0
    for group_key, scans in scan_groups.items():
        stakeholder = stakeholders[group_key]
        scan_day = convert_qualys_date(stakeholder.launched_date)
        run_name = (scans[0].findtext("name") or "").split(" Slice", 1)[0]
        recorded = False
        for (
            schedule_id,
            start_day,
            key,
            name,
            status,
            result,
            sent,
            notes,
            linked,
        ) in rows:
            if schedule_id != stakeholder.schedule_id:
                continue
            legacy = key is None or key.startswith("legacy-import:")
            if legacy and start_day == scan_day:
                recorded = True
                legacy_overlap_count += 1
                break
            if key != group_key and not (name == run_name and start_day == scan_day):
                continue
            completed = (
                status in {"Finished", "Error"}
                and result
                and result.upper() not in {"PROCESSING", "RUNNING"}
            )
            deletion_pending = delete_apps and notes == "QUALYS DELETION REQUIRED"
            if sent or linked or (completed and not deletion_pending):
                recorded = True
                recorded_count += 1
                break
        if not recorded:
            pending[group_key] = scans
    if counts is not None:
        counts["legacy_overlaps"] = legacy_overlap_count
        counts["recorded_runs"] = recorded_count
        counts["pending_runs"] = len(pending)
    LOGGER.info(
        "Tracker execution preflight: %d completed Qualys runs; %d already "
        "recorded or legacy overlaps; %d require enrichment.",
        len(scan_groups),
        len(scan_groups) - len(pending),
        len(pending),
    )
    return pending


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
    tracker_lookback_days: int = DEFAULT_TRACKER_LOOKBACK_DAYS,
    preflight_only: bool = False,
) -> int:
    """Refresh recent Qualys scan results into Postgres tracker rows."""
    if preflight_only and delete_apps:
        raise ValueError("Preflight cannot be combined with webapp deletion.")
    counts = {}
    input_date, previous_schedule_ids = tracker_search_window(
        lookback_days=tracker_lookback_days
    )
    stakeholders = search_schedules(
        client=client,
        input_date=input_date,
        previous_schedule_ids=previous_schedule_ids,
        stakeholder_tag=stakeholder_tag,
    )
    if not stakeholders:
        if preflight_only:
            print("Tracker discovery preflight: 0 schedules; 0 pending runs.")
        if stakeholder_tag:
            LOGGER.info(
                "No recent Qualys schedules found for stakeholder tag %s.",
                stakeholder_tag,
            )
        else:
            LOGGER.info("No recent Qualys schedules found.")
        return 0

    stakeholders = pending_schedules(stakeholders, counts=counts, delete_apps=delete_apps)
    if not stakeholders:
        if preflight_only:
            print(
                "Tracker discovery preflight: {} schedules; {} early exclusions; "
                "0 pending runs.".format(
                    counts["discovered_schedules"], counts["early_excluded_schedules"]
                )
            )
        return 0
    history_groups = {}
    scan_groups = search_scans(
        client=client,
        stakeholders=stakeholders,
        input_date=input_date,
        counts=counts,
        history_groups=history_groups,
    )
    pending_groups = pending_scan_groups(
        scan_groups, stakeholders, delete_apps, counts=counts
    )
    if preflight_only:
        print(
            "Tracker discovery preflight: {} schedules; {} grouped runs; "
            "{} incomplete; {} completed; {} recorded; {} legacy overlaps; "
            "{} pending runs requiring enrichment.".format(
                counts["discovered_schedules"],
                counts.get("grouped_runs", 0),
                counts.get("incomplete_runs", 0),
                counts.get("completed_runs", 0),
                counts.get("recorded_runs", 0),
                counts.get("legacy_overlaps", 0),
                len(pending_groups),
            )
        )
        print(
            "Before scan search: {} handled executions excluded; {} schedules retained.".format(
                counts["early_excluded_schedules"], counts["schedules_requiring_scans"]
            )
        )
        print(
            "Pending runs are discovery candidates, not the final report-delivery count."
        )
        print(
            "Latest-only selection: {} older runs excluded; {} schedules held because "
            "their latest execution was not found in the returned scan slices; "
            "{} schedules held for tied latest executions.".format(
                counts.get("older_runs_excluded", 0),
                counts.get("missing_latest_runs", 0),
                counts.get("ambiguous_latest_runs", 0),
            )
        )
        print_discovery_breakdown(scan_groups, pending_groups, stakeholders)
        return len(pending_groups)
    tracker_items = create_tracker_items(
        client=client,
        scan_groups=pending_groups,
        stakeholders=stakeholders,
        keep_nws_tags=active_no_deletion_tags(),
        previous_scan_groups=history_groups,
    )
    persisted_count = update_tracker(
        client=client,
        tracker_items=tracker_items,
        delete_apps=delete_apps,
    )
    LOGGER.info(
        "Persisted %d inserted/updated WAS tracker rows from %d candidates.",
        persisted_count,
        len(tracker_items),
    )
    return persisted_count
