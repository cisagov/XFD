"""Compare legacy discovery and stored report eligibility without operational writes.

Only schedule-search requests and read-only database SELECTs are allowed. This
does not simulate slice aggregation, tracker insertion, or future deliveries.
"""

import argparse
from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path

from lxml import etree

from compare_tracker_selection import compare, load_legacy_function, save_private
from was_reports.commands.batch_preflight import inspect_exclusions, parse_window
from was_reports.commands.batch_progress import summarize_candidates
from was_reports.data.daily_report_tracker import (
    latest_tracker_pull_date,
    list_ready_report_candidates,
)
from was_reports.qualys.qualys_client import QualysRequest, create_qualys_client
from was_reports.tracker.models import TrackerStakeholder
from was_reports.tracker.qualys_scans import (
    build_schedule_search_payload,
    parse_xml,
    response_count,
    response_has_more_records,
)
from was_reports.tracker.service import pending_schedules
from was_reports.utils.database import connect


def source_fingerprints() -> dict[str, str]:
    """Identify local code, including uncommitted edits, rather than only HEAD."""
    root = Path(__file__).resolve().parents[1]
    paths = (
        "scripts/compare_tracker_selection.py", "scripts/diagnose_report_alignment.py",
        "src/was_reports/tracker/qualys_scans.py", "src/was_reports/tracker/service.py",
        "src/was_reports/data/daily_report_tracker.py",
        "src/was_reports/commands/batch_preflight.py",
    )
    return {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in paths}


def capture(report_days: int | None, discovery_days: int) -> dict:
    """Capture one read-only DB snapshot and one shared schedule-search dataset."""
    load_legacy_function({})  # Validate the pinned source before external access.
    connection = connect()
    try:
        connection.set_session(readonly=True, isolation_level="REPEATABLE READ")
        anchor = latest_tracker_pull_date(connection)
        candidates = list_ready_report_candidates(connection, days_back=report_days)
        exclusions = inspect_exclusions(connection, report_days, None)
        with connection.cursor() as cursor:
            cursor.execute("SELECT CURRENT_TIMESTAMP, CURRENT_DATE, "
                           "current_setting('transaction_read_only')")
            timestamp, database_day, readonly = cursor.fetchone()
            if readonly != "on":
                raise RuntimeError("Diagnostic requires a read-only transaction.")
            cursor.execute(
                "SELECT schedule_id, scan_start_date, data_pull_date "
                "FROM was_daily_report_tracker WHERE schedule_id IS NOT NULL"
            )
            tracker_rows = [[row[0], str(row[1]) if row[1] else None,
                             str(row[2]) if row[2] else None] for row in cursor.fetchall()]
            cursor.execute(
                "SELECT schedule_id, scan_start_date, scan_name, status, result, "
                "report_sent_date IS NOT NULL, "
                "CASE WHEN BTRIM(COALESCE(report_scan_notes, '')) = '' THEN '' "
                "ELSE 'PRESENT' END, "
                "EXISTS (SELECT 1 FROM was_report_runs run WHERE run.source_tracker_id = tracker.id), "
                "EXISTS (SELECT 1 FROM was_report_runs run WHERE run.source_tracker_id = tracker.id "
                "AND run.delivery_purpose = 'customer' AND run.email_status = 'sent') "
                "FROM was_daily_report_tracker tracker WHERE schedule_id IS NOT NULL"
            )
            early_rows = [[row[0], str(row[1]) if row[1] else None, *row[2:]]
                          for row in cursor.fetchall()]
            cursor.execute(
                "SELECT id, scan_start_date, scan_name FROM was_daily_report_tracker "
                "WHERE id = ANY(%s)", ([item.id for item in candidates],)
            )
            scan_details = {row[0]: (str(row[1]) if row[1] else None, row[2])
                            for row in cursor.fetchall()}
        reports = [{
            "tracker_id": item.id, "tag": item.tag, "schedule_id": item.schedule_id,
            "template": item.template, "qualys_error_overlay": bool(item.qualys_error),
            "scan_start_date": scan_details[item.id][0],
            "scan_name": scan_details[item.id][1],
        } for item in candidates]
    finally:
        connection.close()

    # The legacy endpoint uses a date-only cutoff. Capture at midnight so a
    # time-bearing modern filter cannot hide records from the legacy replay.
    cutoff = (anchor - timedelta(days=max(2, discovery_days))).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    client = create_qualys_client()
    schedules = []
    offset = 1
    calls = 0
    while True:
        response = client.request(QualysRequest(
            endpoint="/search/was/wasscanschedule",
            payload=build_schedule_search_payload(cutoff, offset), http_method="POST",
        ))
        root = parse_xml(response, "alignment schedule capture")
        for schedule in root.findall("./data/WasScanSchedule"):
            # Persist only fields used by the replay, never launchedBy or credentials.
            safe = etree.Element("WasScanSchedule")
            for field in ("id", "name", "type", "nextLaunchDate"):
                element = schedule.find(field)
                if element is not None:
                    etree.SubElement(safe, field).text = element.text
            for parent, leaves in (
                ("lastScan", ("id", "name", "launchedDate", "status")),
                ("scheduling", ("occurrenceType",)),
            ):
                container = etree.SubElement(safe, parent)
                for leaf in leaves:
                    value = schedule.findtext("{}/{}".format(parent, leaf))
                    if value is not None:
                        etree.SubElement(container, leaf).text = value
            container = safe
            for parent in ("target", "tags", "included", "tagList", "list"):
                container = etree.SubElement(container, parent)
            for tag_id in schedule.findall("./target/tags/included//Tag/id"):
                etree.SubElement(etree.SubElement(container, "Tag"), "id").text = tag_id.text
            schedules.append(etree.tostring(safe, encoding="unicode"))
        calls += 1
        count = response_count(root)
        if not response_has_more_records(root):
            break
        if count < 1:
            raise RuntimeError("Qualys schedule pagination did not advance.")
        offset += count
    return {
        "schema_version": 1, "anchor": anchor.isoformat(), "tracker_rows": tracker_rows,
        "early_tracker_rows": early_rows, "schedules": schedules,
        "capture_schedule_requests": calls, "report_days": report_days,
        "discovery_days": discovery_days, "database_timestamp": timestamp.isoformat(),
        "database_day": str(database_day), "transaction_read_only": readonly,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "code_at_capture": source_fingerprints(), "eligible_reports": reports,
        "report_summary": asdict(summarize_candidates(candidates)), "exclusions": exclusions,
    }


