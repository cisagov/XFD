"""CLI for stakeholder contact maintenance and controlled CSV export."""

# Standard Python Libraries
import argparse
import csv
from datetime import datetime, timezone
import os
from pathlib import Path
import sys
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import List, Optional

# Third-Party Libraries
from botocore.exceptions import BotoCoreError, ClientError
from psycopg2 import DatabaseError

# First-Party Libraries
from was_mailer.email_reports import send_message
from was_mailer.message import (
    approved_analyst_recipients,
    build_stakeholder_export_email,
    parse_email_addresses,
)
from was_mailer.ses_client import create_ses_client
from was_reports.data.stakeholders import (
    STAKEHOLDER_CREATE_COLUMNS,
    STAKEHOLDER_MUTABLE_COLUMNS,
    create_stakeholder_in_db,
    get_stakeholder_record_by_tag,
    list_stakeholders_for_export_from_db,
    update_stakeholder_contacts_for_tag,
    update_stakeholder_fields_for_tag,
)
from was_reports.commands.stakeholder_import import (
    DEFAULT_NULL_TOKEN,
    import_prepared_rows,
    prepare_stakeholder_csv,
)
from was_reports.storage.stakeholder_exports import upload_stakeholder_export
from was_reports.utils.env import require_env
from was_reports.utils.logging_config import configure_logging


def nonempty_value(value: str) -> str:
    """Return one normalized nonempty command value."""
    normalized_value = value.strip()
    if not normalized_value:
        raise argparse.ArgumentTypeError("Value must not be empty.")
    if "\r" in normalized_value or "\n" in normalized_value:
        raise argparse.ArgumentTypeError("Value must not contain line breaks.")
    return normalized_value


def email_list_value(value: str) -> str:
    """Validate a comma or semicolon separated email address list."""
    normalized_value = nonempty_value(value)
    addresses = parse_email_addresses(normalized_value)
    if not addresses:
        raise argparse.ArgumentTypeError("At least one email address is required.")
    for address in addresses:
        if address.count("@") != 1 or any(character.isspace() for character in address):
            raise argparse.ArgumentTypeError(
                "Email addresses must use the local@domain format."
            )
        local_part, domain_part = address.split("@", 1)
        if not local_part or not domain_part or domain_part.startswith("."):
            raise argparse.ArgumentTypeError(
                "Email addresses must use the local@domain format."
            )
    return normalized_value


def nonnegative_integer(value: str) -> int:
    """Return a nonnegative integer command value."""
    try:
        parsed_value = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "Value must be a whole number of zero or greater."
        ) from error
    if parsed_value < 0:
        raise argparse.ArgumentTypeError(
            "Value must be a whole number of zero or greater."
        )
    return parsed_value


STAKEHOLDER_INTEGER_COLUMNS = frozenset(
    {
        "num_web_apps",
        "web_apps_last_updated",
        "last_scanned",
        "next_scheduled",
        "onboarding_date",
    }
)
STAKEHOLDER_BOOLEAN_COLUMNS = frozenset(
    {"elections", "fceb", "manual_report", "retired"}
)
STAKEHOLDER_EMAIL_COLUMNS = frozenset({"distro_email", "tech_poc_email"})
STAKEHOLDER_EPOCH_COLUMNS = frozenset(
    {
        "web_apps_last_updated",
        "last_scanned",
        "next_scheduled",
        "onboarding_date",
    }
)
STAKEHOLDER_EDIT_COLUMNS = tuple(
    column_name
    for column_name in STAKEHOLDER_CREATE_COLUMNS
    if column_name in STAKEHOLDER_MUTABLE_COLUMNS
)


def stakeholder_update_assignment(value: str) -> tuple[str, str]:
    """Parse one column=value stakeholder update assignment."""
    column_name, separator, raw_value = value.partition("=")
    normalized_column = column_name.strip().replace("-", "_")
    if not separator or not normalized_column or not raw_value.strip():
        raise argparse.ArgumentTypeError(
            "Updates must use the format column=value with a nonempty value."
        )
    if normalized_column not in STAKEHOLDER_MUTABLE_COLUMNS:
        raise argparse.ArgumentTypeError(
            "The stakeholder column is unsupported or protected."
        )
    return normalized_column, raw_value.strip()


def normalize_stakeholder_update(column_name: str, value: str) -> object:
    """Validate and convert one stakeholder field value."""
    try:
        if column_name in STAKEHOLDER_INTEGER_COLUMNS:
            return nonnegative_integer(value)
        if column_name in STAKEHOLDER_BOOLEAN_COLUMNS:
            normalized_value = value.strip().lower()
            if normalized_value not in {"true", "false"}:
                raise ValueError("Boolean values must be true or false.")
            return normalized_value == "true"
        if column_name in STAKEHOLDER_EMAIL_COLUMNS:
            return email_list_value(value)
        return nonempty_value(value)
    except argparse.ArgumentTypeError as error:
        raise ValueError(str(error)) from error


