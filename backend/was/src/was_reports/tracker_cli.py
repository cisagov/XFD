"""CLI utilities for WAS daily tracker operations."""

# Standard Python Libraries
import argparse
import sys
from datetime import date
from pathlib import Path
from typing import List, Optional

# First-Party Libraries
from was_reports.data.daily_report_tracker import (
    list_tracker_rows_for_export_from_db,
)
from was_reports.tracker_csv import write_tracker_csv


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse WAS tracker CLI arguments."""
    parser = argparse.ArgumentParser(description="Manage WAS daily tracker output.")
    subcommands = parser.add_subparsers(dest="command", required=True)

    export_command = subcommands.add_parser(
        "export-csv",
        help="Export daily tracker rows to CSV.",
    )
    export_command.add_argument(
        "--data-pull-date",
        type=date.fromisoformat,
        help="Tracker pull date to export, formatted YYYY-MM-DD.",
    )
    export_command.add_argument(
        "--assignee-id",
        type=int,
        help="Restrict export to one assignee id.",
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
    return parser.parse_args(argv)


def export_csv(args: argparse.Namespace) -> int:
    """Export tracker rows from Postgres to a CSV file."""
    rows = list_tracker_rows_for_export_from_db(
        data_pull_date=args.data_pull_date,
        assignee_id=args.assignee_id,
        limit=args.limit,
    )
    write_tracker_csv(rows=rows, output_path=Path(args.output))
    print("Exported {} tracker rows to {}.".format(len(rows), args.output))
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """Run the WAS tracker CLI."""
    args = parse_args(argv)
    if args.command == "export-csv":
        return export_csv(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
