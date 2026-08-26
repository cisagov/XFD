"""Email message helpers for WAS report delivery."""

# Standard Python Libraries
from email.message import EmailMessage
from pathlib import Path
from typing import Iterable, List


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