def stakeholder_updates(args: argparse.Namespace) -> dict[str, object]:
    """Return validated stakeholder updates without duplicate columns."""
    updates: dict[str, object] = {}
    for column_name, raw_value in args.set_values:
        if column_name in updates:
            raise ValueError("A stakeholder column may be updated only once.")
        updates[column_name] = normalize_stakeholder_update(
            column_name,
            raw_value,
        )
    for column_name in args.clear_values:
        if column_name in updates:
            raise ValueError("A stakeholder column may be updated only once.")
        updates[column_name] = None
    return updates


def display_stakeholder_record(record: dict[str, object], output=print) -> None:
    """Display one stakeholder row as an operator-readable field table."""
    field_width = max(len(column_name) for column_name in record)
    separator = "+-{}-+-{}-+".format("-" * field_width, "-" * 54)
    output(separator)
    output("| {:<{}} | {:<54} |".format("Field", field_width, "Current value"))
    output(separator)
    for column_name, value in record.items():
        displayed_value = "NULL" if value is None else str(value)
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


def add_contact_field_options(
    parser: argparse.ArgumentParser,
    option_name: str,
    value_type,
    help_text: str,
) -> None:
    """Add mutually exclusive update and clear options for one contact field."""
    destination = option_name.replace("-", "_")
    option_group = parser.add_mutually_exclusive_group()
    option_group.add_argument(
        "--{}".format(option_name),
        dest=destination,
        type=value_type,
        help=help_text,
    )
    option_group.add_argument(
        "--clear-{}".format(option_name),
        dest="clear_{}".format(destination),
        action="store_true",
        help="Clear the stored {} value.".format(option_name.replace("-", " ")),
    )


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse stakeholder administration arguments."""
    parser = argparse.ArgumentParser(description="Manage WAS stakeholders.")
    subcommands = parser.add_subparsers(dest="command", required=True)

    contacts_command = subcommands.add_parser(
        "update-contacts",
        help="Update stakeholder POC and email fields.",
    )
    contacts_command.add_argument("--tag", required=True, type=nonempty_value)
    add_contact_field_options(
        contacts_command,
        "was-report-poc",
        nonempty_value,
        "WAS report POC name.",
    )
    add_contact_field_options(
        contacts_command,
        "tech-poc-email",
        email_list_value,
        "Technical POC email address list.",
    )
    add_contact_field_options(
        contacts_command,
        "distro-email",
        email_list_value,
        "Report distribution email address list.",
    )
    contacts_command.add_argument(
        "--confirm",
        action="store_true",
        help="Confirm the stakeholder contact update.",
    )

    show_command = subcommands.add_parser(
        "show",
        help="Display one stakeholder row by exact tag.",
    )
    show_command.add_argument("--tag", required=True, type=nonempty_value)

    update_command = subcommands.add_parser(
        "update",
        help="Update selected fields for one stakeholder.",
    )
    update_command.add_argument("--tag", required=True, type=nonempty_value)
    update_command.add_argument(
        "--set",
        dest="set_values",
        action="append",
        default=[],
        type=stakeholder_update_assignment,
        help="Set an editable field using column=value. Repeat as needed.",
    )
    update_command.add_argument(
        "--clear",
        dest="clear_values",
        action="append",
        default=[],
        choices=sorted(STAKEHOLDER_MUTABLE_COLUMNS),
        help="Set an editable field to SQL NULL. Repeat as needed.",
    )
    update_command.add_argument(
        "--confirm",
        action="store_true",
        help="Confirm the stakeholder field update.",
    )

    export_command = subcommands.add_parser(
        "export-csv",
        help="Export WAS stakeholder records to CSV.",
    )
    export_command.add_argument(
        "--output",
        type=Path,
        default=Path("/output/was-stakeholders.csv"),
        help="Local output path or attachment filename.",
    )
    export_destination = export_command.add_mutually_exclusive_group()
    export_destination.add_argument(
        "--s3",
        action="store_true",
        help="Upload the export to the configured WAS S3 bucket.",
    )
    export_destination.add_argument(
        "--email-assignee",
        type=email_list_value,
        help="Email the export to active WAS assignee addresses.",
    )
    export_command.add_argument(
        "--include-report-passwords",
        action="store_true",
        help="Include sensitive PDF report passwords in the export.",
    )
    export_command.add_argument(
        "--confirm-sensitive-export",
        action="store_true",
        help="Confirm creation of a CSV containing report passwords.",
    )

    import_command = subcommands.add_parser(
        "import-csv",
        help="Prepare and insert new WAS stakeholders from CSV.",
    )
    import_command.add_argument("--input", required=True, type=Path)
    import_command.add_argument("--prepared-output", required=True, type=Path)
    import_command.add_argument("--null-token", default=DEFAULT_NULL_TOKEN)
    import_command.add_argument(
        "--confirm",
        action="store_true",
        help="Confirm the insert-only stakeholder import.",
    )

    add_command = subcommands.add_parser(
        "add",
        help="Add one stakeholder and generate its report password.",
    )
    add_command.add_argument("--tag", required=True, type=nonempty_value)
    add_command.add_argument("--customer-name", required=True, type=nonempty_value)
    for option_name in (
        "comments",
        "location-notes",
        "ci-type",
        "testing-sector",
        "subtype",
        "was-report-poc",
        "frequency",
        "parent-tag",
        "ticket",
        "state",
    ):
        add_command.add_argument("--{}".format(option_name), type=nonempty_value)
    add_command.add_argument("--distro-email", type=email_list_value)
    add_command.add_argument("--tech-poc-email", type=email_list_value)
    for option_name in (
        "num-web-apps",
        "web-apps-last-updated",
        "last-scanned",
        "next-scheduled",
        "onboarding-date",
    ):
        add_command.add_argument("--{}".format(option_name), type=nonnegative_integer)
    add_command.add_argument("--elections", action="store_true")
    add_command.add_argument("--fceb", action="store_true")
    add_command.add_argument("--manual-report", action="store_true")
    add_command.add_argument("--retired", action="store_true")
    add_command.add_argument(
        "--confirm",
        action="store_true",
        help="Confirm creation of the stakeholder record.",
    )
    return parser.parse_args(argv)


def contact_updates(args: argparse.Namespace) -> dict[str, str | None]:
    """Return only stakeholder contact fields explicitly supplied by an operator."""
    updates = {}
    for field_name in ("was_report_poc", "tech_poc_email", "distro_email"):
        field_value = getattr(args, field_name)
        clear_value = getattr(args, "clear_{}".format(field_name))
        if field_value is not None:
            updates[field_name] = field_value
        elif clear_value:
            updates[field_name] = None
    return updates


def spreadsheet_safe_value(column_name: str, value: object) -> object:
    """Prevent formula execution for non-password text opened in a spreadsheet."""
    if column_name == "report_password" or not isinstance(value, str):
        return value
    stripped_value = value.lstrip()
    if stripped_value and stripped_value[0] in {"=", "+", "-", "@"}:
        return "'{}".format(value)
    return value


def stakeholder_export_value(column_name: str, value: object) -> object:
    """Return a safe, human-readable stakeholder export value."""
    if column_name in STAKEHOLDER_EPOCH_COLUMNS and value is not None:
        try:
            timestamp = datetime.fromtimestamp(int(value), tz=timezone.utc)
        except (OverflowError, TypeError, ValueError) as error:
            raise ValueError(
                "{} contains an invalid epoch timestamp.".format(column_name)
            ) from error
        return timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
    return spreadsheet_safe_value(column_name, value)


def write_stakeholder_csv(
    columns: list[str],
    rows: list[tuple[object, ...]],
    output_path: Path,
) -> None:
    """Write one stakeholder CSV atomically with owner-only file permissions."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            prefix=".was-stakeholders-",
            suffix=".csv",
            dir=str(output_path.parent),
            delete=False,
        ) as csv_file:
            temporary_path = Path(csv_file.name)
            os.chmod(temporary_path, 0o600)
            writer = csv.writer(csv_file)
            writer.writerow(columns)
            for row in rows:
                writer.writerow(
                    [
                        stakeholder_export_value(column_name, value)
                        for column_name, value in zip(columns, row)
                    ]
                )
        os.replace(temporary_path, output_path)
        os.chmod(output_path, 0o600)
    except Exception:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise


