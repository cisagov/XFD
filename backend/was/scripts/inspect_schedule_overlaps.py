"""Read-only experiment on captured schedule overlaps, never a production selector."""

import argparse
from collections import Counter
from datetime import date
import json
import os
from pathlib import Path

from was_reports.data.daily_report_tracker import list_ready_report_candidates
from was_reports.utils.database import connect


def classify(rows: list[dict]) -> str:
    """Separate delivery evidence from tracker completion and unresolved work."""
    if not rows:
        return "no_matching_day"
    if len(rows) != 1:
        return "ambiguous_multiple_rows"
    row = rows[0]
    if row["run_status"] in {"running", "pending"} or row["email_status"] == "sending":
        return "active_report_run"
    if row["run_status"] == "failed" or row["email_status"] == "failed":
        return "failed_report_or_delivery"
    if row["has_notes"]:
        return "notes_require_review"
    if row["email_status"] == "held":
        return "held_delivery"
    if row["sent"] or (row["emailed"] and row["delivery_purpose"] == "customer"):
        return "delivery_recorded"
    if row["run_status"]:
        return "other_linked_report_run"
    if row["status"].lower() == "error":
        return "scan_error"
    if row["status"].lower() == "finished" and row["result"].lower() not in {
        "", "processing", "running"
    }:
        return "tracker_complete_unsent"
    return "incomplete_or_unknown"


def main() -> None:
    """Inspect the captured overlap population using a fresh read-only snapshot."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--comparison", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    comparison = json.loads(arguments.comparison.read_text())
    population = next(item for item in comparison["comparisons"]
                      if item["lookback_days"] == 3)
    schedules = population["current_only"]
    connection = connect()
    try:
        connection.set_session(readonly=True, isolation_level="REPEATABLE READ")
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT tracker.id, tracker.schedule_id, tracker.scan_start_date, "
                "COALESCE(tracker.status, ''), COALESCE(tracker.result, ''), "
                "tracker.report_sent_date IS NOT NULL, "
                "BTRIM(COALESCE(tracker.report_scan_notes, '')) <> '', "
                "tracker.scan_execution_key, run.status, run.email_status, "
                "run.emailed_at IS NOT NULL, run.delivery_purpose, tracker.tag, "
                "tracker.scan_name, run.id, run.started_at, run.completed_at, "
                "CASE WHEN run.error_message ILIKE '%%stale%%' THEN 'stale' "
                "WHEN run.error_message IS NOT NULL THEN 'other' ELSE NULL END "
                "FROM was_daily_report_tracker tracker "
                "LEFT JOIN was_report_runs run ON run.source_tracker_id = tracker.id "
                "WHERE tracker.schedule_id = ANY(%s)",
                (sorted({item["schedule_id"] for item in schedules}),),
            )
            fields = ("id", "schedule_id", "scan_day", "status", "result", "sent",
                      "has_notes", "execution_key", "run_status", "email_status", "emailed",
                      "delivery_purpose", "tag", "scan_name", "run_id", "run_started_at",
                      "run_completed_at", "error_category")
            records = [dict(zip(fields, row)) for row in cursor.fetchall()]
            cursor.execute("SELECT CURRENT_TIMESTAMP, CURRENT_DATE, "
                           "current_setting('transaction_read_only')")
            timestamp, database_day, readonly = cursor.fetchone()
        candidates = list_ready_report_candidates(connection, days_back=7)
    finally:
        connection.close()
    details = []
    for schedule in schedules:
        matches = [row for row in records if row["schedule_id"] == schedule["schedule_id"]
                   and row["scan_day"] == date.fromisoformat(schedule["launch_day_eastern"])]
        category = classify(matches)
        details.append({"schedule_id": schedule["schedule_id"], "tag": schedule["tag"],
                        "scan_day": schedule["launch_day_eastern"], "category": category,
                        "matching_tracker_ids": sorted({row["id"] for row in matches}),
                        "rows": matches})
    counts = dict(Counter(item["category"] for item in details))
    skipped = counts.get("delivery_recorded", 0)
    output = {
        "scope": "captured schedules plus fresh read-only tracker state; not full scan parity",
        "database_timestamp": timestamp.isoformat(), "database_day": str(database_day),
        "transaction_read_only": readonly,
        "overlap_count": len(schedules), "categories": counts,
        "experimental_delivery_only_skips": skipped,
        "experimental_remaining_schedule_candidates": population["current_executions"] - skipped,
        "legacy_schedule_candidates": population["legacy_tags"],
        "current_existing_database_report_candidates_7_days": len(candidates),
        "limitations": ["Schedule-day identity may cover multiple executions.",
                        "Skipping a schedule can hide older unrecorded runs in the same window.",
                        "Experiment does not prove total scan API calls or final delivery counts.",
                        "Tracker completion and successful delivery are distinct.",
                        "Qualys schedules are the prior capture, not refreshed in this inspection."],
        "details": details,
    }
    descriptor = os.open(arguments.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        json.dump(output, stream, indent=2, default=str)
    print(json.dumps({key: value for key, value in output.items() if key != "details"}, indent=2))


if __name__ == "__main__":
    main()
