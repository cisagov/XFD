"""CLI utilities for WAS daily tracker operations."""

# Standard Python Libraries
import argparse
from datetime import date
from pathlib import Path
import sys
from typing import List, Optional

# Third-Party Libraries
# First-Party Libraries
from was_reports.data.daily_report_tracker import (
    TrackerTableRow,
    list_tracker_rows_for_export_from_db,
    list_tracker_table_rows_from_db,
    mark_manual_tracker_report_sent_by_id,
)
from was_reports.data.report_runs import (
    ReportRunError,
    list_report_run_errors_from_db,
)
from was_reports.tracker.tracker_csv import write_tracker_csv

TABLE_COLUMNS = [
    ("ID", 8),
    ("Pull Date", 10),
    ("Tag", 18),
    ("Scan Name", 24),
    ("Assignee", 20),
    ("Scan Status", 12),
    ("Result", 14),
    ("Report", 8),
    ("Sent Date", 10),
    ("Notes", 20),
    ("Next Scan", 10),
]

ERROR_TABLE_COLUMNS = [
    ("Run ID", 8),
    ("Tag", 18),
    ("Stage", 10),
    ("Status", 10),
    ("Started", 19),
    ("Error", 60),
]


def nonnegative_integer(value: str) -> int:
    """Parse a command argument that must be zero or greater."""
    parsed_value = int(value)
    if parsed_value < 0:
        raise argparse.ArgumentTypeError("Value must be zero or greater.")
    return parsed_value


def positive_integer(value: str) -> int:
    """Parse a command argument that must be greater than zero."""
    parsed_value = int(value)
    if parsed_value < 1:
        raise argparse.ArgumentTypeError("Value must be greater than zero.")
    return parsed_value


def report_status_value(value: str) -> str:
    """Normalize and validate a tracker report status filter."""
    normalized_value = value.strip().upper()
    if normalized_value not in {"MANUAL", "PENDING", "SENT"}:
        raise argparse.ArgumentTypeError(
            "Report status must be manual, pending, or sent."
        )
    return normalized_value