def run_update_contacts(args: argparse.Namespace) -> int:
    """Update selected stakeholder contact fields."""
    if not args.confirm:
        raise ValueError("Stakeholder contact updates require --confirm.")
    updates = contact_updates(args)
    if not updates:
        raise ValueError("At least one stakeholder contact update is required.")
    update_stakeholder_contacts_for_tag(tag=args.tag, updates=updates)
    print("Updated stakeholder contact fields for {}.".format(args.tag))
    return 0


def run_show(args: argparse.Namespace) -> int:
    """Display the stakeholder row matching an exact tag."""
    record = get_stakeholder_record_by_tag(args.tag)
    display_stakeholder_record(record)
    return 0


def run_update(args: argparse.Namespace) -> int:
    """Update selected stakeholder fields and display the resulting row."""
    if not args.confirm:
        raise ValueError("Stakeholder field updates require --confirm.")
    updates = stakeholder_updates(args)
    if not updates:
        raise ValueError("At least one stakeholder field update is required.")
    update_stakeholder_fields_for_tag(tag=args.tag, updates=updates)
    print("Updated stakeholder fields for {}.".format(args.tag))
    display_stakeholder_record(get_stakeholder_record_by_tag(args.tag))
    return 0


def run_export(args: argparse.Namespace) -> int:
    """Export stakeholder records locally, to S3, or to an assignee."""
    if args.confirm_sensitive_export and not args.include_report_passwords:
        raise ValueError(
            "--confirm-sensitive-export requires --include-report-passwords."
        )
    if args.include_report_passwords and not args.confirm_sensitive_export:
        raise ValueError("Password export requires --confirm-sensitive-export.")
    if args.include_report_passwords and args.email_assignee:
        raise ValueError("Stakeholder password exports cannot be emailed.")
    columns, rows = list_stakeholders_for_export_from_db(
        include_report_passwords=args.include_report_passwords
    )
    if not args.s3 and not args.email_assignee:
        write_stakeholder_csv(columns=columns, rows=rows, output_path=args.output)
        print("Exported {} stakeholders to {}.".format(len(rows), args.output))
        return 0

    with TemporaryDirectory(prefix="was-stakeholder-export-") as directory:
        export_path = Path(directory) / args.output.name
        write_stakeholder_csv(
            columns=columns,
            rows=rows,
            output_path=export_path,
        )
        if args.s3:
            export_uri = upload_stakeholder_export(export_path)
            print("Exported {} stakeholders to {}.".format(len(rows), export_uri))
            return 0

        recipients = approved_analyst_recipients(args.email_assignee)
        message = build_stakeholder_export_email(
            source_email=require_env("WAS_EMAIL_SOURCE"),
            recipients=recipients,
            export_path=export_path,
            includes_passwords=args.include_report_passwords,
        )
        message_id = send_message(create_ses_client(), message)
        print(
            "Emailed {} stakeholders to approved assignee recipients; "
            "SES message ID: {}.".format(len(rows), message_id)
        )
    return 0


