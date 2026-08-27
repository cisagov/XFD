"""CSV helpers for WAS daily tracker rows."""

# Standard Python Libraries
import csv
from io import StringIO
from pathlib import Path
from typing import List

# First-Party Libraries
from was_reports.data.daily_report_tracker import DailyReportTrackerRow

CSV_HEADERS = [
    "DataPullDate",
    "Tag",
    "Scan Name",
    "Assignee",
    "Status",
    "Result",
    "Report Sent Date",
    "Report/Scan Notes",
    "Scan Start Date",
    "Next Scan Date",
    "POC",
    "POC Email",
    "Customer Notes",
    "NWS",
    "Template",
    "Recent NWS",
    "Remove NWS",
    "Password",
    "Schedule ID",
    "Qualys Error",
]


def tracker_row_to_csv(row: DailyReportTrackerRow) -> List[object]:
    """Return one tracker row in legacy daily tracker column order."""
    return [
        row.data_pull_date,
        row.tag,
        row.scan_name,
        row.assignee,
        row.status,
        row.result,
        row.report_sent_date,
        row.report_scan_notes,
        row.scan_start_date,
        row.next_scan_date,
        row.poc,
        row.poc_email,
        row.customer_notes,
        row.nws,
        row.template,
        row.recent_nws,
        row.remove_nws,
        row.legacy_password,
        row.schedule_id,
        row.qualys_error,
    ]


def tracker_rows_to_csv_text(rows: List[DailyReportTrackerRow]) -> str:
    """Return tracker rows as CSV text."""
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(CSV_HEADERS)
    for row in rows:
        writer.writerow(tracker_row_to_csv(row))
    return output.getvalue()


def write_tracker_csv(rows: List[DailyReportTrackerRow], output_path: Path) -> None:
    """Write tracker rows to a CSV file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(tracker_rows_to_csv_text(rows), encoding="utf-8")
