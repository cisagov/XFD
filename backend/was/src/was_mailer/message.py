"""Email message helpers for WAS report delivery."""

# Standard Python Libraries
from email.message import EmailMessage
from pathlib import Path
from typing import Iterable, List

# First-Party Libraries
from was_reports.tracker_csv import tracker_rows_to_csv_text


def parse_email_addresses(raw_addresses: str | None) -> List[str]:
    """Parse semicolon or comma separated email addresses."""
    if not raw_addresses:
        return []

    addresses = []
    for semicolon_part in raw_addresses.split(";"):
        for comma_part in semicolon_part.split(","):
            address = comma_part.strip()
            if address:
                addresses.append(address)

    return addresses


def unique_addresses(addresses: Iterable[str]) -> List[str]:
    """Return unique email addresses while preserving order."""
    seen_addresses = set()
    unique = []
    for address in addresses:
        normalized_address = address.lower()
        if normalized_address in seen_addresses:
            continue
        seen_addresses.add(normalized_address)
        unique.append(address)
    return unique


def recipient_addresses(
    report_run_email,
    override_recipients: str | None = None,
) -> List[str]:
    """Return final recipients for a WAS report email."""
    if override_recipients:
        return unique_addresses(parse_email_addresses(override_recipients))

    addresses = []
    addresses.extend(parse_email_addresses(report_run_email.tech_poc_email))
    addresses.extend(parse_email_addresses(report_run_email.distro_email))
    return unique_addresses(addresses)


def build_report_email(
    source_email: str,
    recipients: List[str],
    stakeholder_tag: str,
    report_path: Path,
) -> EmailMessage:
    """Build a WAS report email with the PDF attached."""
    if not recipients:
        raise ValueError("At least one report email recipient is required.")

    if not report_path.is_file():
        raise FileNotFoundError(
            "WAS report attachment was not found at {}.".format(str(report_path))
        )

    message = EmailMessage()
    message["From"] = source_email
    message["To"] = ", ".join(recipients)
    message["Subject"] = "WAS Report for {}".format(stakeholder_tag)
    message.set_content(
        "Attached is the WAS report for {}.\n\n"
        "Use the existing stakeholder report password to open the PDF. "
        "If the password needs to be changed, submit a password change request.\n".format(
            stakeholder_tag
        )
    )

    with report_path.open("rb") as report_file:
        report_bytes = report_file.read()

    message.add_attachment(
        report_bytes,
        maintype="application",
        subtype="pdf",
        filename=report_path.name,
    )
    return message


def build_assignee_digest_email(
    source_email: str,
    recipients: List[str],
    assignee_digest,
) -> EmailMessage:
    """Build a daily WAS tracker digest email for one assignee."""
    if not recipients:
        raise ValueError("At least one assignee digest recipient is required.")

    message = EmailMessage()
    message["From"] = source_email
    message["To"] = ", ".join(recipients)
    message["Subject"] = "WAS Daily Tracker Assignments for {}".format(
        assignee_digest.assignee
    )
    message.set_content(assignee_digest_body(assignee_digest))
    message.add_attachment(
        tracker_rows_to_csv_text(assignee_digest.rows).encode("utf-8"),
        maintype="text",
        subtype="csv",
        filename=assignee_digest_csv_filename(assignee_digest.assignee),
    )
    return message


def assignee_digest_body(assignee_digest) -> str:
    """Return the plain text body for an assignee digest."""
    lines = [
        "WAS daily tracker assignments for {}".format(assignee_digest.assignee),
        "",
        "Total assigned rows: {}".format(len(assignee_digest.rows)),
        "",
    ]
    for tracker_row in assignee_digest.rows:
        lines.append("Tag: {}".format(tracker_row.tag or ""))
        lines.append("Scan Name: {}".format(tracker_row.scan_name or ""))
        lines.append("Status: {}".format(tracker_row.status or ""))
        lines.append("Result: {}".format(tracker_row.result or ""))
        lines.append("Template: {}".format(tracker_row.template or ""))
        lines.append("Next Scan Date: {}".format(tracker_row.next_scan_date or ""))
        lines.append("Notes: {}".format(tracker_row.report_scan_notes or ""))
        lines.append("")
    lines.append("Do not reply with report passwords or scanner credentials.")
    return "\n".join(lines)


def assignee_digest_csv_filename(assignee_name: str) -> str:
    """Return a safe CSV filename for an assignee digest."""
    characters = []
    for character in assignee_name.strip().lower():
        if character.isalnum():
            characters.append(character)
        elif character in [" ", "-", "_"]:
            characters.append("-")
    safe_name = "".join(characters).strip("-")
    if not safe_name:
        safe_name = "assignee"
    return "was-daily-tracker-{}.csv".format(safe_name)
