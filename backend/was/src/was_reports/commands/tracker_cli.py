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
)
from was_reports.tracker.tracker_csv import write_tracker_csv

TABLE_COLUMNS = [
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
        required=True,
        help="Exact assignee name, matched without case sensitivity.",
    )
    table_command.add_argument(
        "--limit",
        type=positive_integer,
        default=200,
        help="Maximum number of tracker rows to display.",
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
        limit=args.limit,
    )
    sys.stdout.write("{}\n".format(format_tracker_table(rows)))
    sys.stdout.write("Displayed {} tracker rows.\n".format(len(rows)))
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """Run the WAS tracker CLI."""
    args = parse_args(argv)
    if args.command == "export-csv":
        return export_csv(args)
    if args.command == "show":
        return show_table(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