def sent_date_value(value: str) -> date:
    """Parse a manual sent date that is not in the future."""
    parsed_date = date.fromisoformat(value)
    if parsed_date > date.today():
        raise argparse.ArgumentTypeError("Sent date must not be in the future.")
    return parsed_date


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse WAS tracker CLI arguments."""
    parser = argparse.ArgumentParser(description="Manage WAS daily tracker output.")
    subcommands = parser.add_subparsers(dest="command", required=True)

    export_command = subcommands.add_parser(
        "export-csv",
        help="Export daily tracker rows to CSV.",
    )
    export_date_filter = export_command.add_mutually_exclusive_group()
    export_date_filter.add_argument(
        "--data-pull-date",
        type=date.fromisoformat,
        help="Tracker pull date to export, formatted YYYY-MM-DD.",
    )
    export_date_filter.add_argument(
        "--days-back",
        type=nonnegative_integer,
        help="Include today and this many previous calendar days.",
    )
    export_assignee_filter = export_command.add_mutually_exclusive_group()
    export_assignee_filter.add_argument(
        "--assignee-id",
        type=int,
        help="Restrict export to one assignee id.",
    )
    export_assignee_filter.add_argument(
        "--assignee",
        help="Restrict export to one exact assignee name.",
    )
    export_command.add_argument(
        "--limit",
        type=int,
        help="Maximum number of tracker rows to export.",
    )
    export_command.add_argument(
        "--output",
        required=True,
        help="CSV output path.",
    )

    table_command = subcommands.add_parser(
        "show",
        help="Display recent tracker rows from Postgres as a terminal table.",
    )
    table_command.add_argument(
        "--days-back",
        type=nonnegative_integer,
        default=7,
        help="Include today and this many previous calendar days.",
    )
    table_command.add_argument(
        "--assignee",
        help="Exact assignee name, matched without case sensitivity.",
    )
    table_command.add_argument(
        "--report-status",
        type=report_status_value,
        help="Restrict output to manual, pending, or sent reports.",
    )
    table_command.add_argument(
        "--limit",
        type=positive_integer,
        default=200,
        help="Maximum number of tracker rows to display.",
    )

    errors_command = subcommands.add_parser(
        "errors",
        help="Display persisted report generation and email errors.",
    )
    errors_command.add_argument(
        "--days-back",
        type=nonnegative_integer,
        default=7,
        help="Include errors from this many previous calendar days.",
    )
    errors_command.add_argument(
        "--tag",
        help="Restrict errors to one exact stakeholder tag.",
    )
    errors_command.add_argument(
        "--limit",
        type=positive_integer,
        default=100,
        help="Maximum number of report errors to display.",
    )

    mark_sent_command = subcommands.add_parser(
        "mark-sent",
        help="Record the sent date for one manual tracker report.",
    )
    mark_sent_command.add_argument(
        "--tracker-id",
        required=True,
        type=positive_integer,
        help="Tracker row ID displayed by the tracker table.",
    )
    mark_sent_command.add_argument(
        "--sent-date",
        required=True,
        type=sent_date_value,
        help="Manual report sent date, formatted YYYY-MM-DD.",
    )
    mark_sent_command.add_argument(
        "--confirm",
        action="store_true",
        help="Confirm the manual tracker sent-date update.",
    )
    return parser.parse_args(argv)


def export_csv(args: argparse.Namespace) -> int:
    """Export tracker rows from Postgres to a CSV file."""
    rows = list_tracker_rows_for_export_from_db(
        data_pull_date=args.data_pull_date,
        assignee_id=args.assignee_id,
        days_back=args.days_back,
        assignee_name=args.assignee,
        limit=args.limit,
    )
    write_tracker_csv(rows=rows, output_path=Path(args.output))
    sys.stdout.write("Exported {} tracker rows to {}.\n".format(len(rows), args.output))
    return 0


def table_value(value, width: int) -> str:
    """Return one normalized and width-limited terminal table value."""
    text = "" if value is None else " ".join(str(value).split())
    if len(text) > width:
        return "{}...".format(text[: width - 3])
    return text


def format_tracker_table(rows: list[TrackerTableRow]) -> str:
    """Format tracker rows as a fixed-width terminal table."""
    separator = "+{}+".format("+".join("-" * (width + 2) for _, width in TABLE_COLUMNS))

    def format_values(values) -> str:
        cells = []
        for value, (_, width) in zip(values, TABLE_COLUMNS):
            cells.append(table_value(value, width).ljust(width))
        return "| {} |".format(" | ".join(cells))

    lines = [
        separator,
        format_values([heading for heading, _ in TABLE_COLUMNS]),
        separator,
    ]
    for row in rows:
        lines.append(
            format_values(
                [
                    row.tracker_id,
                    row.data_pull_date,
                    row.tag,
                    row.scan_name,
                    row.assignee,
                    row.scan_status,
                    row.scan_result,
                    row.report_status,
                    row.report_sent_date,
                    row.notes,
                    row.next_scan_date,
                ]
            )
        )
    lines.append(separator)
    return "\n".join(lines)


def show_table(args: argparse.Namespace) -> int:
    """Display current tracker rows directly from Postgres."""
    rows = list_tracker_table_rows_from_db(
        days_back=args.days_back,
        assignee_name=args.assignee,
        report_status=args.report_status,
        limit=args.limit,
    )
    sys.stdout.write("{}\n".format(format_tracker_table(rows)))
    sys.stdout.write("Displayed {} tracker rows.\n".format(len(rows)))
    return 0


def report_error_stage(row: ReportRunError) -> str:
    """Return the failed stage represented by a persisted report error."""
    if row.error_message and row.email_error:
        return "both"
    if row.email_error:
        return "email"
    return "generation"


def format_report_error_table(rows: list[ReportRunError]) -> str:
    """Format persisted report errors as a fixed-width terminal table."""
    separator = "+{}+".format(
        "+".join("-" * (width + 2) for _, width in ERROR_TABLE_COLUMNS)
    )

    def format_values(values) -> str:
        cells = []
        for value, (_, width) in zip(values, ERROR_TABLE_COLUMNS):
            cells.append(table_value(value, width).ljust(width))
        return "| {} |".format(" | ".join(cells))

    lines = [
        separator,
        format_values([heading for heading, _ in ERROR_TABLE_COLUMNS]),
        separator,
    ]
    for row in rows:
        error_text = row.error_message or row.email_error
        if row.error_message and row.email_error:
            error_text = "{}; {}".format(row.error_message, row.email_error)
        status = row.email_status if row.email_error else row.status
        lines.append(
            format_values(
                [
                    row.id,
                    row.stakeholder_tag,
                    report_error_stage(row),
                    status,
                    row.started_at,
                    error_text,
                ]
            )
        )
    lines.append(separator)
    return "\n".join(lines)


def show_errors(args: argparse.Namespace) -> int:
    """Display persisted report generation and email errors."""
    rows = list_report_run_errors_from_db(
        days_back=args.days_back,
        stakeholder_tag=args.tag,
        limit=args.limit,
    )
    sys.stdout.write("{}\n".format(format_report_error_table(rows)))
    sys.stdout.write("Displayed {} report errors.\n".format(len(rows)))
    return 0


def mark_sent(args: argparse.Namespace) -> int:
    """Record one manual report sent date after explicit confirmation."""
    if not args.confirm:
        raise ValueError("Manual sent-date updates require --confirm.")
    mark_manual_tracker_report_sent_by_id(
        tracker_id=args.tracker_id,
        sent_date=args.sent_date,
    )
    sys.stdout.write(
        "Marked manual tracker row {} sent on {}.\n".format(
            args.tracker_id,
            args.sent_date,
        )
    )
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """Run the WAS tracker CLI."""
    args = parse_args(argv)
    try:
        if args.command == "export-csv":
            return export_csv(args)
        if args.command == "show":
            return show_table(args)
        if args.command == "errors":
            return show_errors(args)
        if args.command == "mark-sent":
            return mark_sent(args)
    except (KeyError, ValueError) as error:
        print("Error: {}".format(str(error)), file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    sys.exit(main())
