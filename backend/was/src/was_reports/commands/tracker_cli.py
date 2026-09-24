"""CLI utilities for WAS daily tracker operations."""

# Standard Python Libraries
import argparse
from datetime import date
import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from email.message import EmailMessage
import sys
from typing import List, Optional

# Third-Party Libraries
# First-Party Libraries
from was_reports.data.assignees import get_assignee_by_name_from_db
from was_reports.data.daily_report_tracker import (
    TrackerTableRow,
    get_tracker_record_by_id_from_db,
    list_tracker_rows_for_export_from_db,
    list_tracker_table_rows_from_db,
    mark_manual_tracker_report_sent_by_id,
)
from was_reports.data.report_runs import (
    ReportRunError,
    list_report_run_errors_from_db,
)
from was_reports.tracker.tracker_csv import write_tracker_csv
from was_reports.tracker.tracker_import import import_tracker_workbook
from was_reports.utils.logging_config import configure_logging, exception_details
from was_mailer.message import approved_analyst_recipients
from was_mailer.ses_client import create_ses_client
from was_mailer.email_reports import send_message
from was_reports.utils.env import require_env
from was_reports.storage.tracker_exports import upload_tracker_export
from was_reports.tracker.tracker_csv import write_safe_tracker_csv

LOGGER = logging.getLogger(__name__)

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


def row_limit(value: str) -> int | None:
    """Parse a positive tracker row limit or an all-rows request."""
    if value.strip().lower() == "all":
        return None
    return positive_integer(value)


def report_status_value(value: str) -> str:
    """Normalize and validate a tracker report status filter."""
    normalized_value = value.strip().upper()
    if normalized_value not in {"MANUAL", "PENDING", "SENT"}:
        raise argparse.ArgumentTypeError(
            "Report status must be manual, pending, or sent."
        )
    return normalized_value


def validated_assignee_name(value: str | None) -> str | None:
    """Return the canonical stored assignee name or reject an unknown name."""
    if value is None:
        return None
    assignee = get_assignee_by_name_from_db(value)
    if assignee is None:
        raise ValueError(
            "Assignee name '{}' is not present in was_assignees. Use the "
            "stored assignee name or leave the filter blank.".format(value)
        )
    if not assignee.active:
        raise ValueError(
            "Assignee name '{}' exists but is inactive.".format(assignee.name)
        )
    return assignee.name


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
    export_destination = export_command.add_mutually_exclusive_group(required=True)
    export_destination.add_argument(
        "--s3", action="store_true", help="Upload a password-free CSV directly to S3."
    )
    export_destination.add_argument(
        "--email-assignee", help="Email a password-free CSV to approved analysts."
    )
    export_destination.add_argument(
        "--output",
        help="CSV output path.",
    )

    table_command = subcommands.add_parser(
        "show",
        help="Display recent tracker rows from Postgres as a terminal table.",
    )
    table_dates = table_command.add_mutually_exclusive_group()
    table_dates.add_argument(
        "--days-back",
        type=nonnegative_integer,
        default=7,
        help="Include today and this many previous calendar days.",
    )
    table_dates.add_argument(
        "--all-dates", action="store_true", help="Include all tracker history."
    )
    table_command.add_argument("--tag", help="Exact customer tag.")
    table_command.add_argument(
        "--include-children", action="store_true", help="Include all descendant tags."
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
        type=row_limit,
        default=200,
        help="Maximum tracker rows to display, or 'all' for no row limit.",
    )

    row_command = subcommands.add_parser(
        "show-row",
        help="Display one tracker row by its database ID.",
    )
    row_command.add_argument(
        "--tracker-id",
        required=True,
        type=positive_integer,
        help="Tracker row ID displayed by the tracker table.",
    )
    row_command.add_argument(
        "--field",
        help="Print one field's complete value without table truncation.",
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

    import_command = subcommands.add_parser(
        "import-xlsx",
        help="Convert and import only new rows from a legacy tracker workbook.",
    )
    import_command.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to the legacy WAS daily tracker XLSX file.",
    )
    import_command.add_argument(
        "--confirm",
        action="store_true",
        help="Confirm the tracker database import.",
    )
    return parser.parse_args(argv)


