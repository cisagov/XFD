"""CLI for stakeholder contact maintenance and controlled CSV export."""

# Standard Python Libraries
import argparse
import csv
import os
from pathlib import Path
import sys
from tempfile import NamedTemporaryFile
from typing import List, Optional

# First-Party Libraries
from was_mailer.message import parse_email_addresses
from was_reports.data.stakeholders import (
    list_stakeholders_for_export_from_db,
    update_stakeholder_contacts_for_tag,
)


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

    export_command = subcommands.add_parser(
        "export-csv",
        help="Export WAS stakeholder records to CSV.",
    )
    export_command.add_argument("--output", required=True, type=Path)
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
                        spreadsheet_safe_value(column_name, value)
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


def run_export(args: argparse.Namespace) -> int:
    """Export stakeholder records to a protected local CSV file."""
    if args.confirm_sensitive_export and not args.include_report_passwords:
        raise ValueError(
            "--confirm-sensitive-export requires --include-report-passwords."
        )
    if args.include_report_passwords and not args.confirm_sensitive_export:
        raise ValueError(
            "Password export requires --confirm-sensitive-export."
        )
    columns, rows = list_stakeholders_for_export_from_db(
        include_report_passwords=args.include_report_passwords
    )
    write_stakeholder_csv(columns=columns, rows=rows, output_path=args.output)
    print("Exported {} stakeholders to {}.".format(len(rows), args.output))
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """Run one stakeholder administration command."""
    args = parse_args(argv)
    try:
        if args.command == "update-contacts":
            return run_update_contacts(args)
        if args.command == "export-csv":
            return run_export(args)
    except (KeyError, ValueError) as error:
        print("Error: {}".format(str(error)), file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    sys.exit(main())