def run_import(args: argparse.Namespace) -> int:
    """Prepare a CSV and atomically insert stakeholders not already present."""
    if not args.confirm:
        raise ValueError("Stakeholder CSV imports require --confirm.")
    prepared_rows = prepare_stakeholder_csv(
        input_path=args.input,
        output_path=args.prepared_output,
        null_token=args.null_token,
    )
    inserted_count, skipped_count = import_prepared_rows(
        prepared_rows=prepared_rows,
        null_token=args.null_token,
    )
    print(
        "Imported {} new stakeholders and skipped {} existing tags.".format(
            inserted_count, skipped_count
        )
    )
    print("Prepared import CSV written to {}.".format(args.prepared_output))
    return 0


def run_add(args: argparse.Namespace) -> int:
    """Create one stakeholder with an automatically generated password."""
    if not args.confirm:
        raise ValueError("Stakeholder creation requires --confirm.")
    values = {
        "tag": args.tag,
        "customer_name": args.customer_name,
        "comments": args.comments,
        "location_notes": args.location_notes,
        "ci_type": args.ci_type,
        "testing_sector": args.testing_sector,
        "subtype": args.subtype,
        "distro_email": args.distro_email,
        "tech_poc_email": args.tech_poc_email,
        "was_report_poc": args.was_report_poc,
        "frequency": args.frequency,
        "num_web_apps": args.num_web_apps,
        "web_apps_last_updated": args.web_apps_last_updated,
        "last_scanned": args.last_scanned,
        "next_scheduled": args.next_scheduled,
        "onboarding_date": args.onboarding_date,
        "parent_tag": args.parent_tag,
        "ticket": args.ticket,
        "elections": args.elections,
        "fceb": args.fceb,
        "manual_report": args.manual_report,
        "retired": args.retired,
        "state": args.state,
    }
    stakeholder_tag = create_stakeholder_in_db(values)
    print(
        "Created stakeholder {} with a generated report password.".format(
            stakeholder_tag
        )
    )
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """Run one stakeholder administration command."""
    configure_logging()
    args = parse_args(argv)
    try:
        if args.command == "update-contacts":
            return run_update_contacts(args)
        if args.command == "show":
            return run_show(args)
        if args.command == "update":
            return run_update(args)
        if args.command == "export-csv":
            return run_export(args)
        if args.command == "import-csv":
            return run_import(args)
        if args.command == "add":
            return run_add(args)
    except DatabaseError:
        print(
            "Error: database operation failed and was rolled back.",
            file=sys.stderr,
        )
        return 1
    except (BotoCoreError, ClientError):
        print("Error: AWS export delivery failed.", file=sys.stderr)
        return 1
    except (KeyError, OSError, ValueError) as error:
        print("Error: {}".format(str(error)), file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    sys.exit(main())