def export_csv(args: argparse.Namespace) -> int:
    """Export tracker rows from Postgres to a CSV file."""
    assignee_name = validated_assignee_name(args.assignee)
    rows = list_tracker_rows_for_export_from_db(
        data_pull_date=args.data_pull_date,
        assignee_id=args.assignee_id,
        days_back=args.days_back,
        assignee_name=assignee_name,
        limit=args.limit,
    )
    if args.s3 or args.email_assignee:
        recipients = (
            approved_analyst_recipients(args.email_assignee)
            if args.email_assignee
            else None
        )
        with TemporaryDirectory(prefix="was-tracker-export-") as directory:
            path = Path(directory) / "was-report-tracker.csv"
            write_safe_tracker_csv(rows, path)
            if args.s3:
                destination = upload_tracker_export(path)
            else:
                message = EmailMessage()
                message["From"] = require_env("WAS_EMAIL_SOURCE")
                message["To"] = ", ".join(recipients)
                message["Subject"] = "WAS Report Tracker Export - Analyst Copy"
                message.set_content(
                    "The requested report tracker CSV is attached. Report passwords are excluded. Do not forward outside the approved WAS team."
                )
                message.add_attachment(
                    path.read_bytes(),
                    maintype="text",
                    subtype="csv",
                    filename=path.name,
                )
                message_id = send_message(create_ses_client(), message)
                destination = "approved analysts; SES message ID: " + message_id
        print("Exported {} tracker rows to {}.".format(len(rows), destination))
        return 0
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
    assignee_name = validated_assignee_name(args.assignee)
    filters = {}
    if args.include_children and not args.tag:
        raise ValueError("--include-children requires --tag.")
    if args.tag:
        filters = {
            "stakeholder_tag": args.tag,
            "include_children": args.include_children,
        }
    rows = list_tracker_table_rows_from_db(
        days_back=None if args.all_dates else args.days_back,
        assignee_name=assignee_name,
        report_status=args.report_status,
        limit=args.limit,
        **filters,
    )
    sys.stdout.write("{}\n".format(format_tracker_table(rows)))
    sys.stdout.write("Displayed {} tracker rows.\n".format(len(rows)))
    if assignee_name and not rows:
        sys.stdout.write(
            "Assignee '{}' exists, but no tracker rows matched the selected "
            "date window and report status.\n".format(assignee_name)
        )
    return 0


def tracker_record_display_value(value: object) -> str:
    """Return one complete operator-readable tracker field value."""
    if value is None:
        return "NULL"
    return str(value)


def display_tracker_record(record: dict[str, object], output=print) -> None:
    """Display one safe tracker row in a compact field-value table."""
    field_width = max(len(column_name) for column_name in record)
    separator = "+-{}-+-{}-+".format("-" * field_width, "-" * 54)
    output(separator)
    output("| {:<{}} | {:<54} |".format("Field", field_width, "Current value"))
    output(separator)
    for column_name, value in record.items():
        displayed_value = " ".join(tracker_record_display_value(value).split())
        if len(displayed_value) > 54:
            displayed_value = "{}...".format(displayed_value[:51])
        output(
            "| {:<{}} | {:<54} |".format(
                column_name,
                field_width,
                displayed_value,
            )
        )
    output(separator)


def show_row(args: argparse.Namespace) -> int:
    """Display one tracker row or one complete field value."""
    record = get_tracker_record_by_id_from_db(args.tracker_id)
    if args.field:
        normalized_field = args.field.strip().lower().replace("-", "_")
        if normalized_field not in record:
            raise ValueError(
                "Unknown tracker field. Available fields: {}".format(
                    ", ".join(record)
                )
            )
        sys.stdout.write("Full value for {}:\n".format(normalized_field))
        sys.stdout.write(
            "{}\n".format(tracker_record_display_value(record[normalized_field]))
        )
        return 0
    display_tracker_record(record)
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


def import_xlsx(args: argparse.Namespace) -> int:
    """Convert and import new rows from one tracker workbook."""
    if not args.confirm:
        raise ValueError("Daily tracker imports require --confirm.")
    try:
        result = import_tracker_workbook(
            args.input,
            status_callback=lambda message: print(message, flush=True),
        )
    except ValueError:
        raise
    except Exception as error:
        LOGGER.exception(
            "Daily tracker import failed; the transaction was rolled back."
        )
        raise ValueError(
            "Daily tracker import failed with {}. No rows were committed. "
            "Review the WAS application log for file, line, and database "
            "details.".format(type(error).__name__)
        ) from error
    sys.stdout.write(
        "Tracker import completed successfully. Imported {} new rows; "
        "overwrote {} matching rows; ignored {} duplicate workbook rows, "
        "{} database conflict rows, and {} blank rows.\n".format(
            result.inserted_rows,
            result.updated_rows,
            result.workbook_duplicates,
            result.database_duplicates,
            result.blank_rows,
        )
    )
    if result.inserted_rows == 0 and result.updated_rows == 0:
        sys.stdout.write(
            "No tracker data was added or overwritten. The workbook contained "
            "no unique nonblank rows to import.\n"
        )
    if result.unknown_assignees:
        sys.stdout.write(
            "Warning: {} assignee name(s) were not found in was_assignees. "
            "Their text names were preserved without an assignee ID: {}.\n".format(
                len(result.unknown_assignees),
                ", ".join(result.unknown_assignees),
            )
        )
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """Run the WAS tracker CLI."""
    configure_logging()
    args = parse_args(argv)
    try:
        if args.command == "export-csv":
            return export_csv(args)
        if args.command == "show":
            return show_table(args)
        if args.command == "show-row":
            return show_row(args)
        if args.command == "errors":
            return show_errors(args)
        if args.command == "mark-sent":
            return mark_sent(args)
        if args.command == "import-xlsx":
            return import_xlsx(args)
    except (KeyError, ValueError) as error:
        LOGGER.error("Tracker operation failed: %s", exception_details(error))
        print("Error: {}".format(str(error)), file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    sys.exit(main())