def build_report(snapshot: dict) -> dict:
    """Replay discovery and link it to the captured production eligibility result."""
    if snapshot.get("schema_version") != 1 or snapshot.get("transaction_read_only") != "on":
        raise ValueError("Not a supported read-only alignment snapshot.")
    legacy_comparison = compare(snapshot, 2)
    current_comparison = compare(snapshot, snapshot["discovery_days"])
    current = {}
    for record in current_comparison["current_selected"]:
        fields = dict(record)
        execution_key = fields.pop("execution_key")
        current[execution_key] = TrackerStakeholder(**fields)
    early_rows = [(row[0], date.fromisoformat(row[1]) if row[1] else None, *row[2:])
                  for row in snapshot["early_tracker_rows"]]
    counts = {}
    pending = pending_schedules(current, counts=counts, tracker_rows=early_rows)
    legacy_pairs = {(row["tag"], row["schedule_id"])
                    for row in legacy_comparison["legacy_selected"]}
    legacy_valid = legacy_comparison.get("legacy_valid", True)
    modern_pairs = {(item.tag, item.schedule_id) for item in pending.values()}
    reports = []
    for item in snapshot["eligible_reports"]:
        pair = (item["tag"], item["schedule_id"])
        reports.append({
            **item,
            "same_tag_schedule_in_legacy_discovery": pair in legacy_pairs if legacy_valid else None,
            "same_tag_schedule_in_new_pending_discovery": pair in modern_pairs,
        })
    return {
        "scope": "schedule selection and stored new-report eligibility, not full outcome parity",
        "database_timestamp": snapshot["database_timestamp"],
        "database_day": snapshot["database_day"], "captured_at": snapshot["captured_at"],
        "report_days": snapshot["report_days"], "discovery_days": snapshot["discovery_days"],
        "code_at_capture": snapshot["code_at_capture"], "code_at_replay": source_fingerprints(),
        "legacy_48_hour_comparison": legacy_comparison,
        "current_window_comparison": current_comparison, "early_filter_counts": counts,
        "new_early_excluded": [key for key in current if key not in pending],
        "legacy_only_after_new_early_filter": (
            sorted(legacy_pairs - modern_pairs) if legacy_valid else None),
        "new_only_after_early_filter": (
            sorted(modern_pairs - legacy_pairs) if legacy_valid else None),
        "eligible_reports": reports, "report_summary": snapshot["report_summary"],
        "exclusions": snapshot["exclusions"],
        "limitations": [
            "Legacy discovery is not a legacy PDF-generation queue.",
            "Eligible reports are stored tracker candidates, not predictions after refresh.",
            "Offline replay recalculates discovery only; report eligibility remains captured SQL output.",
            "No scan slices, historical NWS searches, tracker writes, generation, or email calls occur.",
            "Qualys pagination is a shared capture, not an atomic vendor snapshot.",
            "Modern early filtering uses captured tracker rows; unknowns remain pending.",
            "Report-to-discovery links compare tag and schedule only, not exact run identity.",
            "Legacy AM and ad-hoc lookups are adapted as described in comparison results.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    """Write private reproducible artifacts and print safe operator-facing counts."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, help="Replay locally without DB or Qualys access")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--days-back", type=parse_window, default=7)
    parser.add_argument("--discovery-days", type=int, default=3)
    args = parser.parse_args(argv)
    if args.discovery_days < 1:
        parser.error("--discovery-days must be positive")
    snapshot_path = args.output.with_suffix(".snapshot.json")
    if args.output.exists() or (not args.snapshot and snapshot_path.exists()):
        parser.error("Choose a new output filename; existing artifacts are never overwritten")
    snapshot = json.loads(args.snapshot.read_text()) if args.snapshot else capture(
        args.days_back, args.discovery_days
    )
    report = build_report(snapshot)
    if not args.snapshot:
        save_private(snapshot_path, snapshot)
    save_private(args.output, report)
    print("Read-only alignment diagnostic. Database snapshot: {}".format(report["database_timestamp"]))
    print("Legacy 48-hour selection: {} tags".format(
        report["legacy_48_hour_comparison"]["legacy_tags"]))
    if not report["legacy_48_hour_comparison"].get("legacy_valid", True):
        print("Legacy replay failed: {}. Legacy counts/differences are unavailable, not zero.".format(
            report["legacy_48_hour_comparison"]["legacy_evaluation_error"]))
    print("New discovery stages: {}".format(report["early_filter_counts"]))
    print("Stored eligible reports: {}".format(report["report_summary"]))
    print("Eligible tracker ID | tag | template | scan date")
    for item in report["eligible_reports"]:
        print("{} | {} | {} | {}".format(item["tracker_id"], item["tag"],
                                         item["template"], item["scan_start_date"]))
    print("Exclusions: {}".format(dict(report["exclusions"])))
    print("NOT full legacy report parity; no post-refresh report prediction. See limitations in JSON.")
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
